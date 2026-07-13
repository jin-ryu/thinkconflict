"""공통 CSV 계층: 전처리 파이프라인의 중간 표현 (사람이 읽고 고치는 형식).

파이프라인은 세 단계이며, **중간 산출물은 전부 CSV**다. JSONL은 마지막에만 나온다:

    1) draft   원본 → `<ds>.draft.csv`   규칙이 아는 것만 채우고 나머지는 빈칸
    2) llm     빈칸 채움 → `<ds>.llm.csv`  LLM 초벌 (RAMDocs는 채울 빈칸이 없어 생략)
    3) build   사람 확정 → `<ds>.jsonl`    최종본. CSV의 값을 그대로 읽어 만든다

**채우는 칸은 하나뿐이다.** 문서 라벨은 `label`, QACC 판정은 `verdict`·`conflict_type`.
규칙이 확정한 값은 미리 채워져 있고, LLM은 **빈칸만** 메우며, 사람은 아무 칸이나 고쳐 쓴다
(맨 나중에 쓴 값이 그대로 최종본이 된다 — 우선순위 규칙 같은 건 없다).

`*_source` 열은 그 값을 누가 넣었는지 기록하는 **참고용**이다(rule / llm / 빈칸=사람).
파이프라인은 이 열을 읽어 판정에 쓰지 않고, build 리포트에만 쓴다.

CSV는 **청크 1개 = 1행**이고, 문항 수준 필드(question, correct_answer 등)는 행마다 반복된다.
Excel/Numbers로 열어 정렬·필터하며 검토할 수 있다.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from preprocessing.schema import CHUNK_LABELS, Chunk, Item

# 청크 1개 = 1행. 앞쪽은 문항 수준(행마다 반복), 뒤쪽은 청크 수준.
COLUMNS = [
    # ── 문항 수준 ────────────────────────────────────────────────────────────
    "question_id", "dataset", "question",
    "conflict_type",                # 👈 채우는 칸 (규칙 초벌값이 들어 있음, 고쳐 써도 된다)
    "conflict_type_source",         # 참고: rule / llm / 빈칸=사람
    "correct_answer",               # 👈 채우는 칸: 원본 정답. 오타면 여기서 직접 고친다
    "verdict",                      # 👈 채우는 칸: QACC 게이트 ① (sharp / soft)
    "verdict_source",               # 참고: rule / llm / 빈칸=사람
    "exclusion_flag",               # 규칙이 붙인 제외·보류 사유
    # ── 청크 수준 ────────────────────────────────────────────────────────────
    "doc_id", "date", "url", "supported_answer",
    "label",                        # 👈 채우는 칸 (correct / conflict / noise)
    "label_source",                 # 참고: rule / llm / 빈칸=사람
    "rule_hint",                    # 규칙의 참고 신호 (matched_older / unmatched) — 확정 아님
    "text",                         # 문서 본문 (판단 근거)
    "note",                         # 검토자 메모 (파이프라인은 읽지 않음)
]
VALID_LABELS = tuple(l for l in CHUNK_LABELS if l != "unknown")


def _cell(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def write_csv(items: list[Item], path: str | Path, *,
              hints: dict[str, dict] | None = None) -> None:
    """Item 목록을 검토용 CSV로 쓴다. 규칙이 확정한 값은 채워지고 나머지는 빈칸이다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hints = hints or {}
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM: Excel 한글 대응
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for it in items:
            item_hints = hints.get(it.question_id, {})
            verdict = it.meta.get("screen_verdict", "")
            for c in it.chunks:
                known = c.label != "unknown"
                w.writerow({
                    "question_id": it.question_id,
                    "dataset": it.dataset,
                    "question": it.question,
                    "conflict_type": it.conflict_type,
                    "conflict_type_source": "rule",
                    "correct_answer": it.correct_answers[0] if it.correct_answers else "",
                    "verdict": verdict,
                    "verdict_source": "rule" if verdict else "",
                    "exclusion_flag": it.exclusion_flag or "",
                    "doc_id": c.doc_id,
                    "date": c.date or "",
                    "url": c.url or "",
                    "supported_answer": c.supported_answer or "",
                    "label": c.label if known else "",       # 미확정은 빈칸
                    "label_source": "rule" if known else "",
                    "rule_hint": item_hints.get(c.doc_id) or item_hints.get(str(c.doc_id)) or "",
                    "text": c.text,
                    "note": "",
                })


def read_csv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict], path: str | Path,
               extra_columns: list[str] | None = None) -> None:
    """행을 그대로 다시 쓴다. extra_columns로 판정자별 열(judge1_verdict 등)을 덧붙인다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = {k for r in rows for k in r}                       # 이미 있는 열 보존(재개 시)
    cols = COLUMNS + [c for c in (extra_columns or []) if c not in COLUMNS]
    cols += [c for c in sorted(seen) if c not in cols]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})


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
        if _cell(head, "verdict"):
            meta["screen_verdict"] = _cell(head, "verdict")
        notes = [_cell(r, "note") for r in entry["rows"] if _cell(r, "note")]
        if notes:
            meta["review_notes"] = notes

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


def label_provenance(rows: list[dict]) -> dict[str, int]:
    """label을 누가 채웠는지 집계 — build 리포트용.

    사람이 빈칸을 채우면 label_source는 빈 채로 남으므로 'human'으로 센다.
    (사람이 LLM 값을 덮어쓴 경우는 source가 llm으로 남아 구분되지 않는다 — 참고 지표다.)"""
    counts = {"rule": 0, "llm": 0, "human": 0, "unresolved": 0}
    for r in rows:
        if _cell(r, "label") not in VALID_LABELS:
            counts["unresolved"] += 1
            continue
        src = _cell(r, "label_source")
        counts[src if src in ("rule", "llm") else "human"] += 1
    return counts
