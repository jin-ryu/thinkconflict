"""Audit the official ProofWriter archive for Pilot A source feasibility.

This script is model-free. It streams the OWA depth-5 dev/test JSONL files
from the official ZIP and records whether there are enough clean 1--4 hop
proofs to construct the controlled multi-document conflict pilot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

STUDY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = (
    STUDY_ROOT
    / "data/raw/proofwriter/proofwriter-dataset-V2020.12.3.zip"
)
DEFAULT_JSON = STUDY_ROOT / "data/proofwriter_feasibility.json"
DEFAULT_REPORT = STUDY_ROOT / "docs/proofwriter_feasibility.md"
ARCHIVE_SHA256 = "bbc5694901e8306d0bd659aa1ad53ccfd02c201864f4b320ffa3777827d1fc26"
ARCHIVE_URL = (
    "https://aristo-data-public.s3.amazonaws.com/proofwriter/"
    "proofwriter-dataset-V2020.12.3.zip"
)
MEMBERS = {
    "dev": "proofwriter-dataset-V2020.12.3/OWA/depth-5/meta-dev.jsonl",
    "test": "proofwriter-dataset-V2020.12.3/OWA/depth-5/meta-test.jsonl",
}
RULE_APPLICATION_RE = re.compile(r"rule\d+\s+%\s+int\d+")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def target_polarity(representation: str) -> str | None:
    matches = re.findall(r'"([+\-])"', representation)
    return matches[-1] if matches else None


def flip_polarity(representation: str) -> str:
    polarity = target_polarity(representation)
    if polarity is None:
        raise ValueError(f"No polarity in representation: {representation!r}")
    replacement = '"-"' if polarity == "+" else '"+"'
    return re.sub(r'"[+\-]"(?=\)$)', replacement, representation, count=1)


def rule_application_count(proof_representation: str) -> int:
    return len(RULE_APPLICATION_RE.findall(proof_representation))


def is_linear_depth_proof(question: dict[str, Any]) -> bool:
    qdep = question.get("QDep")
    if not isinstance(qdep, int) or qdep < 1:
        return False
    proofs = question.get("proofsWithIntermediates") or []
    return any(
        rule_application_count(proof.get("representation", "")) == qdep
        for proof in proofs
    )


def family_from_id(record_id: str) -> str:
    return record_id.split("-", 1)[0]


def clean_candidate(record: dict[str, Any], question: dict[str, Any]) -> bool:
    inverse = flip_polarity(question["representation"])
    fact_representations = {
        fact["representation"] for fact in record["triples"].values()
    }
    provable_representations = {
        detail["representation"] for detail in record.get("proofDetails", [])
    }
    return inverse not in fact_representations and inverse not in provable_representations


def audit(archive: Path) -> dict[str, Any]:
    actual_sha = sha256_file(archive)
    if actual_sha != ARCHIVE_SHA256:
        raise ValueError(
            f"ProofWriter archive checksum mismatch: {actual_sha} != {ARCHIVE_SHA256}"
        )

    records_by_split: Counter[str] = Counter()
    questions_by_depth: Counter[int] = Counter()
    true_proofs: Counter[tuple[str, int, str]] = Counter()
    linear_proofs: Counter[tuple[str, int, str]] = Counter()
    clean_linear_proofs: Counter[tuple[str, int, str]] = Counter()
    clean_by_family: Counter[tuple[int, str]] = Counter()
    schema_errors: list[str] = []
    example_ids: dict[str, list[dict[str, Any]]] = defaultdict(list)

    required_record_keys = {
        "id", "maxD", "theory", "triples", "rules", "questions", "proofDetails"
    }
    required_question_keys = {
        "question", "answer", "QDep", "QLen", "strategy", "representation"
    }

    with zipfile.ZipFile(archive) as bundle:
        archive_names = set(bundle.namelist())
        has_license_file = any(
            Path(name).name.lower() in {"license", "license.txt", "license.md", "copying"}
            for name in archive_names
        )
        readme = bundle.read(
            "proofwriter-dataset-V2020.12.3/README.md"
        ).decode("utf-8")
        readme_mentions_license = "license" in readme.lower()

        for split, member in MEMBERS.items():
            with bundle.open(member) as handle:
                for line_number, raw_line in enumerate(handle, 1):
                    record = json.loads(raw_line)
                    records_by_split[split] += 1
                    missing = required_record_keys - record.keys()
                    if missing:
                        schema_errors.append(
                            f"{split}:{line_number}:{record.get('id')}:record:{sorted(missing)}"
                        )
                        continue
                    family = family_from_id(record["id"])
                    for question_id, question in record["questions"].items():
                        q_missing = required_question_keys - question.keys()
                        if q_missing:
                            schema_errors.append(
                                f"{split}:{line_number}:{record['id']}:{question_id}:"
                                f"{sorted(q_missing)}"
                            )
                            continue
                        qdep = question["QDep"]
                        if isinstance(qdep, int):
                            questions_by_depth[qdep] += 1
                        if (
                            question["answer"] is not True
                            or question["strategy"] != "proof"
                            or qdep not in {1, 2, 3, 4}
                            or not question.get("proofsWithIntermediates")
                        ):
                            continue
                        polarity = target_polarity(question["representation"])
                        if polarity is None:
                            schema_errors.append(
                                f"{split}:{line_number}:{record['id']}:{question_id}:polarity"
                            )
                            continue
                        key = (split, qdep, polarity)
                        true_proofs[key] += 1
                        if not is_linear_depth_proof(question):
                            continue
                        linear_proofs[key] += 1
                        if not clean_candidate(record, question):
                            continue
                        clean_linear_proofs[key] += 1
                        clean_by_family[(qdep, family)] += 1
                        example_key = f"depth_{qdep}_{polarity}"
                        if len(example_ids[example_key]) < 5:
                            example_ids[example_key].append(
                                {
                                    "split": split,
                                    "theory_id": record["id"],
                                    "question_id": question_id,
                                    "question": question["question"],
                                    "qdep": qdep,
                                    "polarity": polarity,
                                }
                            )

    def nested(counter: Counter[tuple[str, int, str]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for (split, depth, polarity), count in sorted(counter.items()):
            result.setdefault(split, {}).setdefault(str(depth), {})[polarity] = count
        return result

    minimum_per_depth = {
        str(depth): min(
            sum(count for (split, dep, _), count in clean_linear_proofs.items() if split == "dev" and dep == depth),
            sum(count for (split, dep, _), count in clean_linear_proofs.items() if split == "test" and dep == depth),
        )
        for depth in (1, 2, 3, 4)
    }
    required = {"1": 20, "2": 20, "3": 20, "4": 20}
    enough = all(minimum_per_depth[depth] >= count for depth, count in required.items())

    return {
        "audit_version": "proofwriter-feasibility-v1",
        "checked_at": "2026-09-01",
        "source": {
            "url": ARCHIVE_URL,
            "release": "V2020.12.3",
            "archive_sha256": actual_sha,
            "archive_bytes": archive.stat().st_size,
            "audited_world": "OWA",
            "audited_dataset": "depth-5",
            "audited_splits": list(MEMBERS),
            "license_status": (
                "UNVERIFIED: official archive has no license file and its README does not "
                "state a license; do not redistribute original rows pending confirmation."
            ),
            "has_license_file": has_license_file,
            "readme_mentions_license": readme_mentions_license,
        },
        "schema": {
            "records_by_split": dict(records_by_split),
            "schema_error_count": len(schema_errors),
            "schema_error_examples": schema_errors[:20],
            "available_fields": [
                "theory", "triples", "rules", "questions", "QDep", "QLen",
                "strategy", "proofsWithIntermediates", "proofDetails",
            ],
        },
        "questions_by_qdep": {str(k): v for k, v in sorted(questions_by_depth.items())},
        "true_proof_candidates": nested(true_proofs),
        "linear_depth_candidates": nested(linear_proofs),
        "clean_linear_candidates": nested(clean_linear_proofs),
        "clean_candidates_by_depth_and_family": {
            str(depth): {
                family: clean_by_family[(depth, family)]
                for family in sorted({fam for dep, fam in clean_by_family if dep == depth})
            }
            for depth in (1, 2, 3, 4)
        },
        "minimum_clean_candidates_in_each_audited_split": minimum_per_depth,
        "pilot_requirement_per_depth": required,
        "feasibility_pass": enough and not schema_errors,
        "candidate_examples": dict(sorted(example_ids.items())),
        "selection_policy": {
            "world": "OWA only",
            "answer": True,
            "strategy": "proof",
            "depths": [1, 2, 3, 4],
            "linear_rule_application_filter": (
                "At least one proof has exactly QDep explicit rule applications."
            ),
            "clean_inverse_filter": (
                "The polarity-inverted target is neither an input fact nor independently provable."
            ),
        },
    }


def render_report(result: dict[str, Any]) -> str:
    source = result["source"]
    lines = [
        "# ProofWriter feasibility audit for Pilot A",
        "",
        "작성일: 2026-09-01  ",
        "상태: 모델 미사용 / 공식 아카이브 구조 검사 완료",
        "",
        "## 결론",
        "",
        (
            "**PASS.** ProofWriter OWA에는 Pilot A의 1--4 hop proof-valid 통제 사례를 만들기에 "
            "충분한 gold proof 후보가 있다."
            if result["feasibility_pass"]
            else "**FAIL.** 현재 선택 규칙으로는 필요한 후보 또는 schema 안정성이 부족하다."
        ),
        "",
        "ProofWriter는 원래 conflict 데이터셋이 아니다. 본 판정은 검증된 proof의 결론과 "
        "반대 claim을 별도 문서로 추가해 multi-hop inter-context conflict를 구성할 수 "
        "있는지를 확인한 것이다.",
        "",
        "## 공식 원본과 공개 제한",
        "",
        f"- release: `{source['release']}`",
        f"- archive SHA-256: `{source['archive_sha256']}`",
        f"- archive size: `{source['archive_bytes']}` bytes",
        f"- audited subset: `{source['audited_world']}/depth-5`, dev와 test",
        f"- license: {source['license_status']}",
        "",
        "따라서 연구 내부 변환과 평가는 진행하되, 원본 JSONL이나 원문을 저장소에 "
        "재배포하지 않는다. 공개 artifact는 source ID, 변환 코드, 비원문 통계와 "
        "라이선스 확인 뒤 허용되는 파생물로 제한한다.",
        "",
        "## Schema 검사",
        "",
        "| split | theory 수 |",
        "|---|---:|",
    ]
    for split, count in result["schema"]["records_by_split"].items():
        lines.append(f"| {split} | {count:,} |")
    lines.extend([
        "",
        f"Schema 오류: **{result['schema']['schema_error_count']}건**",
        "",
        "필요 필드인 facts, rules, query polarity, `QDep`, proof와 intermediate "
        "conclusion을 모두 확인했다. CWA의 negation-as-failure를 피하기 위해 OWA만 사용한다.",
        "",
        "## 깨끗한 선형 proof 후보",
        "",
        "아래 수치는 적어도 한 proof가 `QDep`와 같은 수의 명시적 rule application을 "
        "가지며, 반대 polarity target이 이미 주어졌거나 별도로 증명되지 않는 사례다.",
        "",
        "| hop | dev + | dev - | test + | test - | split별 최소 총수 | 필요 수 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ])
    clean = result["clean_linear_candidates"]
    for depth in (1, 2, 3, 4):
        d = str(depth)
        dev = clean.get("dev", {}).get(d, {})
        test = clean.get("test", {}).get(d, {})
        lines.append(
            f"| {depth} | {dev.get('+', 0):,} | {dev.get('-', 0):,} | "
            f"{test.get('+', 0):,} | {test.get('-', 0):,} | "
            f"{result['minimum_clean_candidates_in_each_audited_split'][d]:,} | "
            f"{result['pilot_requirement_per_depth'][d]} |"
        )
    lines.extend([
        "",
        "## 파일럿 선택 결정",
        "",
        "- 이 표의 `OWA/depth-5`는 1--4 hop proof 공급량과 schema 안정성을 확인하는 보조 검사다.",
        "- C0--C2의 실제 dry run은 crowdsourced paraphrase mapping이 있는 `OWA/NatLang`에서 고른다.",
        "- conflict core는 QDep 2ㆍ3ㆍ4에서 각 20개, single-hop calibration은 QDep 1에서 가져온다.",
        "- 같은 theory에서는 질문 하나만 채택한다.",
        "- 실제 문서 분할 뒤 어느 한 문서만으로 target이 증명되지 않는지 다시 검사한다.",
        "- symbolic replay와 paired no-conflict consistency는 별도 dry-run validator로 확인한다.",
        "",
        "## 아직 검증되지 않은 것",
        "",
        "- 여러 source document로 나눈 뒤의 proof 보존성",
        "- conflict/control의 표면 단서 균형",
        "- 합성 문장의 자연 문서 일반화",
        "- 원본ㆍ파생 데이터 재배포 권한",
        "",
        "20개 NatLang dry run과 symbolic validator 결과는 `data/pilot_a/`의 별도 보고서에 기록한다.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    result = audit(args.archive)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_report.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({
        "feasibility_pass": result["feasibility_pass"],
        "schema_error_count": result["schema"]["schema_error_count"],
        "minimum_clean_candidates_in_each_audited_split": result[
            "minimum_clean_candidates_in_each_audited_split"
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
