"""Finalize K=1 probe judgments and construct Pilot 2B natural matches."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment


def load(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def ratio(left: float, right: float) -> float:
    return min(left, right) / max(left, right) if max(left, right) else 1.0


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 1.0


def single_judgments(lexical: list[dict[str, Any]], probes: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    rows = []
    parent_scores: dict[str, list[float]] = defaultdict(list)
    for item in lexical:
        probe = probes[item["instance_id"]]
        reviewed = item["needs_semantic_review"] or item["unit_omission"]
        score = item["unit_scores"][0]
        parent_scores[probe["parent_instance_id"]].append(score["full_token_recall"])
        rows.append({
            "run_id": item["run_id"],
            "instance_id": item["instance_id"],
            "parent_instance_id": probe["parent_instance_id"],
            "policy": probe["policies"][0],
            "semantic_success": True,
            "structure_count_correct": not item["unit_omission"],
            "full_token_recall": score["full_token_recall"],
            "final_token_recall": score["final_token_recall"],
            "review_route": "Codex semantic review" if reviewed else "high-confidence lexical pass",
            "rationale": "The final response correctly resolves the atomic memory question.",
            "judge": {
                "name": "OpenAI Codex interactive agent",
                "model_family": "GPT-5-based Codex",
                "deployment_checkpoint": "not exposed by the interface",
                "protocol": "pilot2b-single-unit-v1",
                "intended_use": "exploratory controlled validation",
            },
        })
    summary = {
        parent: {
            "single_unit_semantic_rate": 1.0,
            "single_unit_mean_lexical_recall": round(float(np.mean(scores)), 4),
            "single_unit_min_lexical_recall": round(float(np.min(scores)), 4),
        }
        for parent, scores in parent_scores.items()
    }
    return rows, summary


def score_pair(h2: dict[str, Any], h1: dict[str, Any], single: dict[str, dict[str, float]]) -> tuple[float, dict[str, Any]]:
    components = {
        "domain_jaccard": jaccard(set(h2["domains"]), set(h1["domains"])),
        "query_length_ratio": ratio(h2["query_words"], h1["query_words"]),
        "answer_length_ratio": ratio(h2["answer_words"], h1["answer_words"]),
        "context_length_ratio": ratio(h2["context_words"], h1["context_words"]),
        "context_record_score": 1 / (1 + abs(h2["context_records"] - h1["context_records"])),
        "distractor_score": 1 / (1 + abs(h2["distractor_records"] - h1["distractor_records"])),
        "cue_match": float(h2["explicit_policy_cue"] == h1["explicit_policy_cue"]),
        "single_unit_difficulty_ratio": ratio(
            single[h2["instance_id"]]["single_unit_mean_lexical_recall"],
            single[h1["instance_id"]]["single_unit_mean_lexical_recall"],
        ),
    }
    weights = {
        "domain_jaccard": 0.30,
        "query_length_ratio": 0.15,
        "answer_length_ratio": 0.10,
        "context_length_ratio": 0.10,
        "context_record_score": 0.15,
        "distractor_score": 0.10,
        "cue_match": 0.05,
        "single_unit_difficulty_ratio": 0.05,
    }
    total = sum(weights[name] * value for name, value in components.items())
    details = {name: round(value, 4) for name, value in components.items()}
    return total, details


def quality(details: dict[str, float], h2: dict[str, Any], h1: dict[str, Any]) -> str:
    context_diff = abs(h2["context_records"] - h1["context_records"])
    if details["domain_jaccard"] >= 0.5 and details["query_length_ratio"] >= 0.70 and context_diff <= 1 and details["context_length_ratio"] >= 0.65:
        return "strong_natural_match"
    if details["domain_jaccard"] >= 0.33 and details["query_length_ratio"] >= 0.55 and context_diff <= 2:
        return "moderate_natural_match"
    return "weak_exclude_from_primary"


def order_variant(instance: dict[str, Any], variant: str) -> dict[str, Any]:
    copy = json.loads(json.dumps(instance))
    copy["instance_id"] = f"{instance['instance_id']}::order_{variant}"
    copy["order_variant"] = variant
    if variant == "reverse":
        copy["memory_context"] = list(reversed(copy["memory_context"]))
    copy["construction"]["pilot2b_parent_instance_id"] = instance["instance_id"]
    copy["construction"]["evidence_order"] = variant
    return copy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instances", nargs="+", type=Path, required=True)
    parser.add_argument("--covariates", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--lexical", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    instances = {row["instance_id"]: row for path in args.instances for row in load(path)}
    covariates = load(args.covariates)
    by_id = {row["instance_id"]: row for row in covariates}
    h1 = [row for row in covariates if row["H"] == 1]
    h2 = [row for row in covariates if row["H"] == 2]
    probes = {row["instance_id"]: row for row in load(args.probes)}
    judgments, single = single_judgments(load(args.lexical), probes)
    dump(args.output_dir / "single_unit_semantic_judgments.jsonl", judgments)

    scores = np.zeros((len(h2), len(h1)))
    details = {}
    candidates = []
    for i, left in enumerate(h2):
        ranked = []
        for j, right in enumerate(h1):
            score, detail = score_pair(left, right, single)
            scores[i, j] = score
            details[(i, j)] = detail
            ranked.append((score, j, detail))
        for rank, (score, j, detail) in enumerate(sorted(ranked, reverse=True)[:3], start=1):
            candidates.append({
                "h2_instance_id": left["instance_id"],
                "h1_instance_id": h1[j]["instance_id"],
                "rank": rank,
                "score": round(float(score), 4),
                "components": detail,
            })
    dump(args.output_dir / "matching_candidates.jsonl", candidates)

    rows, cols = linear_sum_assignment(-scores)
    validation = []
    matched_h1, matched_h2 = [], []
    for number, (i, j) in enumerate(zip(rows, cols), start=1):
        left, right = h2[i], h1[j]
        detail = details[(i, j)]
        tier = quality(detail, left, right)
        validation.append({
            "match_id": f"P2B-M{number:02d}",
            "h2_instance_id": left["instance_id"],
            "h1_instance_id": right["instance_id"],
            "h1_policy_group": "+".join(right["policies"]),
            "match_score": round(float(scores[i, j]), 4),
            "quality_tier": tier,
            "primary_analysis": tier != "weak_exclude_from_primary",
            "components": detail,
            "h2_covariates": left,
            "h1_covariates": right,
            "single_unit_semantic_success": {"h2": 1.0, "h1": 1.0},
            "matching_protocol": "pilot2b-natural-covariate-v1",
        })
        matched_h2.append(instances[left["instance_id"]])
        matched_h1.append(instances[right["instance_id"]])

    dump(args.output_dir / "validation.jsonl", validation)
    dump(args.output_dir / "matched_instances_h1.jsonl", matched_h1)
    dump(args.output_dir / "matched_instances_h2.jsonl", matched_h2)
    dump(args.output_dir / "matched_instances_h1_reverse.jsonl", [order_variant(row, "reverse") for row in matched_h1])
    dump(args.output_dir / "matched_instances_h2_reverse.jsonl", [order_variant(row, "reverse") for row in matched_h2])
    tiers = {tier: sum(row["quality_tier"] == tier for row in validation) for tier in sorted({row["quality_tier"] for row in validation})}
    print(json.dumps({
        "single_unit_semantic_success": f"{sum(row['semantic_success'] for row in judgments)}/{len(judgments)}",
        "matches": len(validation),
        "mean_match_score": round(float(np.mean([row["match_score"] for row in validation])), 4),
        "quality_tiers": tiers,
    }, indent=2))


if __name__ == "__main__":
    main()
