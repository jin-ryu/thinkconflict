"""공통 CSV 계층: 전처리 파이프라인의 중간 표현 (사람이 읽고 고치는 형식).

파이프라인은 세 단계이며, **중간 산출물은 전부 CSV**다. JSONL은 마지막에만 나온다:

    1) draft   원본 → `<ds>.draft.csv`   규칙이 아는 것만 채우고 나머지는 빈칸
    2) llm     빈칸 채움 → `<ds>.llm.csv`  LLM 초벌 (RAMDocs는 채울 빈칸이 없어 생략)
    3) build   사람 확정 → `<ds>.jsonl`    최종본. CSV의 값을 그대로 읽어 만든다

**CSV의 모든 열은 공통 스키마(schema.Item/Chunk)에 그대로 대응한다.** 보조 열은 두지 않는다 —
파이프라인 사정으로 만든 칸이 검토자의 시야를 어지럽히지 않게 하기 위함이다.

규칙이 아는 값은 미리 채워져 있고, LLM은 **빈칸만** 메우며, 사람은 아무 칸이나 고쳐 쓴다.
CSV에 적힌 값이 그대로 최종본이 된다 (우선순위 규칙 같은 건 없다).

CSV는 **청크 1개 = 1행**이고, 문항 수준 필드(question, correct_answer 등)는 행마다 반복된다.
Excel/Numbers로 열어 정렬·필터하며 검토할 수 있다.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from preprocessing.schema import CHUNK_LABELS, Chunk, Item

# 청크 1개 = 1행. 열은 전부 공통 스키마 필드다 (Item.* 또는 Chunk.*).
COLUMNS = [
    # ── 문항 수준 (Item) ─────────────────────────────────────────────────────
    "question_id", "dataset", "question",
    "conflict_type",     # 👈 채우는 칸: temporal / misinfo / opinion / complementary / none
    "correct_answer",    # 👈 채우는 칸: 정답. 오타면 여기서 직접 고친다 (Item.correct_answers)
    "exclusion_flag",    # 👈 채우는 칸: 채점 트랙 제외 사유. 비우면 트랙에 들어간다
    # ── 청크 수준 (Chunk) ────────────────────────────────────────────────────
    "doc_id", "date", "url", "supported_answer",
    "label",             # 👈 채우는 칸: correct / conflict / noise
    "text",              # 문서 본문 (판단 근거)
]
VALID_LABELS = tuple(l for l in CHUNK_LABELS if l != "unknown")

# QACC 게이트 ①(sharp/soft)은 별도 열이 아니라 exclusion_flag로 표현한다:
#   pending_screen — 아직 판정 안 됨 (기본값 → 채점 트랙 진입 불가)
#   soft_conflict  — 사이비 충돌(표기 차이)로 판정 → 드롭
#   (빈칸)         — sharp = 진짜 사실 모순 → 채점 트랙 진입
PENDING_SCREEN = "pending_screen"
SOFT_CONFLICT = "soft_conflict"


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def write_csv(items: list[Item], path: str | Path) -> None:
    """Item 목록을 검토용 CSV로 쓴다. 규칙이 확정한 값은 채워지고 나머지는 빈칸이다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM: Excel 한글 대응
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for it in items:
            for c in it.chunks:
                w.writerow({
                    "question_id": it.question_id,
                    "dataset": it.dataset,
                    "question": it.question,
                    "conflict_type": it.conflict_type,
                    "correct_answer": it.correct_answers[0] if it.correct_answers else "",
                    "exclusion_flag": it.exclusion_flag or "",
                    "doc_id": c.doc_id,
                    "date": c.date or "",
                    "url": c.url or "",
                    "supported_answer": c.supported_answer or "",
                    "label": "" if c.label == "unknown" else c.label,   # 미확정은 빈칸
                    "text": c.text,
                })


def read_csv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict], path: str | Path) -> None:
    """행을 그대로 다시 쓴다 (열 구성은 COLUMNS 고정 — 스키마 밖 열은 만들지 않는다)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def to_items(rows: list[dict], *,
             original_answers: dict[str, str] | None = None) -> list[Item]:
    """CSV 행 → Item 목록. CSV에 적힌 값을 그대로 읽는다 (우선순위 규칙 없음).

    `label`이 빈칸이거나 알 수 없는 값이면 `unknown`으로 두고, `unknown`이 남은 문항은
    채점 트랙에 들어가지 못한다(schema.validate_item이 막는다).

    부가 정보(문서 길이 공변량·오답 목록 등)는 별도 파일 없이 **CSV에서 직접 파생**한다.
    original_answers(초안 CSV의 정답)를 주면 사람이 고친 오타를 meta.answer_errata에 남긴다.
    """
    original_answers = original_answers or {}
    by_item: dict[str, dict] = {}
    for r in rows:
        by_item.setdefault(r["question_id"], {"rows": [], "first": r})["rows"].append(r)

    items = []
    for qid, entry in by_item.items():
        head = entry["first"]
        answer = _cell(head, "correct_answer")
        chunks = []
        for r in sorted(entry["rows"], key=lambda x: int(x["doc_id"])):
            label = _cell(r, "label")
            chunks.append(Chunk(
                doc_id=int(r["doc_id"]), text=r.get("text", ""),
                label=label if label in VALID_LABELS else "unknown",
                date=_cell(r, "date") or None, url=_cell(r, "url") or None,
                supported_answer=_cell(r, "supported_answer") or None,
            ))
        # 문서에 실린 오답 = 문서별 지지 답 중 정답이 아닌 것 (원본 귀속 주석에서 파생)
        wrong = sorted({(r.get("supported_answer") or "").strip()
                        for r in entry["rows"]} - {"", answer})
        meta = {
            "n_docs": len(chunks),                                   # RQ3 공변량
            "doc_len_words": [len(c.text.split()) for c in chunks],  # RQ3 공변량
        }
        original = original_answers.get(qid)
        if original is not None and answer != original:
            meta["answer_errata"] = original      # 사람이 정답 오타를 고쳤다 (원본 보존)

        items.append(Item(
            question_id=qid,
            dataset=head["dataset"],
            question=head["question"],
            conflict_type=_cell(head, "conflict_type"),
            correct_answers=[answer] if answer else [],
            wrong_answers=wrong,
            chunks=chunks,
            exclusion_flag=(_cell(head, "exclusion_flag") or None),
            meta=meta,
        ))
    return items


def original_answers(path: str | Path) -> dict[str, str]:
    """초안 CSV에서 문항별 원본 정답을 읽는다 (정오표 비교용).
    초안 CSV는 커밋되므로, 사람이 고친 값과 원본의 차이가 git에도 그대로 남는다."""
    p = Path(path)
    if not p.exists():
        return {}
    return {r["question_id"]: (r.get("correct_answer") or "").strip()
            for r in read_csv(p)}


def label_provenance(rows: list[dict], draft_rows: list[dict] | None = None) -> dict[str, int]:
    """라벨이 채워졌는지 집계 — build 리포트용.

    출처 열을 따로 두지 않으므로, 초안 CSV(draft_rows)와 대조해 '규칙이 채운 것'과
    '나중에 채워진 것(LLM·사람)'을 가른다. 누가 채웠는지의 정확한 이력은 git diff가 갖는다."""
    by_key = {(r["question_id"], r["doc_id"]): _cell(r, "label")
              for r in (draft_rows or [])}
    counts = {"rule": 0, "filled": 0, "unresolved": 0}
    for r in rows:
        label = _cell(r, "label")
        if label not in VALID_LABELS:
            counts["unresolved"] += 1
        elif by_key.get((r["question_id"], r["doc_id"])) == label:
            counts["rule"] += 1          # 초안과 같다 = 규칙이 채운 값 그대로
        else:
            counts["filled"] += 1        # LLM·사람이 채우거나 고친 값
    return counts
