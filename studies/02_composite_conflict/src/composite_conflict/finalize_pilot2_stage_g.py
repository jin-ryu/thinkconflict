"""Aggregate Stage G semantic judgments at the independent base-instance level."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ORDERS = ("original", "reverse", "interleaved")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def rate(values: list[bool]) -> dict[str, Any]:
    n = len(values)
    success = sum(values)
    if not n:
        return {"n": 0, "success": 0, "rate": None, "wilson95": [None, None]}
    p = success / n
    z = 1.959963984540054
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return {
        "n": n,
        "success": success,
        "rate": round(p, 4),
        "wilson95": [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atomic", type=Path, required=True)
    parser.add_argument("--composite", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    atomic = load_jsonl(args.atomic)
    composite = load_jsonl(args.composite)
    judgments = load_jsonl(args.judgments)
    errors = [row for row in judgments if "error" in row]
    if errors:
        raise ValueError(f"semantic judgments contain {len(errors)} errors")
    judged = {row["instance_id"]: row["judgment"] for row in judgments}
    expected = {row["instance_id"] for row in atomic + composite}
    if set(judged) != expected:
        raise ValueError(f"judgment coverage mismatch: expected {len(expected)}, got {len(judged)}")

    bases: dict[str, dict[str, Any]] = {}
    for row in composite:
        base = bases.setdefault(row["base_instance_id"], {
            "K": row["K"],
            "H": row["H"],
            "cell": f"K{row['K']}_H{row['H']}",
            "policy_multiset": row["policy_multiset"],
            "atomic": [],
            "composite": {},
            "errors": {},
        })
        success = judged[row["instance_id"]]["all_unit_success"]
        base["composite"][row["order_variant"]] = success
        base["errors"][row["order_variant"]] = judged[row["instance_id"]]["error_types"]
    for row in atomic:
        bases[row["base_instance_id"]]["atomic"].append(judged[row["instance_id"]]["all_unit_success"])

    for base_id, base in bases.items():
        if len(base["atomic"]) != base["K"]:
            raise ValueError(f"{base_id}: expected {base['K']} atomic probes")
        if set(base["composite"]) != set(ORDERS):
            raise ValueError(f"{base_id}: missing order variant")
        base["atomic_all"] = all(base["atomic"])
        outcomes = [base["composite"][order] for order in ORDERS]
        base["worst_order_success"] = all(outcomes)
        base["best_order_success"] = any(outcomes)
        base["order_flip"] = len(set(outcomes)) > 1
        base["composition_specific_trials"] = [
            base["atomic_all"] and not base["composite"][order] for order in ORDERS
        ]
        base["composition_specific_any"] = any(base["composition_specific_trials"])

    def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
        atomic_units = [value for item in items for value in item["atomic"]]
        order_trials = [item["composite"][order] for item in items for order in ORDERS]
        eligible_trials = [
            item["composite"][order]
            for item in items if item["atomic_all"] for order in ORDERS
        ]
        error_types = Counter(
            error
            for item in items
            for order in ORDERS
            if item["atomic_all"] and not item["composite"][order]
            for error in item["errors"][order]
        )
        return {
            "independent_base_instances": len(items),
            "atomic_unit_accuracy": rate(atomic_units),
            "atomic_all_units_per_base": rate([item["atomic_all"] for item in items]),
            "composite_by_order": {
                order: rate([item["composite"][order] for item in items]) for order in ORDERS
            },
            "pooled_order_trials_not_independent": rate(order_trials),
            "worst_order_base_accuracy": rate([item["worst_order_success"] for item in items]),
            "best_order_base_accuracy": rate([item["best_order_success"] for item in items]),
            "order_flip_by_base": rate([item["order_flip"] for item in items]),
            "composition_specific_failure": {
                "eligible_bases_atomic_all_correct": sum(item["atomic_all"] for item in items),
                "base_with_any_failure": rate([
                    item["composition_specific_any"] for item in items if item["atomic_all"]
                ]),
                "successful_composite_order_trials_given_atomic_all": rate(eligible_trials),
                "failure_error_types": dict(error_types),
            },
        }

    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    policies: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for base in bases.values():
        cells[base["cell"]].append(base)
        policies[base["policy_multiset"]].append(base)

    by_cell = {key: summarize(cells[key]) for key in sorted(cells)}
    trend = {
        "K2_H1_to_H2_worst_order_delta": round(
            by_cell["K2_H2"]["worst_order_base_accuracy"]["rate"]
            - by_cell["K2_H1"]["worst_order_base_accuracy"]["rate"], 4
        ),
        "K3_worst_order_rates_by_H": {
            str(h): by_cell[f"K3_H{h}"]["worst_order_base_accuracy"]["rate"] for h in (1, 2, 3)
        },
        "warning": "Cells contain different sampled composites; deltas are descriptive, not paired causal estimates.",
    }
    result = {
        "generation_model": judgments[0]["generation_model"],
        "judge_model": judgments[0]["judge_model"],
        "design": {
            "base_instances": len(bases),
            "atomic_probes": len(atomic),
            "composite_order_trials": len(composite),
            "orders": list(ORDERS),
            "statistical_unit": "base_instance; order variants are repeated measures",
        },
        "overall": summarize(list(bases.values())),
        "by_cell": by_cell,
        "descriptive_H_trend": trend,
        "by_policy_multiset": {
            key: summarize(value) for key, value in sorted(policies.items())
        },
        "caveats": [
            "This is a controlled cross-session composition diagnostic, not a natural-prevalence estimate.",
            "The semantic judge is an LLM; publication claims require blind human validation on a stratified sample.",
            "H spans the three MemConflict validity operations only: temporal, factual/source, and contextual.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "generation_model": result["generation_model"],
        "judge_model": result["judge_model"],
        "cells": {key: value["worst_order_base_accuracy"] for key, value in by_cell.items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
