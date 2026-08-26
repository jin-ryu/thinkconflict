"""Pilot-1 sidecar annotation schema and validation.

The source records remain immutable. Human annotations are linked by
``instance_id`` and K/H are always derived from conflict units and operators.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

RELATIONS = (
    "COMPLEMENT",
    "TEMPORAL_UPDATE",
    "SCOPE_CONDITIONED",
    "PERSPECTIVE_DISAGREEMENT",
    "CONTRADICT_FACT",
    "UNRESOLVED",
)

CORE_OPERATORS = (
    "MERGE",
    "SUPERSEDE",
    "CONDITION",
    "KEEP_BOTH",
    "VERIFY_PREFER",
    "ABSTAIN_QUALIFY",
)

EVIDENCE_CONDITIONS = (
    "IRRELEVANT",
    "INSUFFICIENT",
    "DEPENDENT_DUPLICATE",
    "LOW_CREDIBILITY",
)

ANNOTATION_VERSION = "kh-pilot-v2"


def read_jsonl(path: str | Path) -> Iterator[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc


def write_jsonl(records: Iterable[dict], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def document_ids(view: dict) -> set[str]:
    return {str(document["doc_id"]) for document in view.get("documents", [])}


def derive_k_h(annotation: dict) -> tuple[int, int, list[str]]:
    units = annotation.get("conflict_units", [])
    operators = sorted({unit.get("operator") for unit in units if unit.get("operator")})
    return len(units), len(operators), operators


def finalize_annotation(annotation: dict) -> dict:
    result = dict(annotation)
    k, h, operators = derive_k_h(result)
    result["K"] = k
    result["operator_set"] = operators
    result["H"] = h
    return result


def blank_annotation(instance_id: str, annotator_id: str) -> dict:
    return {
        "instance_id": instance_id,
        "annotation_version": ANNOTATION_VERSION,
        "annotator_id": annotator_id,
        "status": "pending",
        "conflict_units": [],
        "instance_evidence_conditions": [],
        "K": 0,
        "operator_set": [],
        "H": 0,
        "notes": "",
    }


def _claim_doc_ids(unit: dict) -> set[str]:
    ids: set[str] = set()
    for group in unit.get("claim_groups", []):
        ids.update(str(value) for value in group.get("doc_ids", []))
    return ids


def validate_annotation(
    annotation: dict,
    *,
    valid_doc_ids: set[str] | None = None,
    require_complete: bool = False,
) -> list[str]:
    errors: list[str] = []
    instance_id = annotation.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id.strip():
        errors.append("instance_id is required")
    if annotation.get("annotation_version") != ANNOTATION_VERSION:
        errors.append(f"annotation_version must be {ANNOTATION_VERSION}")
    if not str(annotation.get("annotator_id", "")).strip():
        errors.append("annotator_id is required")
    if annotation.get("status") not in {"pending", "complete", "excluded"}:
        errors.append("status must be pending, complete, or excluded")
    if require_complete and annotation.get("status") not in {"complete", "excluded"}:
        errors.append("annotation is not complete")

    units = annotation.get("conflict_units")
    if not isinstance(units, list):
        errors.append("conflict_units must be a list")
        units = []

    seen_unit_ids: set[str] = set()
    for index, unit in enumerate(units, start=1):
        prefix = f"unit[{index}]"
        unit_id = str(unit.get("unit_id", "")).strip()
        if not unit_id:
            errors.append(f"{prefix}: unit_id is required")
        elif unit_id in seen_unit_ids:
            errors.append(f"{prefix}: duplicate unit_id {unit_id}")
        seen_unit_ids.add(unit_id)
        if not str(unit.get("question_slot", "")).strip():
            errors.append(f"{prefix}: question_slot is required")
        if unit.get("relation") not in RELATIONS:
            errors.append(f"{prefix}: invalid relation {unit.get('relation')!r}")
        if unit.get("operator") not in CORE_OPERATORS:
            errors.append(f"{prefix}: invalid operator {unit.get('operator')!r}")
        groups = unit.get("claim_groups", [])
        if not isinstance(groups, list) or len(groups) < 2:
            errors.append(f"{prefix}: at least two claim_groups are required")
        for group_index, group in enumerate(groups, start=1):
            if not str(group.get("claim", "")).strip():
                errors.append(f"{prefix}.claim_group[{group_index}]: claim is required")
            ids = {str(value) for value in group.get("doc_ids", [])}
            if not ids:
                errors.append(f"{prefix}.claim_group[{group_index}]: doc_ids are required")
            if valid_doc_ids is not None and not ids <= valid_doc_ids:
                errors.append(
                    f"{prefix}.claim_group[{group_index}]: unknown doc_ids "
                    f"{sorted(ids - valid_doc_ids)}"
                )
        conditions = unit.get("evidence_conditions", [])
        for condition in conditions:
            label = condition if isinstance(condition, str) else condition.get("condition")
            if label not in EVIDENCE_CONDITIONS:
                errors.append(f"{prefix}: invalid evidence condition {label!r}")
        if valid_doc_ids is not None:
            unknown = _claim_doc_ids(unit) - valid_doc_ids
            if unknown:
                errors.append(f"{prefix}: unknown claim document ids {sorted(unknown)}")

    for condition in annotation.get("instance_evidence_conditions", []):
        label = condition if isinstance(condition, str) else condition.get("condition")
        if label not in EVIDENCE_CONDITIONS:
            errors.append(f"invalid instance evidence condition {label!r}")

    k, h, operators = derive_k_h(annotation)
    if annotation.get("K") != k:
        errors.append(f"K must be derived as {k}, got {annotation.get('K')!r}")
    if annotation.get("H") != h:
        errors.append(f"H must be derived as {h}, got {annotation.get('H')!r}")
    if annotation.get("operator_set") != operators:
        errors.append(f"operator_set must be {operators!r}")
    if h > k:
        errors.append(f"H={h} cannot exceed K={k}")
    return errors
