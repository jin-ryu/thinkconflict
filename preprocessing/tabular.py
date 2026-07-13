"""공통 CSV 계층: 전처리 파이프라인의 중간 표현 (사람이 읽고 고치는 형식).

파이프라인은 세 단계이며, **중간 산출물은 전부 CSV**다. JSONL은 마지막에만 나온다:

    1) draft   원본 → `<ds>.draft.csv`   규칙이 확정한 것만 채우고 나머지는 빈칸
    2) llm     빈칸 채움 → `<ds>.llm.csv`  LLM 초벌 제안 (RAMDocs는 채울 빈칸이 없어 생략)
    3) build   사람 확정 → `<ds>.jsonl`    최종본. CSV의 라벨을 그대로 읽어 만든다

CSV는 **청크 1개 = 1행**이고, 문항 수준 필드(question, correct_answer 등)는 행마다 반복된다.
Excel/Numbers로 열어 정렬·필터하며 검토할 수 있다.

라벨 우선순위 (build 시 적용): **final_* (사람) > llm_* (초벌) > rule_* (규칙)**.
사람이 빈칸으로 두면 LLM 제안이, LLM도 없으면 규칙 값이 쓰인다. 셋 다 없으면 `unknown`으로
남고, `unknown`이 있는 문항은 채점 트랙에 들어가지 못한다(schema.validate_item이 막는다).
"""
from __future__ import annotations

import csv
from pathlib import Path

from preprocessing.schema import CHUNK_LABELS, Chunk, Item

# 청크 1개 = 1행. 앞쪽은 문항 수준(행마다 반복), 뒤쪽은 청크 수준.
COLUMNS = [
    # ── 문항 수준 ────────────────────────────────────────────────────────────
    "question_id", "dataset", "question",
    "rule_conflict_type",           # 규칙/원본이 준 유형
    "llm_conflict_type",            # LLM 초벌 (QACC)
    "final_conflict_type",          # 사람 확정 (빈칸이면 위 값 사용)
    "correct_answer",               # 원본 정답
    "corrected_answer",             # 정오표: 원본 정답에 오타가 있을 때만 기입
    "wrong_answers",                # 문서에 실린 오답들 ('|'로 구분, 부가 관측용)
    "llm_verdict",                  # QACC 게이트 ①: sharp / soft (LLM)
    "final_verdict",                # QACC 게이트 ①: 사람 확정
    "exclusion_flag",               # 규칙이 붙인 제외/보류 사유
    # ── 청크 수준 ────────────────────────────────────────────────────────────
    "doc_id", "date", "url", "supported_answer",
    "rule_label",                   # 규칙이 확정한 라벨 (correct만 확정됨)
    "rule_hint",                    # 참고 신호 (matched_older / unmatched) — 확정 아님
    "llm_label",                    # LLM 초벌 제안
    "final_label",                  # 👈 사람이 확정하는 값 (correct / conflict / noise)
    "text",                         # 문서 본문 (판단 근거)
    "note",                         # 검토자 메모 (파이프라인은 읽지 않음)
]
_FINAL_LABELS = tuple(l for l in CHUNK_LABELS if l != "unknown")


def _join(values: list[str] | None) -> str:
    return " | ".join(v for v in (values or []) if v)


def _split(cell: str) -> list[str]:
    return [v.strip() for v in (cell or "").split("|") if v.strip()]


def _pick(*values: str) -> str:
    """우선순위대로 첫 번째 비어있지 않은 값 (final > llm > rule)."""
    return next((v.strip() for v in values if v and v.strip()), "")


def write_csv(items: list[Item], path: str | Path, *,
              hints: dict[str, dict] | None = None) -> None:
    """Item 목록을 검토용 CSV로 쓴다. hints는 {question_id: {doc_id: hint}}."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hints = hints or {}
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM: Excel 한글 대응
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for it in items:
            item_hints = hints.get(it.question_id, {})
            for c in it.chunks:
                w.writerow({
                    "question_id": it.question_id,
                    "dataset": it.dataset,
                    "question": it.question,
                    "rule_conflict_type": it.conflict_type,
                    "llm_conflict_type": "",
                    "final_conflict_type": "",
                    "correct_answer": it.correct_answers[0] if it.correct_answers else "",
                    "corrected_answer": "",
                    "wrong_answers": _join(it.wrong_answers),
                    "llm_verdict": "",
                    "final_verdict": "",
                    "exclusion_flag": it.exclusion_flag or "",
                    "doc_id": c.doc_id,
                    "date": c.date or "",
                    "url": c.url or "",
                    "supported_answer": c.supported_answer or "",
                    "rule_label": "" if c.label == "unknown" else c.label,
                    "rule_hint": item_hints.get(c.doc_id) or item_hints.get(str(c.doc_id)) or "",
                    "llm_label": "",
                    "final_label": "",
                    "text": c.text,
                    "note": "",
                })


def read_csv(path: str | Path) -> list[dict]:
    """CSV를 행 목록으로 읽는다 (LLM 채움 단계가 그대로 다시 쓰기 위해)."""
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


def to_items(rows: list[dict], *, meta_by_qid: dict[str, dict] | None = None) -> list[Item]:
    """CSV 행 → Item 목록. 라벨 우선순위(final > llm > rule)를 여기서 적용한다.

    meta_by_qid를 주면 draft 단계가 기록해 둔 meta(문서 길이 공변량 등)를 되붙인다.
    """
    meta_by_qid = meta_by_qid or {}
    by_item: dict[str, dict] = {}
    for r in rows:
        qid = r["question_id"]
        it = by_item.setdefault(qid, {"rows": [], "first": r})
        it["rows"].append(r)

    items = []
    for qid, entry in by_item.items():
        head = entry["first"]
        answer = _pick(head.get("corrected_answer", ""), head.get("correct_answer", ""))
        chunks = []
        for r in sorted(entry["rows"], key=lambda x: int(x["doc_id"])):
            label = _pick(r.get("final_label", ""), r.get("llm_label", ""),
                          r.get("rule_label", ""))
            if label not in _FINAL_LABELS:
                label = "unknown"      # 미확정 — 채점 트랙 진입을 스키마가 막는다
            chunks.append(Chunk(
                doc_id=int(r["doc_id"]), text=r.get("text", ""), label=label,
                date=r.get("date") or None, url=r.get("url") or None,
                supported_answer=r.get("supported_answer") or None,
            ))
        meta = dict(meta_by_qid.get(qid, {}))
        if _pick(head.get("corrected_answer", "")):
            meta["answer_errata"] = head.get("correct_answer", "")
        verdict = _pick(head.get("final_verdict", ""), head.get("llm_verdict", ""))
        if verdict:
            meta["screen_verdict"] = verdict
        notes = [r["note"] for r in entry["rows"] if r.get("note", "").strip()]
        if notes:
            meta["review_notes"] = notes

        items.append(Item(
            question_id=qid,
            dataset=head["dataset"],
            question=head["question"],
            conflict_type=_pick(head.get("final_conflict_type", ""),
                                head.get("llm_conflict_type", ""),
                                head.get("rule_conflict_type", "")),
            correct_answers=[answer] if answer else [],
            wrong_answers=_split(head.get("wrong_answers", "")),
            chunks=chunks,
            exclusion_flag=(head.get("exclusion_flag") or None),
            meta=meta,
        ))
    return items


def label_provenance(rows: list[dict]) -> dict[str, int]:
    """라벨이 어디서 왔는지 집계 (사람/LLM/규칙/미확정) + 규칙↔LLM 불일치 — build 리포트용.

    불일치는 조용히 넘기지 않고 센다: LLM이 규칙의 골드 매핑을 뒤집은 경우이므로
    사람이 반드시 봐야 한다(사람이 final_label을 채우면 그쪽이 이긴다)."""
    counts = {"human": 0, "llm": 0, "rule": 0, "unresolved": 0, "rule_llm_disagree": 0}
    for r in rows:
        human = _pick(r.get("final_label", ""))
        llm = _pick(r.get("llm_label", ""))
        rule = _pick(r.get("rule_label", ""))
        if llm in _FINAL_LABELS and rule in _FINAL_LABELS and llm != rule:
            counts["rule_llm_disagree"] += 1
        if human in _FINAL_LABELS:
            counts["human"] += 1
        elif llm in _FINAL_LABELS:
            counts["llm"] += 1
        elif rule in _FINAL_LABELS:
            counts["rule"] += 1
        else:
            counts["unresolved"] += 1
    return counts


def export_label_record(rows: list[dict], path: str | Path) -> None:
    """본문을 뺀 라벨 기록만 남긴다 — 검증 이력을 git에 커밋하기 위한 산출물.

    작업용 CSV는 원본 본문을 담고 있어 커밋할 수 없다(QACC는 CC BY-SA 3.0 ShareAlike).
    반면 "어느 문서를 무엇으로 판정했는가"는 재현 불가능한 인간 노동의 결과이므로
    반드시 이력으로 남긴다 (계획서 §5).
    """
    cols = ["question_id", "doc_id", "rule_label", "rule_hint", "llm_label",
            "final_label", "corrected_answer", "llm_verdict", "final_verdict", "note"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
