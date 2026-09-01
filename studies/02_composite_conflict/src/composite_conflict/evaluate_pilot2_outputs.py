"""Deterministic first-pass evaluator for Pilot 2 baseline outputs.

This evaluator is deliberately labeled a screen: lexical support cannot replace
semantic human/Codex validation, but it provides reproducible coverage and
omission diagnostics for all runs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STOP = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at", "from", "with",
    "their", "they", "them", "user", "users", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "it", "this", "that", "when", "while", "during", "under", "what",
    "changed", "change", "current", "now", "prefer", "prefers", "preference", "situation",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_token(token: str) -> str:
    token = token.lower().strip("-_ ")
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("s") and not token.endswith("ss") and len(token) > 4:
        token = token[:-1]
    return token


def tokens(text: str) -> set[str]:
    return {
        normalized
        for raw in re.findall(r"[a-z0-9][a-z0-9_-]*", text.lower().replace("–", "-"))
        if (normalized := normalize_token(raw)) and normalized not in STOP and len(normalized) > 1
    }


def response_text(response: dict[str, Any], final_only: bool = False) -> str:
    if final_only:
        return str(response.get("final_answer", ""))
    resolutions = " ".join(str(unit.get("resolution", "")) for unit in response.get("resolved_units", []) if isinstance(unit, dict))
    return " ".join([str(response.get("analysis_summary", "")), resolutions, str(response.get("final_answer", ""))])


def recall(expected: set[str], observed: set[str]) -> float:
    return len(expected & observed) / len(expected) if expected else 0.0


def evaluate(output: dict[str, Any], instance: dict[str, Any]) -> dict[str, Any]:
    response = output.get("response", {})
    all_text = tokens(response_text(response))
    final_text = tokens(response_text(response, final_only=True))
    units = response.get("resolved_units", []) if isinstance(response, dict) else []
    unit_scores = []
    for gold in instance["gold_units"]:
        expected = tokens(gold["gold_atomic_answer"])
        full_recall = recall(expected, all_text)
        final_recall = recall(expected, final_text)
        unit_scores.append({
            "unit_id": gold["unit_id"],
            "policy": gold["policy"],
            "expected_tokens": sorted(expected),
            "full_token_recall": round(full_recall, 4),
            "final_token_recall": round(final_recall, 4),
            "automatic_unit_success": full_recall >= 0.30 and final_recall >= 0.12,
        })

    valid_memory_ids = {record["memory_id"] for record in instance["memory_context"]}
    used_ids = {
        memory_id
        for unit in units if isinstance(unit, dict)
        for memory_id in unit.get("used_memory_ids", []) if isinstance(memory_id, str)
    }
    invalid_ids = sorted(used_ids - valid_memory_ids)
    expected_count = int(instance.get("K", len(instance["gold_units"])))
    automatic_all = len(unit_scores) == expected_count and all(item["automatic_unit_success"] for item in unit_scores)
    near_boundary = any(
        0.20 <= item["full_token_recall"] < 0.40 or 0.05 <= item["final_token_recall"] < 0.20
        for item in unit_scores
    )
    return {
        "run_id": output["run_id"],
        "instance_id": output["instance_id"],
        "H": instance["H"],
        "policies": instance["policies"],
        "baseline_condition": output["baseline_condition"],
        "automatic_all_unit_success": automatic_all,
        "unit_omission": len(units) != expected_count,
        "resolved_unit_count": len(units),
        "invalid_memory_ids": invalid_ids,
        "unit_scores": unit_scores,
        "needs_semantic_review": near_boundary or not automatic_all,
        "evaluator": "lexical-screen-v1; not final semantic judgment",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", nargs="+", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    instances = {row["instance_id"]: row for path in args.instances for row in load_jsonl(path)}
    outputs = load_jsonl(args.outputs)
    evaluations = [evaluate(row, instances[row["instance_id"]]) for row in outputs if "error" not in row]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        for row in evaluations:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary: dict[str, dict[str, int]] = {}
    for row in evaluations:
        key = f"H{row['H']}::{row['baseline_condition']}"
        bucket = summary.setdefault(key, {"n": 0, "automatic_success": 0, "needs_semantic_review": 0, "omission": 0})
        bucket["n"] += 1
        bucket["automatic_success"] += int(row["automatic_all_unit_success"])
        bucket["needs_semantic_review"] += int(row["needs_semantic_review"])
        bucket["omission"] += int(row["unit_omission"])
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
