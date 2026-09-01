"""Run Stage H oracle diagnostic interventions on frozen Stage G instances."""

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

from composite_conflict.run_pilot2_baselines import parse_json


CONDITIONS = (
    "grouped_only",
    "owner_filter",
    "target_filter",
    "grouped_policy",
    "full_local",
)

SYSTEM = """You are a personalized assistant answering from dated memory records.
Return JSON only with keys: analysis_summary (brief string), resolved_units (list of exactly {unit_count} objects with keys unit_id, resolution, used_memory_ids), final_answer (string), selected_global_policy (string or null).
Do not mention benchmark labels in final_answer. Do not invent facts absent from the supplied records. Address every numbered query item."""

INSTRUCTIONS = {
    "grouped_only": "Records are physically grouped by the query unit they concern. Infer the appropriate resolution for each group and combine all conclusions.",
    "owner_filter": "Records about other people have been removed. Resolve every requested item and combine all conclusions.",
    "target_filter": "Other-person and oracle-identified non-target preference records have been removed. Resolve every requested item and combine all conclusions.",
    "grouped_policy": "Records are grouped by unit and each group supplies its required behavior. Apply the behavior locally to every group and combine all conclusions.",
    "full_local": "Records are grouped by unit, source/target filtered, and each group supplies its required behavior. Resolve every group locally and combine all conclusions.",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def text_tokens(value: Any) -> set[str]:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def conflict_signature(memory_id: str) -> str:
    parts = memory_id.rsplit(":", 2)
    if len(parts) < 3:
        raise ValueError(f"invalid memory id: {memory_id}")
    return parts[-2]


def unit_signatures(unit: dict[str, Any]) -> set[str]:
    return {conflict_signature(memory_id) for memory_id in unit["evidence_ids"]}


def assign_groups(instance: dict[str, Any]) -> list[dict[str, Any]]:
    units = instance["gold_units"]
    evidence_to_index = {
        memory_id: index
        for index, unit in enumerate(units)
        for memory_id in unit["evidence_ids"]
    }
    signatures = [unit_signatures(unit) for unit in units]
    grouped: list[list[dict[str, Any]]] = [[] for _ in units]
    for record in instance["memory_context"]:
        memory_id = record["memory_id"]
        index = evidence_to_index.get(memory_id)
        if index is not None:
            grouped[index].append(record)
            continue
        candidates = [
            unit_index
            for unit_index, unit_signature_set in enumerate(signatures)
            if conflict_signature(memory_id) in unit_signature_set
        ]
        if not candidates:
            raise ValueError(f"{instance['instance_id']}: cannot assign {memory_id} to any unit")
        # A distractor can be shared by multiple static questions from the same
        # conflict group. Preserve it in every applicable local context.
        for candidate in candidates:
            grouped[candidate].append(record)

    return [
        {
            "unit_id": unit["unit_id"],
            "question": unit["atomic_question"],
            "target_date": unit["unit_target_date"],
            "required_behavior": unit["policy"],
            "gold_answer_for_filter_only": unit["gold_atomic_answer"],
            "records": records,
        }
        for unit, records in zip(units, grouped, strict=True)
    ]


def owner_filtered(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("source") != "other_person_statement"]


def target_filtered(group: dict[str, Any]) -> list[dict[str, Any]]:
    records = owner_filtered(group["records"])
    if group["required_behavior"] != "CONDITION":
        return records
    preferences = [record for record in records if record.get("source") == "user_preference_statement"]
    if len(preferences) <= 1:
        return records
    target = text_tokens(group["question"] + " " + group["gold_answer_for_filter_only"])
    scores = [len(target & text_tokens(record["claim"])) for record in preferences]
    best = max(scores)
    keep_ids = {
        record["memory_id"] for record, score in zip(preferences, scores, strict=True) if score == best
    }
    return [record for record in records if record.get("source") != "user_preference_statement" or record["memory_id"] in keep_ids]


def public_group(group: dict[str, Any], *, filtered: bool, include_policy: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "unit_id": group["unit_id"],
        "question": group["question"],
        "target_date": group["target_date"],
        "records": target_filtered(group) if filtered else group["records"],
    }
    if include_policy:
        result["required_behavior"] = group["required_behavior"]
    return result


def payload(instance: dict[str, Any], condition: str) -> dict[str, Any]:
    groups = assign_groups(instance)
    body: dict[str, Any] = {"target_date": instance["target_date"], "query": instance["query"]}
    if condition == "owner_filter":
        allowed = {record["memory_id"] for group in groups for record in owner_filtered(group["records"])}
        body["memory_records"] = [record for record in instance["memory_context"] if record["memory_id"] in allowed]
    elif condition == "target_filter":
        allowed = {record["memory_id"] for group in groups for record in target_filtered(group)}
        body["memory_records"] = [record for record in instance["memory_context"] if record["memory_id"] in allowed]
    else:
        filtered = condition == "full_local"
        include_policy = condition in {"grouped_policy", "full_local"}
        body["memory_groups"] = [
            public_group(group, filtered=filtered, include_policy=include_policy) for group in groups
        ]
    return body


def prompt_for(instance: dict[str, Any], condition: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM.format(unit_count=instance["K"]) + "\n\n" + INSTRUCTIONS[condition],
        },
        {"role": "user", "content": json.dumps(payload(instance, condition), ensure_ascii=False)},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8004/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=list(CONDITIONS))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260828)
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
    throttle = RequestThrottle(args.request_cooldown_seconds)
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
            extra_body = {"chat_template_kwargs": {"enable_thinking": False}} if args.disable_thinking else None
            if args.reasoning_effort:
                extra_body = extra_body or {}
                extra_body["reasoning_effort"] = args.reasoning_effort
            request: dict[str, Any] = {
                "model": args.model,
                "messages": prompt_for(instance, condition),
                "temperature": 0,
                "max_tokens": args.max_tokens,
                "extra_body": extra_body,
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
            return {
                "run_id": run_id,
                "instance_id": instance["instance_id"],
                "instance_condition": instance["condition"],
                "K": instance["K"],
                "H": instance["H"],
                "policies": instance["policies"],
                "api_key_env": args.api_key_env,
                "request_cooldown_seconds": args.request_cooldown_seconds,
                "omit_seed": args.omit_seed,
                "baseline_condition": condition,
                "model": args.model,
                "temperature": 0,
                "seed": args.seed,
                "max_tokens": args.max_tokens,
                "disable_thinking": args.disable_thinking,
                "response": parse_json(raw),
                "reasoning_effort": args.reasoning_effort,
                "raw_response": raw,
                "usage": response.usage.model_dump() if response.usage else None,
                "request_attempts": 1 + len(retry_events),
                "retry_events": retry_events,
            }
        except Exception as exc:  # noqa: BLE001
            return {"run_id": run_id, "instance_id": instance["instance_id"], "baseline_condition": condition, "model": args.model, "error": str(exc), "raw_response": raw, "request_attempts": 1 + len(retry_events), "retry_events": retry_events}

    todo = [job for job in jobs if f"{job[0]['instance_id']}::{job[1]}" not in existing]
    with args.output.open("a") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run, job): job for job in todo}
            for future in as_completed(futures):
                row = future.result()
                with lock:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()

    latest = {row["run_id"]: row for row in load_jsonl(args.output)}
    canonical = [latest[run_id] for run_id in sorted(latest)]
    with args.output.open("w") as handle:
        for row in canonical:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    expected = {f"{instance['instance_id']}::{condition}" for instance, condition in jobs}
    final = [row for row in canonical if row["run_id"] in expected]
    print(json.dumps({"expected": len(expected), "completed": len(final), "errors": sum("error" in row for row in final)}, indent=2))


if __name__ == "__main__":
    main()
