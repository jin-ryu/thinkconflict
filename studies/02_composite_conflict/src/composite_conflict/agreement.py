"""Validate two completed annotation files and calculate Pilot-1 agreement."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.metrics import cohen_kappa_score, f1_score

from .schema import document_ids, read_jsonl, validate_annotation


def _index(path: Path) -> dict[str, dict]:
    records = list(read_jsonl(path))
    indexed = {record["instance_id"]: record for record in records}
    if len(indexed) != len(records):
        raise ValueError(f"{path}: duplicate instance_id")
    return indexed


def _unit_docs(unit: dict) -> set[str]:
    return {
        str(doc_id)
        for group in unit.get("claim_groups", [])
        for doc_id in group.get("doc_ids", [])
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def match_units(left: list[dict], right: list[dict], threshold: float = 0.5) -> list[tuple[dict, dict]]:
    candidates = []
    for left_index, left_unit in enumerate(left):
        for right_index, right_unit in enumerate(right):
            score = _jaccard(_unit_docs(left_unit), _unit_docs(right_unit))
            if score >= threshold:
                candidates.append((score, left_index, right_index))
    matches = []
    used_left: set[int] = set()
    used_right: set[int] = set()
    for _, left_index, right_index in sorted(candidates, reverse=True):
        if left_index in used_left or right_index in used_right:
            continue
        used_left.add(left_index)
        used_right.add(right_index)
        matches.append((left[left_index], right[right_index]))
    return matches


def _kappa_or_none(left: list, right: list, *, weights: str | None = None):
    if len(set(left) | set(right)) < 2:
        return None
    return float(cohen_kappa_score(left, right, weights=weights))


def calculate(view_path: Path, left_path: Path, right_path: Path) -> dict:
    views = _index(view_path)
    left = _index(left_path)
    right = _index(right_path)
    if set(left) != set(right) or set(left) != set(views):
        raise ValueError("view and annotation files must contain identical instance_id sets")

    errors = []
    for side, records in (("A", left), ("B", right)):
        for instance_id, record in records.items():
            for error in validate_annotation(
                record,
                valid_doc_ids=document_ids(views[instance_id]),
                require_complete=True,
            ):
                errors.append(f"{side}:{instance_id}: {error}")
    if errors:
        raise ValueError("invalid completed annotations:\n" + "\n".join(errors))

    ids = sorted(views)
    k_left = [left[key]["K"] for key in ids]
    k_right = [right[key]["K"] for key in ids]
    h_left = [left[key]["H"] for key in ids]
    h_right = [right[key]["H"] for key in ids]
    binary_left = [value > 1 for value in h_left]
    binary_right = [value > 1 for value in h_right]

    matched = []
    total_left = total_right = 0
    for key in ids:
        left_units = left[key]["conflict_units"]
        right_units = right[key]["conflict_units"]
        total_left += len(left_units)
        total_right += len(right_units)
        matched.extend(match_units(left_units, right_units))
    precision = len(matched) / total_right if total_right else 1.0
    recall = len(matched) / total_left if total_left else 1.0
    localization_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    relation_left = [pair[0]["relation"] for pair in matched]
    relation_right = [pair[1]["relation"] for pair in matched]
    operator_left = [pair[0]["operator"] for pair in matched]
    operator_right = [pair[1]["operator"] for pair in matched]
    result = {
        "n_instances": len(ids),
        "h_gt_1_kappa": _kappa_or_none(binary_left, binary_right),
        "k_weighted_kappa": _kappa_or_none(k_left, k_right, weights="quadratic"),
        "h_weighted_kappa": _kappa_or_none(h_left, h_right, weights="quadratic"),
        "k_exact_agreement": sum(a == b for a, b in zip(k_left, k_right)) / len(ids),
        "h_exact_agreement": sum(a == b for a, b in zip(h_left, h_right)) / len(ids),
        "unit_localization_precision": precision,
        "unit_localization_recall": recall,
        "unit_localization_f1": localization_f1,
        "matched_units": len(matched),
        "relation_macro_f1": f1_score(relation_left, relation_right, average="macro") if matched else None,
        "operator_macro_f1": f1_score(operator_left, operator_right, average="macro") if matched else None,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", required=True, type=Path)
    parser.add_argument("--annotator-a", required=True, type=Path)
    parser.add_argument("--annotator-b", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = calculate(args.view, args.annotator_a, args.annotator_b)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
