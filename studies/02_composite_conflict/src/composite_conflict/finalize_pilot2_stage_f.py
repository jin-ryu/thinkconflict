"""Materialize audited Stage F judgments and cross-model gate metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parent_id(instance_id: str) -> str:
    if "::single::" in instance_id:
        return instance_id.split("::single::", 1)[0]
    return instance_id.removesuffix("::order_reverse")


def evidence_order(instance_id: str) -> str:
    return "reverse" if instance_id.endswith("::order_reverse") else "original"


def rate(success: int, n: int) -> dict[str, Any]:
    return {"n": n, "success": success, "rate": round(success / n, 4) if n else None}


def materialize_model(model_dir: Path) -> dict[str, Any]:
    audit = json.loads((model_dir / "manual_audit.json").read_text())
    direct = load_jsonl(model_dir / "raw/direct_outputs.jsonl")
    oracle = load_jsonl(model_dir / "raw/oracle_unit_policy_outputs.jsonl")

    atomic_failures = audit["atomic_failures"]
    direct_failures = audit["direct_failures"]
    oracle_failures = audit["oracle_failures"]
    rows: list[dict[str, Any]] = []

    for output in direct:
        instance_id = output["instance_id"]
        if output["K"] == 1:
            failure = atomic_failures.get(instance_id)
            kind = "atomic"
        else:
            failure = direct_failures.get(instance_id)
            kind = "direct_composite"
        rows.append({
            "run_id": output["run_id"],
            "instance_id": instance_id,
            "parent_instance_id": parent_id(instance_id),
            "trial_kind": kind,
            "evidence_order": evidence_order(instance_id),
            "semantic_success": failure is None,
            "error_type": failure["error_type"] if failure else None,
            "rationale": failure["rationale"] if failure else "The response satisfies the query-grounded unit resolution(s).",
            "review_route": "Codex semantic review" if failure or output["K"] == 2 else "high-confidence lexical pass",
            "judge": audit["judge"],
        })

    for output in oracle:
        instance_id = output["instance_id"]
        failure = oracle_failures.get(instance_id)
        rows.append({
            "run_id": output["run_id"],
            "instance_id": instance_id,
            "parent_instance_id": parent_id(instance_id),
            "trial_kind": "oracle_composite",
            "evidence_order": evidence_order(instance_id),
            "semantic_success": failure is None,
            "error_type": failure["error_type"] if failure else None,
            "rationale": failure["rationale"] if failure else "The response satisfies both query-grounded unit resolutions with unit behaviors supplied.",
            "review_route": "Codex semantic review" if failure else "lexical pass with boundary audit",
            "judge": audit["judge"],
        })

    dump_jsonl(model_dir / "semantic_judgments.jsonl", rows)
    atomic = [row for row in rows if row["trial_kind"] == "atomic"]
    direct_rows = [row for row in rows if row["trial_kind"] == "direct_composite"]
    oracle_rows = [row for row in rows if row["trial_kind"] == "oracle_composite"]
    atomic_by_parent: dict[str, list[bool]] = {}
    for row in atomic:
        atomic_by_parent.setdefault(row["parent_instance_id"], []).append(row["semantic_success"])

    composition_specific = [
        row for row in direct_rows
        if not row["semantic_success"] and all(atomic_by_parent[row["parent_instance_id"]])
    ]
    direct_lookup = {(row["evidence_order"], row["parent_instance_id"]): row for row in direct_rows}
    oracle_lookup = {(row["evidence_order"], row["parent_instance_id"]): row for row in oracle_rows}
    parents = sorted({row["parent_instance_id"] for row in direct_rows})
    flips = [parent for parent in parents if direct_lookup[("original", parent)]["semantic_success"] != direct_lookup[("reverse", parent)]["semantic_success"]]
    direct_failed_keys = {key for key, row in direct_lookup.items() if not row["semantic_success"]}
    direct_success_keys = set(direct_lookup) - direct_failed_keys

    metrics = {
        "model": direct[0]["model"],
        "inference_control": {
            "temperature": direct[0].get("temperature"),
            "seed": direct[0].get("seed"),
            "disable_thinking": direct[0].get("disable_thinking"),
            "reasoning_effort": direct[0].get("reasoning_effort"),
        },
        "atomic": rate(sum(row["semantic_success"] for row in atomic), len(atomic)),
        "direct": {
            order: rate(sum(row["semantic_success"] for row in direct_rows if row["evidence_order"] == order), 24)
            for order in ("original", "reverse")
        },
        "direct_pooled_order_trials_not_independent": rate(sum(row["semantic_success"] for row in direct_rows), len(direct_rows)),
        "composition_specific_failures": {
            "count": len(composition_specific),
            "rate_over_order_trials": round(len(composition_specific) / len(direct_rows), 4),
            "error_types": dict(Counter(row["error_type"] for row in composition_specific)),
        },
        "order_sensitivity": {
            "parents_with_flip": len(flips),
            "rate": round(len(flips) / len(parents), 4),
            "parent_ids": flips,
        },
        "oracle_unit_policies": {
            order: rate(sum(row["semantic_success"] for row in oracle_rows if row["evidence_order"] == order), 24)
            for order in ("original", "reverse")
        },
        "oracle_pooled_order_trials_not_independent": rate(sum(row["semantic_success"] for row in oracle_rows), len(oracle_rows)),
        "oracle_effect_on_direct": {
            "rescued_direct_failures": sum(oracle_lookup[key]["semantic_success"] for key in direct_failed_keys),
            "direct_failures": len(direct_failed_keys),
            "regressed_direct_successes": sum(not oracle_lookup[key]["semantic_success"] for key in direct_success_keys),
        },
        "caveat": "Original and reverse trials reuse the same 24 parents and are not independent. Codex judgments are exploratory; publication claims require blind human validation.",
    }
    (model_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dirs", nargs="+", type=Path, required=True)
    parser.add_argument("--mistral-metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    added = [materialize_model(path) for path in args.model_dirs]
    mistral = json.loads(args.mistral_metrics.read_text())
    models = [{
        "model": "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
        "atomic": mistral["h2_within_instance_composition"]["single_units"],
        "direct_original": mistral["h2_within_instance_composition"]["original_composite"],
        "direct_reverse": mistral["h2_within_instance_composition"]["reverse_composite"],
        "composition_specific_failures": 48 - mistral["pooled_order_trials_not_independent"]["H2::direct"]["success"],
        "composition_specific_failure_rate": round((48 - mistral["pooled_order_trials_not_independent"]["H2::direct"]["success"]) / 48, 4),
        "order_flip_observed": mistral["h2_within_instance_composition"]["original_composite"]["success"] != mistral["h2_within_instance_composition"]["reverse_composite"]["success"],
    }]
    for item in added:
        models.append({
            "model": item["model"],
            "atomic": item["atomic"],
            "direct_original": item["direct"]["original"],
            "direct_reverse": item["direct"]["reverse"],
            "composition_specific_failures": item["composition_specific_failures"]["count"],
            "composition_specific_failure_rate": item["composition_specific_failures"]["rate_over_order_trials"],
            "order_flip_observed": item["order_sensitivity"]["parents_with_flip"] > 0,
            "error_types": item["composition_specific_failures"]["error_types"],
        })

    failure_gate_models = [row for row in models if row["composition_specific_failures"] >= 3 or row["composition_specific_failure_rate"] >= 0.10]
    added_common_errors = set(added[0]["composition_specific_failures"]["error_types"])
    for item in added[1:]:
        added_common_errors &= set(item["composition_specific_failures"]["error_types"])
    gate = {
        "at_least_two_models_show_composition_failure": len(failure_gate_models) >= 2,
        "minimum_three_or_ten_percent_per_model": len(failure_gate_models) == len(models),
        "common_error_type_across_added_families": sorted(added_common_errors),
        "order_flip_not_unique_to_one_model": sum(row["order_flip_observed"] for row in models) >= 2,
    }
    gate["stage_f_pass"] = all([
        gate["at_least_two_models_show_composition_failure"],
        gate["minimum_three_or_ten_percent_per_model"],
        bool(gate["common_error_type_across_added_families"]),
        gate["order_flip_not_unique_to_one_model"],
    ])
    result = {"models": models, "gate": gate, "interpretation": "Stage F tests cross-model existence and diagnostic plausibility, not a causal H effect. Proceeding to a larger K×H design is justified only as the next validation stage."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
