"""QACC 전처리: conflict_type 부여 + 스크리닝 게이트 (계획서 Phase 1-2, §3.1.3(4)).

사전등록된 스크리닝 게이트(사전등록 §3.3) — 통과분만 채점 트랙 투입:
    ① sharp/soft 재분류 — LLM 판정자 2종으로 진짜 사실 모순(sharp)만 선별,
       사이비 충돌(granularity·표기 변형, 예: "September 1915" vs "25 September 1915") 드롭.
       ※ 유료 API 판정자는 비용 예측·승인 후에만 집행 (--estimate-cost로 먼저 산정).
    ② DRAGged 질문 중복 제거 (실측 47건; 판정 불일치 27건은 경계 사례로 별도 보고)
    ③ correctAnswer 재검증 (주석자 1인 라벨 — 판정자·인간 스팟체크)
    ④ 문서 길이 공변량 기록 (스니펫 중앙값 27단어 — 분리 보고 사유)
    ⑤ 셔플링·표준 렌더링은 serving 단계에서 공통 적용

CLI 서브커맨드:
    convert        — 원본 → 공통 스키마 초안 (귀속 주석 → chunk 라벨 승계, 사유 → conflict_type)
    estimate-cost  — 게이트 ① LLM 판정 비용 예측 (승인 절차용; API 호출 없음)
    screen         — 게이트 ①~③ 적용 (판정 결과 시트 필요) → 검토 시트 갱신
    final          — 게이트 통과분 확정 → data/processed/qacc.jsonl

usage: python -m preprocessing.qacc_prep {convert|estimate-cost|screen|final}
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from preprocessing.schema import Chunk, Item, read_jsonl, write_jsonl

# 정답 선택 사유 라벨 → 공통 conflict_type (원문 표기는 convert 시 실측 확인)
REASON_TO_TYPE = {
    "recency": "temporal",     # 최신성 사유 48건 — 자연 시간 근거 보조 (§5)
    "majority": "misinfo",
    "source": "misinfo",
    "common sense": "misinfo",
}
JUDGE_SHEET = Path("preprocessing/review/qacc_screen.csv")


def load_raw(raw_dir: Path) -> list[dict]:
    candidates = sorted(p for p in raw_dir.rglob("*.json*") if ".git" not in p.parts)
    if not candidates:
        raise FileNotFoundError(f"{raw_dir}에 원본 없음 — data/raw/download.sh 먼저 실행")
    path = candidates[0]
    text = path.read_text(encoding="utf-8").strip()
    rows = ([json.loads(l) for l in text.splitlines() if l.strip()]
            if path.suffix == ".jsonl" else json.loads(text))
    if isinstance(rows, dict):
        rows = rows.get("data", list(rows.values())[0])
    print(f"원본 로드: {path} (N={len(rows)})")
    return rows


def norm_q(q: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()


def reason_to_type(row: dict) -> str:
    reason = str(row.get("reason", row.get("answer_reason", ""))).lower()
    for key, val in REASON_TO_TYPE.items():
        if key in reason:
            return val
    return "misinfo"  # 사유 불명 사실 충돌의 보수적 기본값 — screen 단계에서 재검


def build_items(rows: list[dict]) -> list[Item]:
    """충돌 문항만 공통 스키마로 변환. 귀속 주석(어느 문맥이 어느 답 지지)을 라벨로 승계."""
    items = []
    for i, row in enumerate(rows):
        answers = row.get("answers", row.get("conflicting_answers", []))
        if not row.get("is_conflict", len(answers) > 1):
            continue
        gold = row.get("correctAnswer", row.get("correct_answer"))
        chunks = []
        for j, ctx in enumerate(row.get("contexts", row.get("search_results", []))):
            supported = ctx.get("supported_answer", ctx.get("answer"))
            label = "noise"
            if supported and gold:
                label = "correct" if norm_q(str(supported)) == norm_q(str(gold)) else "conflicting"
            chunks.append(Chunk(
                doc_id=j, text=ctx.get("text", ctx.get("snippet", "")),
                url=ctx.get("url"), title=ctx.get("title"),
                date=ctx.get("date"), supported_answer=supported,
            ))
            chunks[-1].label = label
        items.append(Item(
            question_id=f"qacc-{i:04d}",
            dataset="qacc",
            question=row["question"],
            conflict_type=reason_to_type(row),
            correct_answers=[gold] if gold else [],
            chunks=chunks,
            behavior_track=False,  # 게이트 통과 후 final에서 확정
            self_consistency_track=True,
            meta={"source_row": i,
                  "n_conflicting_answers": len(answers),
                  "doc_len_words": [len(c.text.split()) for c in chunks],  # 게이트 ④ 공변량
                  "raw_reason": row.get("reason")},
        ))
    return items


def dedup_against_dragged(items: list[Item], dragged_path: Path) -> tuple[list[Item], int]:
    """게이트 ②: DRAGged 질문 중복 제거. 중복분은 meta에 보존해 경계 사례 보고에 쓴다."""
    if not dragged_path.exists():
        print(f"경고: {dragged_path} 없음 — 중복 제거를 건너뜀 (dragged draft 먼저 생성)")
        return items, 0
    dragged_qs = {norm_q(it.question) for it in read_jsonl(dragged_path)}
    kept = [it for it in items if norm_q(it.question) not in dragged_qs]
    return kept, len(items) - len(kept)


def estimate_cost(items: list[Item]) -> None:
    """게이트 ① 판정 비용 예측 — 유료 API 집행 전 승인 절차 (계획서 Phase 1-2)."""
    n = len(items)
    avg_in = sum(sum(m for m in it.meta["doc_len_words"]) for it in items) / max(n, 1)
    # 판정자 2종 × 문항 전량, 문항당 입력 ≈ 질문+문서(단어→토큰 1.4배)+프롬프트 500tok, 출력 ≈ 150tok
    tok_in = int(n * 2 * (avg_in * 1.4 + 500))
    tok_out = n * 2 * 150
    print(f"게이트 ① 판정 대상 N={n} (중복 제거 후), 판정자 2종")
    print(f"예상 토큰: 입력 ~{tok_in:,} / 출력 ~{tok_out:,}")
    print("→ 사용할 판정자 모델 단가를 곱해 승인 요청 후 집행할 것 (사전등록 §3.3)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["convert", "estimate-cost", "screen", "final"])
    ap.add_argument("--raw-dir", default="data/raw/qacc", type=Path)
    ap.add_argument("--out-dir", default="data/processed", type=Path)
    ap.add_argument("--dragged-draft", default="data/processed/dragged.draft.jsonl", type=Path)
    args = ap.parse_args()
    draft_path = args.out_dir / "qacc.draft.jsonl"

    if args.stage == "convert":
        items = build_items(load_raw(args.raw_dir))
        items, n_dup = dedup_against_dragged(items, args.dragged_draft)
        write_jsonl(items, draft_path)
        print(f"초안 생성: {draft_path} (충돌 N={len(items)}, DRAGged 중복 제거 {n_dup}건 — 실측 기대 47)")
    elif args.stage == "estimate-cost":
        estimate_cost(list(read_jsonl(draft_path)))
    elif args.stage == "screen":
        # LLM 판정자 2종의 sharp/soft 판정은 diagnosis.labeler의 judge 인터페이스를 재사용해
        # JUDGE_SHEET(question_id, judge1, judge2, human_spotcheck)로 저장한 뒤 이 단계를 실행한다.
        raise SystemExit(f"판정 시트 {JUDGE_SHEET} 작성 후 구현 단계 진행 (Phase 1-2; 비용 승인 선행)")
    else:  # final
        if not JUDGE_SHEET.exists():
            raise SystemExit(f"게이트 ① 판정 시트 없음: {JUDGE_SHEET} — screen 단계 선행")
        import csv
        sharp = {r["question_id"] for r in csv.DictReader(open(JUDGE_SHEET, encoding="utf-8"))
                 if r.get("verdict", "").strip() == "sharp"}
        items = []
        for it in read_jsonl(draft_path):
            if it.question_id in sharp:
                it.behavior_track = bool(it.correct_answers)
                it.meta["screen"] = "sharp"
                items.append(it)
        write_jsonl(items, args.out_dir / "qacc.jsonl")
        print(f"확정: qacc.jsonl (게이트 통과 N={len(items)} — 보수 가정 ~167)")


if __name__ == "__main__":
    main()
