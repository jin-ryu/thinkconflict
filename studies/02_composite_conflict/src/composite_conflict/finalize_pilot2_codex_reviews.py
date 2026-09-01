"""Merge direct Codex annotations with the immutable MemConflict pair pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


JUDGE = {
    "judge_name": "OpenAI Codex interactive agent",
    "model_family": "GPT-5-based Codex",
    "deployment_checkpoint": "not exposed by the interface",
    "protocol": "pilot2-codex-direct-v1",
    "judged_at": "2026-08-26",
    "independence": "single Codex pass; no independent human validation",
    "intended_use": "exploratory feasibility only",
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pool", type=Path)
    parser.add_argument("annotations", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    pool = {row["pair_id"]: row for row in load_jsonl(args.pool)}
    annotations = load_jsonl(args.annotations)
    if len({row["pair_id"] for row in annotations}) != len(annotations):
        raise ValueError("Duplicate pair_id in annotations")

    merged = []
    for annotation in annotations:
        pair_id = annotation["pair_id"]
        if pair_id not in pool:
            raise KeyError(f"Unknown pair_id: {pair_id}")
        if annotation["codex_valid"] and not annotation.get("combined_query"):
            raise ValueError(f"Valid row lacks combined_query: {pair_id}")
        row = dict(pool[pair_id])
        row["selection_frame"] = "enriched feasibility sample; not random prevalence sample"
        row["codex_review"] = {key: value for key, value in annotation.items() if key != "pair_id"}
        row["judge"] = JUDGE
        merged.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in merged:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    valid = sum(row["codex_review"]["codex_valid"] for row in merged)
    print(json.dumps({"reviewed": len(merged), "valid": valid, "rejected": len(merged) - valid}, indent=2))


if __name__ == "__main__":
    main()
