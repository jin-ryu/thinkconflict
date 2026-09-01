"""Run no-training Pilot 2 baselines against an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from composite_conflict.api_runtime import (
    RequestThrottle,
    completion_with_retry,
    create_client,
    resolve_api_key,
)


CONDITIONS = (
    "direct",
    "generic_cot",
    "taxonomy_cot",
    "single_global_policy",
    "oracle_units",
    "oracle_unit_policies",
)

COMMON_SYSTEM = """You are a personalized assistant answering from dated memory records.
Return JSON only with keys: analysis_summary (brief string), resolved_units (list of exactly {unit_count} objects with keys unit_id, resolution, used_memory_ids), final_answer (string), selected_global_policy (string or null).
Do not mention benchmark labels in final_answer. Do not invent facts absent from the records. A useful final answer must address every requested part of the user's goal."""

INSTRUCTIONS = {
    "direct": "Answer the query using the supplied memory records.",
    "generic_cot": "First compare the relevant records and resolve any conflicts; then combine all resolved parts into one answer. Keep analysis_summary concise.",
    "taxonomy_cot": """Identify the independent relevant memory units. For each unit choose the appropriate behavior:
- SUPERSEDE: a genuine temporal update makes the newer user state replace the older state.
- VERIFY_PREFER: incompatible claims concern a stable fact; preserve the benchmark-supported canonical fact and explicitly note the disagreement when useful.
- CONDITION: multiple preferences can remain valid under different conditions; apply only the preference whose condition matches the query.
Resolve the units separately and then compose the answer. Do not assume one behavior must apply globally.""",
    "single_global_policy": """Choose exactly one global behavior from SUPERSEDE, VERIFY_PREFER, or CONDITION for the entire instance. Apply that same behavior to every relevant unit. Put the choice in selected_global_policy, resolve all units, and compose the answer.""",
    "oracle_units": "The relevant memory units are already grouped for you. Infer the correct behavior separately for each group, resolve every group, and compose the answer.",
    "oracle_unit_policies": "The relevant memory units and their required behaviors are given. Apply each behavior to its own group, resolve every group, and compose the answer.",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def strip_gold(unit: dict[str, Any], include_policy: bool) -> dict[str, Any]:
    result = {"unit_id": unit["unit_id"], "evidence_ids": unit["evidence_ids"]}
    if include_policy:
        result["required_behavior"] = unit["policy"]
    return result


def payload(instance: dict[str, Any], condition: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "target_date": instance["target_date"],
        "query": instance["query"],
        "memory_records": instance["memory_context"],
    }
    if condition in {"oracle_units", "oracle_unit_policies"}:
        body["relevant_units"] = [
            strip_gold(unit, include_policy=condition == "oracle_unit_policies")
            for unit in instance["gold_units"]
        ]
    return body


def prompt_for(instance: dict[str, Any], condition: str) -> list[dict[str, str]]:
    unit_count = int(instance.get("K", len(instance["gold_units"])))
    system = COMMON_SYSTEM.format(unit_count=unit_count)
    return [
        {"role": "system", "content": system + "\n\n" + INSTRUCTIONS[condition]},
        {"role": "user", "content": json.dumps(payload(instance, condition), ensure_ascii=False)},
    ]


def parse_json(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8004/v1")
    parser.add_argument("--model", default="mistralai/Mistral-Small-3.2-24B-Instruct-2506")
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260826)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"))
    parser.add_argument("--api-key-env")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--request-cooldown-seconds",
        "--request-delay-seconds",
        dest="request_cooldown_seconds",
        type=float,
        default=0.0,
        help="Minimum delay from one completed request to the next request start.",
    )
    parser.add_argument("--max-retries", type=int, default=0)
    parser.add_argument("--retry-base-delay-seconds", type=float, default=30.0)
    parser.add_argument(
        "--retry-503-backoff",
        action="store_true",
        help="Retry only HTTP 503 after 5 and 15 minutes; never retry timeouts.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--omit-seed", action="store_true")
    parser.add_argument("--max-instances", type=int)
    args = parser.parse_args()

    instances = [row for path in args.inputs for row in load_jsonl(path)]
    if args.max_instances is not None:
        if args.max_instances <= 0:
            raise ValueError("max instances must be positive")
        instances = instances[: args.max_instances]
    jobs = [(instance, condition) for instance in instances for condition in args.conditions]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if args.output.exists():
        for row in load_jsonl(args.output):
            if "error" not in row:
                existing[row["run_id"]] = row

    api_key = resolve_api_key(env_name=args.api_key_env, env_file=args.env_file)
    client = create_client(
        base_url=args.base_url,
        api_key=api_key,
        timeout_seconds=args.timeout_seconds,
    )
    if args.api_key_env and args.workers != 1:
        raise ValueError("external API runs require --workers 1")
    if args.api_key_env and args.request_cooldown_seconds < 30:
        raise ValueError("external API runs require at least 30 seconds of post-completion cooldown")
    # local vLLM runs are served concurrently; the serializing throttle is only for external APIs
    throttle = (
        RequestThrottle(args.request_cooldown_seconds)
        if args.api_key_env or args.request_cooldown_seconds > 0
        else None
    )
    lock = Lock()
    effective_max_retries = 2 if args.retry_503_backoff else args.max_retries
    retry_delays_seconds = (300.0, 900.0) if args.retry_503_backoff else None

    def run(job: tuple[dict[str, Any], str]) -> dict[str, Any]:
        instance, condition = job
        run_id = f"{instance['instance_id']}::{condition}"
        raw = ""
        retry_events: list[dict[str, Any]] = []

        def on_retry(attempt: int, delay: float, error: Exception) -> None:
            event = {
                "retry_number": attempt,
                "delay_seconds": delay,
                "status_code": getattr(error, "status_code", None),
            }
            retry_events.append(event)
            print(json.dumps({"run_id": run_id, "retry": event}), flush=True)

        try:
            extra_body: dict[str, Any] = {}
            if args.disable_thinking:
                extra_body["chat_template_kwargs"] = {"enable_thinking": False}
            if args.reasoning_effort:
                extra_body["reasoning_effort"] = args.reasoning_effort
            request: dict[str, Any] = {
                "model": args.model,
                "messages": prompt_for(instance, condition),
                "temperature": 0,
                "max_tokens": args.max_tokens,
                "extra_body": extra_body or None,
            }
            if not args.omit_seed:
                request["seed"] = args.seed
            response = completion_with_retry(
                client=client,
                request=request,
                throttle=throttle,
                max_retries=effective_max_retries,
                retry_base_delay_seconds=args.retry_base_delay_seconds,
                retry_delays_seconds=retry_delays_seconds,
                retry_status_codes={503} if args.retry_503_backoff else None,
                retry_timeouts=not args.retry_503_backoff,
                retry_connection_errors=not args.retry_503_backoff,
                on_retry=on_retry,
            )
            raw = response.choices[0].message.content or ""
            parsed = parse_json(raw)
            return {
                "run_id": run_id,
                "instance_id": instance["instance_id"],
                "instance_condition": instance["condition"],
                "K": instance["K"],
                "H": instance["H"],
                "policies": instance["policies"],
                "baseline_condition": condition,
                "model": args.model,
                "temperature": 0,
                "seed": args.seed,
                "max_tokens": args.max_tokens,
                "disable_thinking": args.disable_thinking,
                "reasoning_effort": args.reasoning_effort,
                "response": parsed,
                "raw_response": raw,
                "api_key_env": args.api_key_env,
                "request_cooldown_seconds": args.request_cooldown_seconds,
                "omit_seed": args.omit_seed,
                "usage": response.usage.model_dump() if response.usage else None,
                "request_attempts": 1 + len(retry_events),
                "retry_events": retry_events,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "run_id": run_id,
                "instance_id": instance["instance_id"],
                "baseline_condition": condition,
                "model": args.model,
                "error": str(exc),
                "raw_response": raw,
                "request_attempts": 1 + len(retry_events),
                "retry_events": retry_events,
            }

    todo = [job for job in jobs if f"{job[0]['instance_id']}::{job[1]}" not in existing]
    with args.output.open("a") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run, job): job for job in todo}
            for future in as_completed(futures):
                row = future.result()
                with lock:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()

    latest: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(args.output):
        latest[row["run_id"]] = row
    canonical = [latest[run_id] for run_id in sorted(latest)]
    with args.output.open("w") as handle:
        for row in canonical:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    final = canonical
    expected = {f"{instance['instance_id']}::{condition}" for instance, condition in jobs}
    current = {row["run_id"] for row in final if row["run_id"] in expected}
    errors = sum("error" in row for row in final if row["run_id"] in expected)
    print(json.dumps({"expected": len(expected), "completed": len(current), "errors": errors}, indent=2))


if __name__ == "__main__":
    main()
