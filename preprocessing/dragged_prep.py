"""DRAGged 전처리: 골드 매핑 초안 → 사람 전수 검토 시트 → 확정 (계획서 Phase 1-3, §3.1.1).

3단계 파이프라인 (CLI 서브커맨드):
    draft   — 문자열·앵커 토큰 매칭(+선택적 NLI/LLM 초벌)으로 정답 문서 자동 매핑 초안 생성.
              복수 매칭은 제외가 아니라 `date` 최신성으로 해소(사전등록 §3.2). 해소 불가만 플래그.
    sheet   — 행동 주장이 걸린 사실 충돌(temporal+misinfo) 전수 인간 검토 시트(CSV) 생성.
              정답 오탈자 정오표("Boston Celtis" 등) 교정 컬럼 포함.
    final   — 검토 완료 시트(preprocessing/review/dragged_review.csv)를 반영해
              data/processed/dragged.jsonl 확정. 검토 이력 자체가 산출물로 커밋된다.

usage: python -m preprocessing.dragged_prep {draft|sheet|final} [--raw-dir ...] [--out-dir ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from dateutil import parser as dateparser
from rapidfuzz import fuzz

from preprocessing.schema import Chunk, Item, read_jsonl, write_jsonl

CONFLICT_TYPE_MAP = {  # 원본 conflict_type 문구 → 공통 스키마 (원문 표기는 draft 시 실측 확인)
    "outdated": "temporal",
    "misinformation": "misinfo",
    "opinion": "opinion",
    "complementary": "complementary",
    "no conflict": "none",
}
FACT_CONFLICT_TYPES = ("temporal", "misinfo")  # 행동(정확도·AIR) 트랙 대상 67건
FUZZ_THRESHOLD = 85  # 앵커 토큰 부분 일치 임계 (초안용 — 확정은 인간 검증)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def map_conflict_type(raw: str) -> str:
    raw_l = raw.lower()
    for key, val in CONFLICT_TYPE_MAP.items():
        if key in raw_l:
            return val
    raise ValueError(f"미지의 conflict_type: {raw!r} — CONFLICT_TYPE_MAP 갱신 필요")


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


def match_answer(answer: str, doc_text: str) -> bool:
    """문자열 포함 또는 앵커 토큰 fuzzy 매칭 (초안 단계)."""
    a, t = norm(answer), norm(doc_text)
    if a in t:
        return True
    return fuzz.partial_ratio(a, t) >= FUZZ_THRESHOLD


def parse_date(s: str | None):
    try:
        return dateparser.parse(s) if s else None
    except (ValueError, OverflowError):
        return None


def resolve_by_recency(matched: list[Chunk]) -> tuple[list[int], str | None]:
    """복수 매칭 해소: date 최신 문서를 correct로 선정 (사전등록 §3.2).

    반환: (correct로 확정할 doc_id 목록, exclusion_flag 또는 None).
    날짜 동률·전부 부재면 해소 불가 → 플래그."""
    dated = [(c, parse_date(c.date)) for c in matched]
    with_date = [(c, d) for c, d in dated if d is not None]
    if not with_date:
        return [], "date_absent"
    latest = max(d for _, d in with_date)
    winners = [c.doc_id for c, d in with_date if d == latest]
    if len(winners) < len(matched) or len(winners) == 1:
        return winners, None
    return [], "date_tie"


def build_draft(rows: list[dict]) -> list[Item]:
    items = []
    for i, row in enumerate(rows):
        ctype = map_conflict_type(row["conflict_type"])
        chunks = [
            Chunk(doc_id=j, text=d["text"], date=d.get("date"),
                  url=d.get("url"), title=d.get("title"))
            for j, d in enumerate(row["search_results"])
        ]
        answer = row["correct_answer"]
        flag = None
        if ctype in FACT_CONFLICT_TYPES:
            matched = [c for c in chunks if match_answer(answer, c.text)]
            if not matched:
                flag = "no_match"
            elif len(matched) == 1:
                matched[0].label = "correct"
            else:  # 복수 매칭 = 해소 대상 (시간 충돌에서 구조적으로 정상, 실측 79%)
                winners, flag = resolve_by_recency(matched)
                for c in matched:
                    c.label = "correct" if c.doc_id in winners else "conflicting"
            for c in chunks:
                if c.label == "unknown":
                    c.label = "conflicting" if c in matched else "noise"
        elif ctype == "none":
            for c in chunks:  # 비충돌: 문서 일치 → 매핑 자명 (§3.1.1)
                c.label = "correct" if match_answer(answer, c.text) else "noise"
        items.append(Item(
            question_id=f"dragged-{i:04d}",
            dataset="dragged",
            question=row["question"],
            conflict_type=ctype,
            correct_answers=[answer],
            chunks=chunks,
            behavior_track=False,  # 확정은 final 단계 (인간 검증 후)
            self_consistency_track=ctype in ("temporal", "misinfo", "opinion"),
            exclusion_flag=flag,
            meta={"source_row": i, "raw_conflict_type": row["conflict_type"],
                  "mapping": "draft-string-fuzz"},
        ))
    return items


def export_review_sheet(items: list[Item], out_csv: Path) -> None:
    """사실 충돌 전수 인간 검토 시트. 검토자는 doc 라벨 교정 + 정답 정오표를 기입한다."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["question_id", "conflict_type", "question", "correct_answer",
                    "corrected_answer(정오표: 수정 시만)", "doc_id", "date", "url",
                    "draft_label", "final_label(correct/conflicting/noise)", "note"])
        for it in items:
            if it.conflict_type not in FACT_CONFLICT_TYPES:
                continue
            for c in it.chunks:
                w.writerow([it.question_id, it.conflict_type, it.question,
                            it.correct_answers[0], "", c.doc_id, c.date or "",
                            c.url or "", c.label, "", it.exclusion_flag or ""])
    print(f"검토 시트 생성: {out_csv}")


def finalize(items: list[Item], review_csv: Path) -> list[Item]:
    """검토 시트의 final_label·정오표를 반영하고 behavior_track을 확정한다."""
    if not review_csv.exists():
        raise FileNotFoundError(f"검토 완료 시트 없음: {review_csv}")
    fixes: dict[str, dict] = {}
    with open(review_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            qid = row["question_id"]
            fixes.setdefault(qid, {"labels": {}, "answer": None})
            final = row.get("final_label(correct/conflicting/noise)", "").strip()
            if final:
                fixes[qid]["labels"][int(row["doc_id"])] = final
            corr = row.get("corrected_answer(정오표: 수정 시만)", "").strip()
            if corr:
                fixes[qid]["answer"] = corr
    for it in items:
        fix = fixes.get(it.question_id)
        if fix:
            for c in it.chunks:
                if c.doc_id in fix["labels"]:
                    c.label = fix["labels"][c.doc_id]
            if fix["answer"]:
                it.meta["answer_errata"] = it.correct_answers[0]
                it.correct_answers = [fix["answer"]]
            it.meta["mapping"] = "human-verified"
        if it.conflict_type in FACT_CONFLICT_TYPES:
            it.behavior_track = (it.exclusion_flag is None
                                 and any(c.label == "correct" for c in it.chunks))
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["draft", "sheet", "final"])
    ap.add_argument("--raw-dir", default="data/raw/dragged", type=Path)
    ap.add_argument("--out-dir", default="data/processed", type=Path)
    ap.add_argument("--review-dir", default="preprocessing/review", type=Path)
    args = ap.parse_args()
    draft_path = args.out_dir / "dragged.draft.jsonl"
    if args.stage == "draft":
        items = build_draft(load_raw(args.raw_dir))
        write_jsonl(items, draft_path)
        flags = sum(1 for it in items if it.exclusion_flag)
        print(f"초안 생성: {draft_path} (N={len(items)}, 플래그 {flags}건)")
    elif args.stage == "sheet":
        export_review_sheet(list(read_jsonl(draft_path)),
                            args.review_dir / "dragged_review.csv")
    else:
        items = finalize(list(read_jsonl(draft_path)),
                         args.review_dir / "dragged_review.csv")
        write_jsonl(items, args.out_dir / "dragged.jsonl")
        n_behav = sum(1 for it in items if it.behavior_track)
        print(f"확정: dragged.jsonl (N={len(items)}, 채점 가능 {n_behav}건 — 예상 56~61)")


if __name__ == "__main__":
    main()
