"""Build the provisional MAGIC sample and human-audit scaffolding for Pilot A."""
from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

STUDY_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = STUDY_ROOT / "data" / "raw" / "magic"
OUT_ROOT = STUDY_ROOT / "data" / "pilot_a"
GENERATED_ROOT = OUT_ROOT / "generated"
SOURCE_META_PATH = STUDY_ROOT / "data" / "source_snapshots.json"
SEED = 20260901

FILE_SPECS = [
    ("multi-hop", 1, 300, 15, 5),
    ("multi-hop", 2, 158, 15, 5),
    ("multi-hop", 3, 80, 15, 5),
    ("multi-hop", 4, 50, 15, 15),
    ("single-hop", 1, 208, 4, 2),
    ("single-hop", 2, 154, 4, 2),
    ("single-hop", 3, 80, 4, 2),
    ("single-hop", 4, 50, 4, 2),
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def parse_triplet(value: str) -> tuple[str, str, str]:
    value = value.strip()
    inner = value[1:-1] if value.startswith("(") and value.endswith(")") else value
    parts = [part.strip() for part in inner.split("|")]
    if len(parts) < 3:
        raise ValueError(f"Invalid MAGIC triplet: {value!r}")
    return parts[0], " | ".join(parts[1:-1]), parts[-1]


def noncanonical_triplets(record: dict) -> list[str]:
    values = triplet_list(record["original_triplet"]) + triplet_list(record["perturb_triplet"])
    return [value for value in values if len(parse_triplet_parts(value)) != 3]


def parse_triplet_parts(value: str) -> list[str]:
    value = value.strip()
    inner = value[1:-1] if value.startswith("(") and value.endswith(")") else value
    return [part.strip() for part in inner.split("|")]


def triplet_list(value: str | list) -> list[str]:
    if isinstance(value, str):
        return [value]
    flattened = []
    for item in value:
        flattened.extend(triplet_list(item))
    return flattened


def endpoint_coverage(record: dict) -> dict:
    expected = []
    for triplet in triplet_list(record["original_triplet"]):
        subject, _, obj = parse_triplet(triplet)
        expected.extend((("context1", subject), ("context1", obj)))
    for triplet in triplet_list(record["perturb_triplet"]):
        subject, _, obj = parse_triplet(triplet)
        expected.extend((("context2", subject), ("context2", obj)))

    missing = []
    for context_field, endpoint in expected:
        if normalize(endpoint) not in normalize(record[context_field]):
            missing.append({"context": context_field, "endpoint": endpoint})
    return {
        "heuristic_pass": not missing,
        "missing_endpoints": missing,
        "noncanonical_triplet_arity": noncanonical_triplets(record),
        "warning": "Lexical endpoint coverage is only a triage heuristic, not proof-coverage gold.",
    }


def stable_id(hop: str, conflict_count: int, source_id: int) -> str:
    hop_code = "mh" if hop == "multi-hop" else "sh"
    return f"magic-{hop_code}-c{conflict_count}-id{source_id:04d}"


def enrich(records: list[dict], hop: str, conflict_count: int, source_file: str) -> list[dict]:
    lengths = [len((record["context1"] + " " + record["context2"]).split()) for record in records]
    ranked = sorted(range(len(records)), key=lambda index: (lengths[index], records[index]["id"]))
    quartile_by_index = {
        index: min(3, rank * 4 // len(records)) for rank, index in enumerate(ranked)
    }
    enriched = []
    for index, record in enumerate(records):
        originals = [parse_triplet(value) for value in triplet_list(record["original_triplet"])]
        anchor_parts = sorted(
            f"{normalize(subject)}>{normalize(obj)}" for subject, _, obj in originals
        )
        enriched.append(
            {
                "instance_id": stable_id(hop, conflict_count, int(record["id"])),
                "hop": hop,
                "conflict_count": conflict_count,
                "source_file": source_file,
                "source_id": record["id"],
                "relation_id": record["rel_id"],
                "context_token_proxy": lengths[index],
                "length_quartile": quartile_by_index[index] + 1,
                "anchor_key": "|".join(anchor_parts),
                "source_record_sha256": canonical_hash(record),
                "coverage": endpoint_coverage(record),
                "raw": record,
            }
        )
    return enriched


def relation_round_robin(records: list[dict], rng: random.Random) -> list[dict]:
    groups = defaultdict(list)
    for record in records:
        groups[record["relation_id"]].append(record)
    for values in groups.values():
        rng.shuffle(values)
    keys = list(groups)
    rng.shuffle(keys)
    ordered = []
    while keys:
        next_keys = []
        for key in keys:
            ordered.append(groups[key].pop())
            if groups[key]:
                next_keys.append(key)
        keys = next_keys
        rng.shuffle(keys)
    return ordered


def balanced_order(records: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_coverage = defaultdict(list)
    for record in records:
        by_coverage[bool(record["coverage"]["heuristic_pass"])].append(record)

    ordered = []
    for coverage_pass in (True, False):
        by_quartile = defaultdict(list)
        for record in by_coverage[coverage_pass]:
            by_quartile[record["length_quartile"]].append(record)
        quartile_queues = {
            quartile: relation_round_robin(values, rng)
            for quartile, values in by_quartile.items()
        }
        quartiles = [1, 2, 3, 4]
        while any(quartile_queues.get(q) for q in quartiles):
            for quartile in quartiles:
                if quartile_queues.get(quartile):
                    ordered.append(quartile_queues[quartile].pop(0))
            quartiles = quartiles[1:] + quartiles[:1]
    return ordered


def select_unique(records: list[dict], count: int) -> tuple[list[dict], list[dict]]:
    selected, duplicates = [], []
    seen = set()
    for record in records:
        if record["anchor_key"] in seen:
            duplicates.append(record)
            continue
        selected.append(record)
        seen.add(record["anchor_key"])
        if len(selected) == count:
            break
    if len(selected) != count:
        raise ValueError(f"Could select only {len(selected)} unique records; need {count}")
    return selected, duplicates


def public_record(record: dict, role: str, rank: int) -> dict:
    return {
        "instance_id": record["instance_id"],
        "role": role,
        "rank_within_file": rank,
        "hop": record["hop"],
        "conflict_count": record["conflict_count"],
        "source_file": record["source_file"],
        "source_id": record["source_id"],
        "relation_id": record["relation_id"],
        "length_quartile": record["length_quartile"],
        "context_token_proxy": record["context_token_proxy"],
        "coverage_heuristic_pass": record["coverage"]["heuristic_pass"],
        "source_record_sha256": record["source_record_sha256"],
    }


def generated_record(record: dict, selection_role: str) -> dict:
    result = public_record(record, selection_role, 0)
    result.update(record["raw"])
    result["coverage"] = record["coverage"]
    result["dataset_status"] = "provisional_pre_audit"
    return result


def merge_review_annotations(path: Path, candidates: list[dict]) -> None:
    existing = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                existing[value["instance_id"]] = value
    rows = []
    for candidate in candidates:
        instance_id = candidate["instance_id"]
        rows.append(
            existing.get(
                instance_id,
                {
                    "instance_id": instance_id,
                    "selection_role": candidate["selection_role"],
                    "decision": "pending",
                    "exclusion_reasons": [],
                    "proof_facts_present_in_raw": None,
                    "graph_to_text_error": None,
                    "duplicate_entity_or_path": None,
                    "reviewer": None,
                    "notes": "",
                },
            )
        )
    write_jsonl(path, rows)


def merge_gate_annotations(path: Path, candidates: list[dict], annotator: str) -> None:
    existing = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                existing[value["instance_id"]] = value
    rows = []
    for candidate in candidates:
        instance_id = candidate["instance_id"]
        rows.append(
            existing.get(
                instance_id,
                {
                    "instance_id": instance_id,
                    "selection_role": candidate["selection_role"],
                    "annotator": annotator,
                    "g1_source_fact_coverage": "pending",
                    "g2_graph_to_text_fidelity": "pending",
                    "g3_proof_step_soundness": "pending",
                    "g4_terminal_incompatibility": "pending",
                    "overall_decision": "pending",
                    "failing_proof_units": [],
                    "evidence_notes": "",
                    "reviewed_at": None,
                },
            )
        )
    write_jsonl(path, rows)


def validate_source(meta: dict) -> None:
    source = meta["sources"]["magic"]
    total = 0
    for relative_path, expected in source["files"].items():
        path = RAW_ROOT / relative_path
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}; run data/download.sh first")
        if sha256_file(path) != expected["sha256"]:
            raise ValueError(f"Checksum mismatch: {relative_path}")
        records = read_json(path)
        if len(records) != expected["records"]:
            raise ValueError(f"Record-count mismatch: {relative_path}")
        total += len(records)
    if total != source["records"]:
        raise ValueError(f"Total record-count mismatch: {total}")


def build() -> dict:
    meta = read_json(SOURCE_META_PATH)
    validate_source(meta)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    GENERATED_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    audit_candidates = []
    multihop_primary = []
    singlehop_primary = []
    control_templates = []

    for file_index, (hop, conflict_count, expected_count, primary_n, reserve_n) in enumerate(FILE_SPECS):
        relative_path = f"{hop}/{conflict_count}-{hop}_conflict.json"
        records = read_json(RAW_ROOT / relative_path)
        if len(records) != expected_count:
            raise ValueError(f"Unexpected count in {relative_path}")
        enriched = enrich(records, hop, conflict_count, relative_path)
        ordered = balanced_order(enriched, SEED + file_index * 1009)
        selected, duplicate_skips = select_unique(ordered, primary_n + reserve_n)
        primary, reserve = selected[:primary_n], selected[primary_n:]

        for rank, record in enumerate(primary, start=1):
            manifest_rows.append(public_record(record, "primary", rank))
            candidate = generated_record(record, "primary")
            candidate["selection_role"] = "primary"
            audit_candidates.append(candidate)
        for rank, record in enumerate(reserve, start=1):
            manifest_rows.append(public_record(record, "reserve", rank))
            candidate = generated_record(record, "reserve")
            candidate["selection_role"] = "reserve"
            audit_candidates.append(candidate)

        if hop == "multi-hop":
            multihop_primary.extend(generated_record(record, "primary") for record in primary)
            control_anchors = primary[:5]
        else:
            singlehop_primary.extend(generated_record(record, "primary") for record in primary)
            control_anchors = primary[:1]

        for index, anchor in enumerate(control_anchors, start=1):
            control_templates.append(
                {
                    "control_id": f"{anchor['instance_id']}-nc{index}",
                    "anchor_instance_id": anchor["instance_id"],
                    "hop": hop,
                    "conflict_count_stratum": conflict_count,
                    "relation_id": anchor["relation_id"],
                    "length_quartile": anchor["length_quartile"],
                    "target_context_token_proxy": anchor["context_token_proxy"],
                    "anchor_context1": anchor["raw"]["context1"],
                    "anchor_context2": anchor["raw"]["context2"],
                    "compatible_subgraph_candidates": anchor["raw"]["subgraph"],
                    "control_context2": None,
                    "construction_status": "pending_human_construction",
                    "review": {
                        "annotator_a_label": None,
                        "annotator_b_label": None,
                        "adjudicated_label": None,
                        "length_matched": None,
                        "entity_matched": None,
                        "no_label_artifact": None,
                        "notes": "",
                    },
                }
            )

        manifest_rows[-(primary_n + reserve_n)]["duplicate_anchor_candidates_skipped"] = len(duplicate_skips)

    manifest = {
        "manifest_version": "pilot-a-sample-v1",
        "status": "provisional_pre_audit",
        "seed": SEED,
        "source_revision": meta["sources"]["magic"]["revision"],
        "source_records": meta["sources"]["magic"]["records"],
        "selection": {
            "multi_hop_primary_conflicts": 60,
            "multi_hop_reserves": 30,
            "single_hop_primary_conflicts": 16,
            "single_hop_reserves": 8,
            "planned_multi_hop_controls": 20,
            "planned_single_hop_controls": 4,
        },
        "sampling": {
            "balanced_by": ["conflict_count", "context_length_quartile", "relation_id"],
            "unique_anchor_key": True,
            "coverage_heuristic_priority": True,
            "replacement_rule": "Use reserves in rank order after human exclusion.",
        },
        "records": manifest_rows,
    }
    write_json(OUT_ROOT / "sample_manifest.json", manifest)
    write_jsonl(GENERATED_ROOT / "audit_candidates.jsonl", audit_candidates)
    write_jsonl(GENERATED_ROOT / "multihop_conflicts.jsonl", multihop_primary)
    write_jsonl(GENERATED_ROOT / "singlehop_conflicts.jsonl", singlehop_primary)
    write_jsonl(GENERATED_ROOT / "no_conflict_templates.jsonl", control_templates)
    merge_review_annotations(OUT_ROOT / "review_annotations.jsonl", audit_candidates)
    merge_gate_annotations(OUT_ROOT / "review_A.jsonl", audit_candidates, "A")
    merge_gate_annotations(OUT_ROOT / "review_B.jsonl", audit_candidates, "B")

    primary = [row for row in manifest_rows if row["role"] == "primary"]
    relation_counts = Counter(row["relation_id"] for row in primary)
    quartile_counts = Counter(row["length_quartile"] for row in primary)
    heuristic_fails = [row["instance_id"] for row in primary if not row["coverage_heuristic_pass"]]
    noncanonical_primary = sum(
        bool(record["coverage"]["noncanonical_triplet_arity"])
        for record in audit_candidates
        if record["selection_role"] == "primary"
    )
    report = f"""# Pilot A dataset build report

생성일: 2026-09-01
상태: **provisional_pre_audit — 아직 모델 실행 금지**

## 구성 결과

| 구성 | primary | reserve | no-conflict template |
|---|---:|---:|---:|
| multi-hop | 60 | 30 | 20 |
| single-hop | 16 | 8 | 4 |
| 합계 | 76 | 38 | 24 |

최종 목표 100개는 conflict 76개와 paired no-conflict 24개다. 현재 conflict 표본은 구성됐지만 no-conflict는 template만 생성됐으므로 완성된 gold는 100개가 아니다.

## 자동 검사

- 원본: MAGIC revision `{meta['sources']['magic']['revision']}`
- 원본 checksum과 파일별 레코드 수: 통과
- stable ID와 source-record SHA-256: 생성
- primary 내 conflict-count 균형: multi-hop 파일별 15, single-hop 파일별 4
- primary length quartile 분포: `{dict(sorted(quartile_counts.items()))}`
- primary relation 종류: {len(relation_counts)}
- lexical endpoint coverage 경고: {len(heuristic_fails)}건
- noncanonical triplet arity 경고: {noncanonical_primary}건

11개 lexical 경고의 assistant prescreen에서는 별칭ㆍ표기 차이 5개와 proof fact 실제 누락 의심 6개를 구분했다. 이 판정은 `assistant_prescreen.jsonl`에 `gold=false`로 기록했으며 두 사람의 독립 판정을 대체하지 않는다.

Lexical coverage는 endpoint 문자열의 존재만 보는 triage다. 0건이어도 proof에 필요한 관계ㆍ조건이 모두 서술됐다는 뜻이 아니며, 사람의 proof-coverage 판정을 대체하지 않는다.

## 다음 gate

1. `review_annotations.jsonl`의 primary 76개를 두 사람이 확인한다.
2. 제외 사례는 같은 파일의 reserve rank 순서로 교체하고 manifest를 `frozen_post_audit`로 갱신한다.
3. `generated/no_conflict_templates.jsonl`의 24개 control을 작성하고 독립 합의한다.
4. 100개 모두에 gold certificate와 C0--C4를 작성한 뒤에만 모델 입력을 생성한다.
"""
    (OUT_ROOT / "dataset_report.md").write_text(report, encoding="utf-8")
    return manifest


if __name__ == "__main__":
    built = build()
    print(json.dumps(built["selection"], ensure_ascii=False, indent=2))
