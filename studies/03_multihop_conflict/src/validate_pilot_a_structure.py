"""Run deterministic structural and provenance checks for Pilot A data."""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = STUDY_ROOT / "data" / "pilot_a"


def load_prepare_module():
    path = Path(__file__).with_name("prepare_pilot_a_data.py")
    spec = importlib.util.spec_from_file_location("prepare_pilot_a_data", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate() -> dict:
    prepare = load_prepare_module()
    meta = prepare.read_json(prepare.SOURCE_META_PATH)
    prepare.validate_source(meta)

    manifest = prepare.read_json(DATA_ROOT / "sample_manifest.json")
    candidates = read_jsonl(DATA_ROOT / "generated" / "audit_candidates.jsonl")
    controls = read_jsonl(DATA_ROOT / "generated" / "no_conflict_templates.jsonl")
    annotations = read_jsonl(DATA_ROOT / "review_annotations.jsonl")
    review_a = read_jsonl(DATA_ROOT / "review_A.jsonl")
    review_b = read_jsonl(DATA_ROOT / "review_B.jsonl")
    prescreen = read_jsonl(DATA_ROOT / "assistant_prescreen.jsonl")
    failures = []

    records = manifest["records"]
    primary = [record for record in records if record["role"] == "primary"]
    reserve = [record for record in records if record["role"] == "reserve"]
    ids = [record["instance_id"] for record in records]
    candidate_by_id = {record["instance_id"]: record for record in candidates}

    check(manifest["status"] == "provisional_pre_audit", "Unexpected manifest status", failures)
    check(len(primary) == 76, f"Expected 76 primary conflicts, got {len(primary)}", failures)
    check(len(reserve) == 38, f"Expected 38 reserves, got {len(reserve)}", failures)
    check(len(ids) == len(set(ids)), "Duplicate stable instance IDs", failures)
    check(set(ids) == set(candidate_by_id), "Manifest/candidate ID mismatch", failures)
    check(len(annotations) == len(records), "Annotation sidecar count mismatch", failures)
    check(len({row['instance_id'] for row in annotations}) == len(records), "Duplicate annotation IDs", failures)
    check(all(row.get("gold") is False for row in prescreen), "Assistant prescreen must remain non-gold", failures)
    check(len(review_a) == len(records), "Reviewer A sidecar count mismatch", failures)
    check(len(review_b) == len(records), "Reviewer B sidecar count mismatch", failures)
    check(all(row["annotator"] == "A" for row in review_a), "Reviewer A identity mismatch", failures)
    check(all(row["annotator"] == "B" for row in review_b), "Reviewer B identity mismatch", failures)

    expected_strata = {
        ("multi-hop", count): 15 for count in range(1, 5)
    } | {("single-hop", count): 4 for count in range(1, 5)}
    actual_strata = Counter((record["hop"], record["conflict_count"]) for record in primary)
    check(actual_strata == expected_strata, f"Primary stratum mismatch: {actual_strata}", failures)

    anchor_keys = []
    record_hash_failures = []
    noncanonical_primary = []
    empty_contexts = []
    for row in records:
        candidate = candidate_by_id[row["instance_id"]]
        raw = {
            key: candidate[key]
            for key in ("id", "rel_id", "subgraph", "original_triplet", "perturb_triplet", "context1", "context2")
        }
        if prepare.canonical_hash(raw) != row["source_record_sha256"]:
            record_hash_failures.append(row["instance_id"])
        if not candidate["context1"].strip() or not candidate["context2"].strip():
            empty_contexts.append(row["instance_id"])
        if row["role"] == "primary":
            originals = [
                prepare.parse_triplet(value)
                for value in prepare.triplet_list(candidate["original_triplet"])
            ]
            anchor_keys.append(
                "|".join(
                    sorted(
                        f"{prepare.normalize(subject)}>{prepare.normalize(obj)}"
                        for subject, _, obj in originals
                    )
                )
            )
            if candidate["coverage"]["noncanonical_triplet_arity"]:
                noncanonical_primary.append(row["instance_id"])

    check(not record_hash_failures, f"Source-record hash failures: {record_hash_failures}", failures)
    check(not empty_contexts, f"Empty contexts: {empty_contexts}", failures)
    check(len(anchor_keys) == len(set(anchor_keys)), "Duplicate primary original entity/path", failures)
    check(not noncanonical_primary, f"Noncanonical primary triplets: {noncanonical_primary}", failures)

    primary_ids = {record["instance_id"] for record in primary}
    check(len(controls) == 24, f"Expected 24 control templates, got {len(controls)}", failures)
    check(
        all(control["anchor_instance_id"] in primary_ids for control in controls),
        "Control anchor outside primary set",
        failures,
    )
    check(len({control["control_id"] for control in controls}) == 24, "Duplicate control IDs", failures)
    check(
        all(control["construction_status"] == "pending_human_construction" for control in controls),
        "Unexpected control construction state",
        failures,
    )

    lexical_warnings = [
        record["instance_id"] for record in primary if not record["coverage_heuristic_pass"]
    ]
    quartiles = Counter(record["length_quartile"] for record in primary)
    relations = Counter(record["relation_id"] for record in primary)
    result = {
        "validator_version": "pilot-a-structure-v1",
        "manifest_status": manifest["status"],
        "passed": not failures,
        "failures": failures,
        "counts": {
            "primary": len(primary),
            "reserve": len(reserve),
            "control_templates": len(controls),
            "annotations": len(annotations),
            "review_a": len(review_a),
            "review_b": len(review_b),
        },
        "primary_length_quartiles": dict(sorted(quartiles.items())),
        "primary_relation_types": len(relations),
        "lexical_warning_ids": lexical_warnings,
        "semantic_gates_not_covered": [
            "source_fact_coverage_human_confirmation",
            "proof_step_soundness",
            "terminal_incompatibility",
            "no_conflict_semantic_validation",
        ],
    }
    output = DATA_ROOT / "structural_validation.json"
    prepare.write_json(output, result)
    report = f"""# Pilot A structural validation

검증일: 2026-09-01

- 결과: **{'PASS' if result['passed'] else 'FAIL'}**
- Primary: {len(primary)}
- Reserve: {len(reserve)}
- No-conflict templates: {len(controls)}
- Stable IDㆍsource hashㆍ중복ㆍ빈 문맥ㆍ비정규 primary triplet: 검사 완료
- Lexical coverage 경고: {len(lexical_warnings)}건

이 PASS는 구조와 provenance만 뜻한다. Source fact coverage, proof-step soundness, terminal incompatibility, no-conflict consistency는 사람의 의미 판정 전까지 통과한 것으로 간주하지 않는다.
"""
    (DATA_ROOT / "structural_validation_report.md").write_text(report, encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
