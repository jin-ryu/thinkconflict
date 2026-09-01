"""Finalize manually audited semantic metrics for Pilot 2B."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


REVERSE_FAILURES = {
    ("direct", "40f2307d-0db0-8a7b-8187-c4162af0dad9:S50:Q_005+Q_006"): ("wrong_preference_selection", "Selected Racing Games instead of Animal Crossing."),
    ("direct", "575f4af8-5ca4-716c-dfed-0f495c945e0b:S47:Q_002+Q_003"): ("cross_unit_contamination", "Selected the partner's recipe instead of the user's sashimi preference."),
    ("direct", "c2efaebe-0dd4-c0dc-23a5-7d713b14c99f:S51:Q_006+Q_007"): ("wrong_preference_selection", "Selected Chrysanthemum Tea instead of Herbal Tea."),
    ("direct", "5c2a85a4-05a5-5a54-5f50-8029bff79f8f:S44:Q_003+Q_007"): ("wrong_preference_selection", "Selected a tropical getaway rather than the budget-hostel conference condition."),
    ("direct", "f398d596-a91e-2afd-605f-be545475deca:S48:Q_002+Q_003"): ("wrong_preference_selection", "Selected a casual walk and cargo pants instead of a workout and gym tank."),
    ("oracle_unit_policies", "bb30a4e6-6a50-79c4-5c45-ca6d0b4f97be:S52:Q_002+Q_004"): ("condition_over_preservation", "Returned steamed fish as an extra alternative instead of selecting only garden salad."),
    ("oracle_unit_policies", "c2efaebe-0dd4-c0dc-23a5-7d713b14c99f:S51:Q_006+Q_007"): ("wrong_preference_selection", "Selected Chrysanthemum Tea instead of Herbal Tea."),
    ("oracle_unit_policies", "5c2a85a4-05a5-5a54-5f50-8029bff79f8f:S44:Q_003+Q_007"): ("wrong_preference_selection", "Selected a tropical getaway despite the oracle unit behavior."),
    ("oracle_unit_policies", "c2efaebe-0dd4-c0dc-23a5-7d713b14c99f:S51:Q_002+Q_007"): ("condition_over_preservation", "Returned both Chrysanthemum and Herbal Tea instead of the query-matched Herbal Tea."),
    ("oracle_unit_policies", "f398d596-a91e-2afd-605f-be545475deca:S48:Q_002+Q_003"): ("wrong_preference_selection", "Selected cycling and cargo pants instead of a workout and gym tank."),
}


def load(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parent_id(instance_id: str) -> str:
    return instance_id.removesuffix("::order_reverse")


def rate(success: int, n: int) -> dict[str, Any]:
    return {"n": n, "success": success, "rate": round(success / n, 4) if n else None}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        key = f"{row['evidence_order']}::H{row['H']}::{row['baseline_condition']}"
        buckets[key].append(row["semantic_all_unit_success"])
    by_order = {key: rate(sum(values), len(values)) for key, values in sorted(buckets.items())}

    pooled_buckets: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        pooled_buckets[f"H{row['H']}::{row['baseline_condition']}"] .append(row["semantic_all_unit_success"])
    pooled = {key: rate(sum(values), len(values)) for key, values in sorted(pooled_buckets.items())}
    return {"by_evidence_order": by_order, "pooled_order_trials_not_independent": pooled}


def matched_summary(rows: list[dict[str, Any]], validation: list[dict[str, Any]], tier: str) -> dict[str, Any]:
    if tier == "primary":
        pairs = [row for row in validation if row["primary_analysis"]]
    else:
        pairs = [row for row in validation if row["quality_tier"] == tier]
    lookup = {(row["evidence_order"], row["baseline_condition"], row["parent_instance_id"]): row for row in rows}
    result = {"pairs": len(pairs), "orders": {}}
    for order in ("original", "reverse"):
        h1 = [lookup[(order, "direct", pair["h1_instance_id"])]["semantic_all_unit_success"] for pair in pairs]
        h2 = [lookup[(order, "direct", pair["h2_instance_id"])]["semantic_all_unit_success"] for pair in pairs]
        result["orders"][order] = {
            "H1": rate(sum(h1), len(h1)),
            "H2": rate(sum(h2), len(h2)),
            "delta_h2_minus_h1": round(sum(h2) / len(h2) - sum(h1) / len(h1), 4) if h1 else None,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-judgments", type=Path, required=True)
    parser.add_argument("--reverse-outputs", type=Path, required=True)
    parser.add_argument("--single-judgments", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    args = parser.parse_args()

    core = {"direct", "oracle_unit_policies"}
    rows = []
    for item in load(args.base_judgments):
        if item["baseline_condition"] not in core:
            continue
        rows.append({
            **item,
            "parent_instance_id": item["instance_id"],
            "evidence_order": "original",
            "review_protocol": "pilot2 semantic core v1",
        })

    for output in load(args.reverse_outputs):
        condition = output["baseline_condition"]
        if condition not in core:
            continue
        parent = parent_id(output["instance_id"])
        failure = REVERSE_FAILURES.get((condition, parent))
        rows.append({
            "run_id": output["run_id"],
            "instance_id": output["instance_id"],
            "parent_instance_id": parent,
            "H": output["H"],
            "baseline_condition": condition,
            "evidence_order": "reverse",
            "semantic_all_unit_success": failure is None,
            "error_type": failure[0] if failure else None,
            "rationale": failure[1] if failure else "Both gold units are resolved and composed in the final answer.",
            "review_route": "Codex semantic review",
            "judge": {
                "name": "OpenAI Codex interactive agent",
                "model_family": "GPT-5-based Codex",
                "deployment_checkpoint": "not exposed by the interface",
                "protocol": "pilot2b-reverse-semantic-v1",
                "intended_use": "exploratory controlled validation",
            },
        })
    dump(args.judgments, rows)

    metrics = summarize(rows)
    direct = [row for row in rows if row["baseline_condition"] == "direct"]
    lookup = {(row["evidence_order"], row["parent_instance_id"]): row for row in direct}
    h2_parents = sorted({row["parent_instance_id"] for row in direct if row["H"] == 2})
    metrics["h2_within_instance_composition"] = {
        "single_units": rate(sum(row["semantic_success"] for row in load(args.single_judgments) if row["parent_instance_id"] in h2_parents), 2 * len(h2_parents)),
        "original_composite": rate(sum(lookup[("original", parent)]["semantic_all_unit_success"] for parent in h2_parents), len(h2_parents)),
        "reverse_composite": rate(sum(lookup[("reverse", parent)]["semantic_all_unit_success"] for parent in h2_parents), len(h2_parents)),
        "failed_original_despite_both_single_success": sum(not lookup[("original", parent)]["semantic_all_unit_success"] for parent in h2_parents),
        "failed_both_orders_despite_both_single_success": sum(not lookup[("original", parent)]["semantic_all_unit_success"] and not lookup[("reverse", parent)]["semantic_all_unit_success"] for parent in h2_parents),
    }
    validation = load(args.validation)
    metrics["natural_matched_primary"] = matched_summary(rows, validation, "primary")
    metrics["natural_matched_strong_only"] = matched_summary(rows, validation, "strong_natural_match")
    metrics["matching_quality"] = {
        "total": len(validation),
        "strong": sum(row["quality_tier"] == "strong_natural_match" for row in validation),
        "moderate": sum(row["quality_tier"] == "moderate_natural_match" for row in validation),
        "weak_excluded": sum(row["quality_tier"] == "weak_exclude_from_primary" for row in validation),
    }
    metrics["interpretation_caveat"] = "Natural matching retains residual task differences. Original and reverse trials reuse the same instances and are not independent. Codex judgments are exploratory and not a substitute for blind human validation."
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
