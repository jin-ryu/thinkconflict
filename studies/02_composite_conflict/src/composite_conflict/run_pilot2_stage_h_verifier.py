"""Verify and selectively revise Stage H full-local drafts with one extra call."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

from openai import OpenAI

from composite_conflict.run_pilot2_baselines import parse_json
from composite_conflict.run_pilot2_stage_h import load_jsonl, payload


SYSTEM = """You are the final verifier for a personalized-memory answer.
Check the draft against every numbered query item and its corresponding memory group.
Correct stale states, wrong source choices, wrong conditions, cross-unit mixing, omissions, and unsupported extras.
If the draft is already correct, preserve its meaning.
Return JSON only with keys: analysis_summary (brief verification summary), resolved_units (list of exactly {unit_count} objects with keys unit_id, resolution, used_memory_ids), final_answer (string), selected_global_policy (null).
The final answer must address every requested item and must not mention benchmark labels."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--drafts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8004/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--max-tokens", type=int, default=900)
    parser.add_argument("--disable-thinking", action="store_true")
    args = parser.parse_args()

    instances = {row["instance_id"]: row for row in load_jsonl(args.instances)}
    drafts = [
        row for row in load_jsonl(args.drafts)
        if row.get("baseline_condition") == "full_local"
    ]
    if {row["instance_id"] for row in drafts} != set(instances):
        raise ValueError("full_local draft coverage does not match instances")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if args.output.exists():
        for row in load_jsonl(args.output):
            if "error" not in row:
                existing[row["run_id"]] = row
    client = OpenAI(base_url=args.base_url, api_key="EMPTY")
    lock = Lock()

    def run(draft: dict[str, Any]) -> dict[str, Any]:
        instance = instances[draft["instance_id"]]
        run_id = f"{instance['instance_id']}::full_local_verifier"
        raw = ""
        try:
            body = payload(instance, "full_local")
            body["draft_final_answer"] = (
                draft.get("response", {}).get("final_answer", "")
                if isinstance(draft.get("response"), dict) else ""
            )
            extra_body = {"chat_template_kwargs": {"enable_thinking": False}} if args.disable_thinking else None
            response = client.chat.completions.create(
                model=args.model,
                messages=[
                    {"role": "system", "content": SYSTEM.format(unit_count=instance["K"])},
                    {"role": "user", "content": json.dumps(body, ensure_ascii=False)},
                ],
                temperature=0,
                max_tokens=args.max_tokens,
                seed=args.seed,
                extra_body=extra_body,
            )
            raw = response.choices[0].message.content or ""
            return {
                "run_id": run_id,
                "instance_id": instance["instance_id"],
                "instance_condition": instance["condition"],
                "K": instance["K"],
                "H": instance["H"],
                "policies": instance["policies"],
                "baseline_condition": "full_local_verifier",
                "parent_run_id": draft["run_id"],
                "model": args.model,
                "temperature": 0,
                "seed": args.seed,
                "max_tokens": args.max_tokens,
                "disable_thinking": args.disable_thinking,
                "response": parse_json(raw),
                "raw_response": raw,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as exc:  # noqa: BLE001
            return {"run_id": run_id, "instance_id": instance["instance_id"], "baseline_condition": "full_local_verifier", "model": args.model, "error": str(exc), "raw_response": raw}

    todo = [row for row in drafts if f"{row['instance_id']}::full_local_verifier" not in existing]
    with args.output.open("a") as handle:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run, row): row for row in todo}
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
    expected = {f"{instance_id}::full_local_verifier" for instance_id in instances}
    final = [row for row in canonical if row["run_id"] in expected]
    print(json.dumps({"expected": len(expected), "completed": len(final), "errors": sum("error" in row for row in final)}, indent=2))


if __name__ == "__main__":
    main()
