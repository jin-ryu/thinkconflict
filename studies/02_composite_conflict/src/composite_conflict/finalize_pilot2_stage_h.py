"""Aggregate Stage H interventions with paired recovery, robustness, and cost."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


ORDERS = ("original", "reverse", "interleaved")
CONDITIONS = (
    "direct",
    "grouped_only",
    "owner_filter",
    "target_filter",
    "grouped_policy",
    "full_local",
    "full_local_verifier",
)


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
    return {"n": n, "success": success, "rate": round(p, 4), "wilson95": [round(max(0, centre - half), 4), round(min(1, centre + half), 4)]}


def mcnemar_exact(recovered: int, regressed: int) -> float:
    n = recovered + regressed
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(recovered, regressed) + 1)) / (2**n)
    return round(min(1.0, 2 * tail), 6)


def usage_sum(row: dict[str, Any]) -> int:
    usage = row.get("usage") or {}
    return int(usage.get("total_tokens") or 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", type=Path, required=True)
    parser.add_argument("--baseline-judgments", type=Path, required=True)
    parser.add_argument("--intervention-judgments", nargs="+", type=Path, required=True)
    parser.add_argument("--generation-outputs", nargs="+", type=Path, required=True)
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=CONDITIONS,
        default=list(CONDITIONS),
        help="Subset to aggregate; direct must be included.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    conditions = tuple(args.conditions)
    if "direct" not in conditions:
        raise ValueError("conditions must include direct")

    instances = {row["instance_id"]: row for row in load_jsonl(args.instances)}
    judgments = [
        row for path in [args.baseline_judgments, *args.intervention_judgments]
        for row in load_jsonl(path)
        if row["instance_id"] in instances
    ]
    if any("error" in row for row in judgments):
        raise ValueError("judgment files contain errors")
    success = {
        (row["instance_id"], row["baseline_condition"]): row["judgment"]["all_unit_success"]
        for row in judgments
    }
    expected = {(instance_id, condition) for instance_id in instances for condition in conditions}
    if set(success) != expected:
        raise ValueError(f"judgment coverage mismatch: expected {len(expected)}, got {len(success)}")

    outputs = [row for path in args.generation_outputs for row in load_jsonl(path) if row["instance_id"] in instances]
    output_by_key = {(row["instance_id"], row["baseline_condition"]): row for row in outputs}
    if set(output_by_key) != expected:
        raise ValueError(f"generation output coverage mismatch: expected {len(expected)}, got {len(output_by_key)}")

    bases: dict[str, list[str]] = defaultdict(list)
    for instance_id, instance in instances.items():
        bases[instance["base_instance_id"]].append(instance_id)
    if any(len(ids) != 3 for ids in bases.values()):
        raise ValueError("every base needs three order variants")

    direct = {instance_id: success[(instance_id, "direct")] for instance_id in instances}
    metrics: dict[str, Any] = {}
    for condition in conditions:
        trial_values = [success[(instance_id, condition)] for instance_id in sorted(instances)]
        base_outcomes = {
            base_id: [success[(instance_id, condition)] for instance_id in instance_ids]
            for base_id, instance_ids in bases.items()
        }
        recovered = sum(not direct[instance_id] and success[(instance_id, condition)] for instance_id in instances) if condition != "direct" else 0
        regressed = sum(direct[instance_id] and not success[(instance_id, condition)] for instance_id in instances) if condition != "direct" else 0
        by_cell: dict[str, Any] = {}
        for cell in sorted({f"K{x['K']}_H{x['H']}" for x in instances.values()}):
            cell_base_ids = [
                base_id for base_id, instance_ids in bases.items()
                if f"K{instances[instance_ids[0]]['K']}_H{instances[instance_ids[0]]['H']}" == cell
            ]
            cell_trials = [instance_id for base_id in cell_base_ids for instance_id in bases[base_id]]
            by_cell[cell] = {
                "order_trials_not_independent": rate([success[(instance_id, condition)] for instance_id in cell_trials]),
                "worst_order_base": rate([all(base_outcomes[base_id]) for base_id in cell_base_ids]),
            }

        token_totals = []
        calls = []
        for instance_id in instances:
            row = output_by_key[(instance_id, condition)]
            total = usage_sum(row)
            call_count = 1
            if condition == "full_local_verifier":
                total += usage_sum(output_by_key[(instance_id, "full_local")])
                call_count = 2
            token_totals.append(total)
            calls.append(call_count)

        metrics[condition] = {
            "all_unit_success_order_trials_not_independent": rate(trial_values),
            "by_order": {
                order: rate([
                    success[(instance_id, condition)]
                    for instance_id, instance in instances.items()
                    if instance["order_variant"] == order
                ]) for order in ORDERS
            },
            "worst_order_base_accuracy": rate([all(values) for values in base_outcomes.values()]),
            "best_order_base_accuracy": rate([any(values) for values in base_outcomes.values()]),
            "order_flip_by_base": rate([len(set(values)) > 1 for values in base_outcomes.values()]),
            "paired_vs_direct": {
                "recovered_order_trials": recovered,
                "regressed_order_trials": regressed,
                "net_success_change": recovered - regressed,
                "mcnemar_exact_p": mcnemar_exact(recovered, regressed),
            },
            "by_cell": by_cell,
            "cost": {
                "model_calls_per_trial": calls[0],
                "mean_total_tokens_per_trial": round(sum(token_totals) / len(token_totals), 1),
                "total_model_calls": sum(calls),
                "total_tokens": sum(token_totals),
            },
        }

    verifier_increment = None
    if {"full_local", "full_local_verifier"}.issubset(conditions):
        verifier_recovered = sum(
            not success[(instance_id, "full_local")] and success[(instance_id, "full_local_verifier")]
            for instance_id in instances
        )
        verifier_regressed = sum(
            success[(instance_id, "full_local")] and not success[(instance_id, "full_local_verifier")]
            for instance_id in instances
        )
        verifier_increment = {
            "recovered_order_trials": verifier_recovered,
            "regressed_order_trials": verifier_regressed,
            "net_success_change": verifier_recovered - verifier_regressed,
            "mcnemar_exact_p": mcnemar_exact(verifier_recovered, verifier_regressed),
        }
    result = {
        "protocol": "stage-h-outcome-blind-screen-v1",
        "design": {"base_instances": len(bases), "order_trials": len(instances), "statistical_unit": "base_instance; order variants are repeated measures"},
        "generation_model": outputs[0]["model"],
        "judge_model": judgments[0]["judge_model"],
        "conditions": metrics,
        "verifier_increment_over_full_local": verifier_increment,
        "caveats": [
            "Grouping, target filtering, and policy labels are oracle diagnostics, not an end-to-end method.",
            "Target filtering uses the gold atomic answer only to identify removable non-target preferences; the gold answer is never exposed to the generation model.",
            "The 50 bases were selected without model outcomes, but this is a screen rather than a publication-scale human-validated evaluation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({condition: {"trial_rate": item["all_unit_success_order_trials_not_independent"]["rate"], "worst_order": item["worst_order_base_accuracy"]["rate"], "net_vs_direct": item["paired_vs_direct"]["net_success_change"], "tokens": item["cost"]["mean_total_tokens_per_trial"]} for condition, item in metrics.items()}, indent=2))


if __name__ == "__main__":
    main()
