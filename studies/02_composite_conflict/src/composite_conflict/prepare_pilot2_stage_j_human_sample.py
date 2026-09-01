"""Stage J-8: stratified sample of composite trials for blind human validation.

Strata: generation model x cell x judge verdict (all-unit correct / not).
Each sampled row carries the compound query, memory records, candidate final
answer, per-unit gold and the judge's per-unit verdicts (hidden in the
annotation view), so an annotator can mark each unit correct/incorrect and the
leakage label without seeing the machine verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from composite_conflict.analyze_pilot2_stage_j_independence import read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--composites", type=Path, nargs="+", required=True)
    parser.add_argument("--outputs", type=Path, nargs="+", required=True, help="one per model, same order as --judgments")
    parser.add_argument("--judgments", type=Path, nargs="+", required=True)
    parser.add_argument("--labels", nargs="+", required=True)
    parser.add_argument("--per-stratum", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    assert len(args.outputs) == len(args.judgments) == len(args.labels)

    instances = {row["instance_id"]: row for path in args.composites for row in read_jsonl(path)}
    rng = random.Random(args.seed)
    pool: dict[tuple[str, str, bool], list[dict[str, Any]]] = defaultdict(list)
    for out_path, judge_path, label in zip(args.outputs, args.judgments, args.labels):
        outputs = {row["instance_id"]: row for row in read_jsonl(out_path)}
        for jrow in read_jsonl(judge_path):
            inst = instances.get(jrow["instance_id"])
            if inst is None or "judgment" not in jrow or jrow["instance_id"] not in outputs:
                continue
            if inst.get("condition") == "atomic_control":
                continue
            cell = inst.get("cell") or f"K{inst['K']}_H{inst['H']}"
            response = outputs[jrow["instance_id"]].get("response")
            final = response.get("final_answer", "") if isinstance(response, dict) else ""
            pool[(label, cell, bool(jrow["judgment"]["all_unit_success"]))].append({
                "sample_id": hashlib.sha256(f"{label}:{jrow['instance_id']}".encode()).hexdigest()[:12],
                "generation_label": label,
                "instance_id": jrow["instance_id"],
                "cell": cell,
                "query": inst["query"],
                "memory_records": inst["memory_context"],
                "candidate_final_answer": final,
                "units": [
                    {"unit_id": u["unit_id"], "atomic_question": u.get("atomic_question"), "policy": u["policy"], "gold_atomic_answer": u.get("gold_atomic_answer"), "evidence_ids": u.get("evidence_ids", [])}
                    for u in inst["gold_units"]
                ],
                "_machine": {"all_unit_success": jrow["judgment"]["all_unit_success"], "unit_results": jrow["judgment"]["unit_results"]},
            })
    sample = []
    for key in sorted(pool):
        rows = pool[key]
        rng.shuffle(rows)
        sample.extend(rows[: args.per_stratum])
    rng.shuffle(sample)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "human_sample_with_machine.jsonl").open("w", encoding="utf-8") as f:
        for row in sample:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.out_dir / "human_sample_blind.jsonl").open("w", encoding="utf-8") as f:
        for row in sample:
            blind = {k: v for k, v in row.items() if not k.startswith("_")}
            blind["annotation"] = {"units": [{"unit_id": u["unit_id"], "correct": None, "label": None, "note": ""} for u in row["units"]]}
            f.write(json.dumps(blind, ensure_ascii=False) + "\n")
    summary = {"total": len(sample), "strata": {f"{k[0]}|{k[1]}|{'ok' if k[2] else 'fail'}": min(len(v), args.per_stratum) for k, v in sorted(pool.items())}}
    (args.out_dir / "sample_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
