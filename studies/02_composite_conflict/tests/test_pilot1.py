from composite_conflict.agreement import match_units
from composite_conflict.schema import (
    blank_annotation,
    derive_k_h,
    finalize_annotation,
    validate_annotation,
)


def _unit(unit_id: str, operator: str = "VERIFY_PREFER") -> dict:
    return {
        "unit_id": unit_id,
        "question_slot": "slot",
        "claim_groups": [
            {"claim": "a", "doc_ids": ["1"]},
            {"claim": "b", "doc_ids": ["2"]},
        ],
        "relation": "CONTRADICT_FACT",
        "operator": operator,
        "operator_precondition": "compare evidence",
        "evidence_conditions": [],
    }


def test_derive_k_h_counts_distinct_operators():
    annotation = {"conflict_units": [_unit("u1"), _unit("u2"), _unit("u3", "SUPERSEDE")]}
    assert derive_k_h(annotation) == (3, 2, ["SUPERSEDE", "VERIFY_PREFER"])


def test_finalize_and_validate_complete_annotation():
    annotation = blank_annotation("x-1", "A")
    annotation["status"] = "complete"
    annotation["conflict_units"] = [_unit("u1")]
    annotation = finalize_annotation(annotation)
    assert validate_annotation(annotation, valid_doc_ids={"1", "2"}, require_complete=True) == []


def test_validate_rejects_unknown_document():
    annotation = blank_annotation("x-1", "A")
    annotation["status"] = "complete"
    annotation["conflict_units"] = [_unit("u1")]
    annotation = finalize_annotation(annotation)
    errors = validate_annotation(annotation, valid_doc_ids={"1"}, require_complete=True)
    assert any("unknown doc_ids" in error for error in errors)


def test_unit_matching_is_one_to_one():
    left = [_unit("u1"), _unit("u2")]
    right = [_unit("v1")]
    assert len(match_units(left, right)) == 1
