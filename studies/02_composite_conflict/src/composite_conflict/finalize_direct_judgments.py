"""Validate and combine direct Codex judgments into the final Pilot-1 table."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .schema import read_jsonl, write_jsonl

MODEL = "OpenAI Codex interactive agent (GPT-5-based; exact deployment checkpoint unavailable)"
PROTOCOL = "strict-kh-direct-v1"
DATASET_LABELS = {"confrag": "ConfRAG", "natconfqa": "NatConfQA", "qacc": "QACC"}


def _views(pilot_root: Path) -> list[dict]:
    rows = []
    for name in (
        "confrag_prevalence_view.jsonl",
        "natconfqa_strict_wh_mix_view.jsonl",
        "qacc_control_view.jsonl",
    ):
        rows.extend(read_jsonl(pilot_root / name))
    return rows


def _judgments(pilot_root: Path) -> list[dict]:
    rows = []
    for path in sorted(pilot_root.glob("direct_judgments*.jsonl")):
        if path.name == "final_llm_judgments.jsonl":
            continue
        rows.extend(read_jsonl(path))
    return rows


def _validate(views: list[dict], rows: list[dict]) -> None:
    expected = [view["instance_id"] for view in views]
    counts = Counter(row["instance_id"] for row in rows)
    duplicates = sorted(key for key, value in counts.items() if value > 1)
    missing = sorted(set(expected) - set(counts))
    extra = sorted(set(counts) - set(expected))
    if duplicates or missing or extra:
        raise ValueError(f"duplicates={duplicates}, missing={missing}, extra={extra}")
    for row in rows:
        if row["H"] > row["K"]:
            raise ValueError(f"{row['instance_id']}: H cannot exceed K")
        if row["H"] != len(set(row["operators"])):
            raise ValueError(f"{row['instance_id']}: H/operator mismatch")
        if row["K"] == 0 and row["operators"]:
            raise ValueError(f"{row['instance_id']}: K=0 cannot have operators")


def _summary(rows: list[dict], dataset: str) -> dict:
    selected = [row for row in rows if row["dataset"] == dataset]
    return {
        "n": len(selected),
        "k": dict(sorted(Counter(row["K"] for row in selected).items())),
        "h": dict(sorted(Counter(row["H"] for row in selected).items())),
        "operators": dict(Counter(op for row in selected for op in row["operators"])),
        "confidence": dict(Counter(row["confidence"] for row in selected)),
        "composite": sum(row["K"] > 1 and row["H"] > 1 for row in selected),
    }


def _markdown(rows: list[dict]) -> str:
    summaries = {dataset: _summary(rows, dataset) for dataset in DATASET_LABELS}
    lines = [
        "# Pilot 1 최종 LLM 직접 판정표",
        "",
        "> 상태: 빠른 exploratory go/no-go 판정. 인간 검토·human-human IAA가 없으므로 gold benchmark가 아니다.",
        "",
        "## 실행 정보",
        "",
        f"- 판정 모델: `{MODEL}`",
        f"- 판정 protocol: `{PROTOCOL}`",
        "- 판정 방식: 자동 open-LLM API가 아니라 Codex가 질문·answer cluster·문서 snippet을 직접 읽고 strict K/H 기준으로 판정",
        "- 표본: ConfRAG 무작위 120 + NatConfQA strict WH-mix 22 + QACC 무작위 60 = 202건",
        "- 주의: 정확한 내부 checkpoint ID와 raw model trace는 제공되지 않으므로 완전 재현 가능한 자동 judge 결과가 아니다.",
        "",
        "## 핵심 결과",
        "",
        "| 데이터셋 | 표집 성격 | N | K=0 | K=1 | K>1,H>1 | 결론 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    roles = {
        "confrag": "자연 web 무작위 prevalence",
        "natconfqa": "conflict/non-conflict pair 혼합 선별",
        "qacc": "factual 대조 무작위",
    }
    for dataset, label in DATASET_LABELS.items():
        s = summaries[dataset]
        lines.append(
            f"| {label} | {roles[dataset]} | {s['n']} | {s['k'].get(0, 0)} | "
            f"{s['k'].get(1, 0)} | {s['composite']} | strict 복합 충돌 미관측 |"
        )
    lines.extend(
        [
            "",
            "세 표본은 표집 방식이 달라 pooled prevalence를 계산하지 않는다. 핵심 prevalence 표본인 ConfRAG에서는 120건 중 0건이므로, 현재 데이터와 strict 정의는 ‘자연 검색에서 K>1,H>1이 충분히 흔하다’는 주장을 지지하지 않는다. 0/120의 양측 95% Wilson 상한은 약 3.1%다.",
            "",
            "여러 answer cluster가 있어도 대부분은 (a) 보완 정보, (b) 하나의 모호한 answer slot을 scope/time으로 조건화하는 K=1 사례, 또는 (c) 동일 사실값의 K=1 대립이었다. 한 slot의 일반 효과와 세부 수치를 억지로 별도 unit으로 나누지 않았다.",
            "",
            "## Operator 분포",
            "",
            "| 데이터셋 | CONDITION | KEEP_BOTH | VERIFY_PREFER | SUPERSEDE | ABSTAIN_QUALIFY |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset, label in DATASET_LABELS.items():
        ops = summaries[dataset]["operators"]
        lines.append(
            f"| {label} | {ops.get('CONDITION', 0)} | {ops.get('KEEP_BOTH', 0)} | "
            f"{ops.get('VERIFY_PREFER', 0)} | {ops.get('SUPERSEDE', 0)} | "
            f"{ops.get('ABSTAIN_QUALIFY', 0)} |"
        )
    lines.extend(
        [
            "",
            "## 연구 판단",
            "",
            "현재 결과만으로는 자연 prevalence를 주요 동기로 삼는 ‘복합 충돌 해결 파이프라인’ 논문을 그대로 진행하기 어렵다. 다음 단계는 무작위 표본을 더 늘리기보다, 하나의 질문에 독립 answer slot이 둘 이상 존재하도록 설계된 multi-part QA 또는 여러 원자료 instance를 근거 보존 방식으로 조합한 controlled composite benchmark를 구축하고, 자연 retrieval log에서 외적 타당성을 별도 확인하는 방향이 더 타당하다.",
            "",
            "정의를 사후에 넓혀 complementary information이나 한 slot의 여러 하위 수치를 K>1로 세면 사례 수는 증가하지만, ‘독립 core conflict unit’이라는 원래 기여가 약해지므로 권장하지 않는다.",
            "",
            "## 전체 판정표",
            "",
            "| ID | Dataset | K | H | Operator | 확신도 | 판정 근거 |",
            "|---|---|---:|---:|---|---|---|",
        ]
    )
    for row in rows:
        rationale = row["rationale"].replace("|", "\\|").replace("\n", " ")
        operators = ", ".join(row["operators"]) or "-"
        lines.append(
            f"| `{row['instance_id']}` | {DATASET_LABELS[row['dataset']]} | {row['K']} | "
            f"{row['H']} | {operators} | {row['confidence']} | {rationale} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-root", type=Path, default=Path("data/pilot1"))
    parser.add_argument("--out", type=Path, default=Path("data/pilot1/final_llm_judgments.jsonl"))
    parser.add_argument(
        "--report", type=Path, default=Path("results/pilot1/final_llm_judgment_table.md")
    )
    args = parser.parse_args()

    views = _views(args.pilot_root)
    rows = _judgments(args.pilot_root)
    _validate(views, rows)
    by_id = {row["instance_id"]: row for row in rows}
    ordered = [by_id[view["instance_id"]] for view in views]
    for row in ordered:
        row["judge_model"] = MODEL
        row["protocol"] = PROTOCOL
    write_jsonl(ordered, args.out)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(_markdown(ordered), encoding="utf-8")
    print(json.dumps({dataset: _summary(ordered, dataset) for dataset in DATASET_LABELS}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
