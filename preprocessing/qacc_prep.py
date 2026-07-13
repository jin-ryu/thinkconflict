"""QACC 전처리: conflict_type 부여 + 스크리닝 게이트 (Phase 1-2, §3.1.3).

원본(`amazon-science/qa-with-conflicting-context`, data/ConflictQA_Dataset.json) 실측 구조 —
계획서가 상정한 중첩 구조가 아니라 **MTurk 주석 시트를 펼친 플랫 포맷**이다:
    {annotation_task_id, question, contexts:[str], sources:[str],
     firstAnswer,  firstContext:  "['I','G']",   # letter = contexts 인덱스 (A=0 … J=9)
     secondAnswerExist: "A"|"B", secondAnswer, secondContext,
     thirdAnswerExist,          thirdAnswer,  thirdContext,
     fourthAnswerExist,                        # ※ fourthAnswer/fourthContext 필드는 없다
     correctAnswer, reasons: "['B','C']", explanation, split}

실측으로 확인한 사실:
    · 충돌 = `secondAnswerExist == "A"` → 381건 (답 2개 243 · 3개 94 · 4개 44).
      계획서 §3.1.3(2)의 실측치와 정확히 일치한다.
    · 문서는 구글 스니펫(중앙 28단어), 문항당 6~10개. `sources`는 병렬 도메인 리스트.
      날짜 메타데이터는 없다(본문 내 표기뿐) — 게이트 ④의 분리 보고 사유.
    · `correctAnswer`가 후보 답 집합에 없는 문항이 38건 → 게이트 ③(정답 재검증) 대상.
    · `reasons` 코드북은 원 레포에 없다. 코드 A가 정확히 48건이고 explanation의
      최신성 키워드 적중률이 39.6%(타 코드 2.9~7.5%)로, 계획서의 "최신성 사유 48건"과
      일치한다 → **A = recency로만 확정**하고 나머지 코드는 사실 충돌(misinfo)로 묶는다.
      이 미해독은 유형 인지 분석의 한계로 §5에 명시해야 한다.

스크리닝 게이트 (사전등록 §3.3) — 통과분만 채점 트랙 투입:
    ① sharp/soft 재분류 (LLM 판정자 2종 + 인간 스팟체크) ※ 유료 판정자는 비용 승인 후
    ② DRAGged 질문 중복 제거  ③ correctAnswer 재검증  ④ 문서 길이 공변량 기록  ⑤ 셔플링

CLI: convert → estimate-cost → screen → final
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

from preprocessing.schema import Chunk, Item, write_jsonl
from preprocessing.tabular import (label_provenance, read_csv, read_meta, to_items,
                                   write_csv, write_meta)

CONFLICT_FLAG = "A"          # secondAnswerExist == "A" 이면 충돌 (실측 381건)
RECENCY_CODE = "A"           # reasons 코드 A = 최신성 (48건, 계획서와 일치)
ANSWER_SLOTS = (("firstAnswer", "firstContext"),
                ("secondAnswer", "secondContext"),
                ("thirdAnswer", "thirdContext"))


def is_nan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def as_list(v) -> list[str]:
    """"['I', 'G']" 형태의 문자열 리터럴을 안전하게 리스트로 만든다."""
    if is_nan(v):
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    s = str(v).strip()
    if not s:
        return []
    try:
        parsed = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return []
    return [str(x) for x in parsed] if isinstance(parsed, (list, tuple)) else []


def letters_to_indices(letters: list[str], n_contexts: int) -> list[int]:
    out = []
    for L in letters:
        if len(L) == 1 and L.isalpha():
            idx = ord(L.upper()) - 65
            if 0 <= idx < n_contexts:
                out.append(idx)
    return out


def norm_answer(s) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", str(s).lower()).strip() if not is_nan(s) else ""


def norm_q(q: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()


def load_raw(raw_dir: Path) -> list[dict]:
    path = raw_dir / "data" / "ConflictQA_Dataset.json"
    if not path.exists():
        cands = [p for p in sorted(raw_dir.rglob("*.json")) if ".git" not in p.parts]
        if not cands:
            raise FileNotFoundError(f"{raw_dir}에 원본 없음 — data/raw/download.sh 먼저 실행")
        path = cands[0]
    rows = json.loads(path.read_text(encoding="utf-8"))
    print(f"원본 로드: {path} (N={len(rows)})")
    return rows


def conflict_type_of(row: dict) -> str:
    """초벌 prior: reasons 코드 A(최신성 48건, 실측 검증)만 temporal로 확정.

    확정 유형은 PPT 13p 설계대로 LLM 초벌(llm_assist qacc의 judge_type 열) +
    인간 검수를 거쳐 final 단계에서 덮어쓴다 — 여기 값은 그 전까지의 기본값이다."""
    return "temporal" if RECENCY_CODE in as_list(row.get("reasons")) else "misinfo"


def build_items(rows: list[dict]) -> tuple[list[Item], Counter]:
    """충돌 문항만 공통 스키마로 변환. 답변-문서 귀속 주석을 chunk 라벨로 승계한다."""
    items, stats = [], Counter()
    for i, row in enumerate(rows):
        if row.get("secondAnswerExist") != CONFLICT_FLAG:
            continue
        stats["conflict"] += 1
        contexts = list(row.get("contexts") or [])
        sources = list(row.get("sources") or [])
        gold = row.get("correctAnswer")
        gold_n = norm_answer(gold)

        # 답 슬롯별 지지 문서 인덱스를 모아 라벨을 정한다
        support: dict[int, str] = {}   # context 인덱스 → 그 문서가 지지하는 답
        for ans_f, ctx_f in ANSWER_SLOTS:
            ans = row.get(ans_f)
            if is_nan(ans) or not str(ans).strip():
                continue
            for idx in letters_to_indices(as_list(row.get(ctx_f)), len(contexts)):
                support.setdefault(idx, str(ans))

        candidates = {norm_answer(row.get(f)) for f, _ in ANSWER_SLOTS
                      if not is_nan(row.get(f))} - {""}
        flag = None
        if not gold_n:
            flag = "no_gold"
        elif gold_n not in candidates:
            # 주석자 1인이 자유 서술로 정답을 적은 경우 — 게이트 ③ 재검증 대상
            flag = "gold_not_in_candidates"
        if flag:
            stats[f"flag_{flag}"] += 1

        chunks = []
        for j, text in enumerate(contexts):
            sup = support.get(j)
            if sup is None:
                label = "noise"          # 어느 답도 지지하지 않는 문서
            elif gold_n and norm_answer(sup) == gold_n:
                label = "correct"
            else:
                label = "conflict"
            chunks.append(Chunk(doc_id=j, text=text, label=label,
                                url=(sources[j] if j < len(sources) else None),
                                supported_answer=sup))

        has_pair = (any(c.label == "correct" for c in chunks)
                    and any(c.label == "conflict" for c in chunks))
        if not has_pair and flag is None:
            flag = "no_valid_conflict_pair"   # 유효 충돌 게이트 (사전등록 §3.1) 미통과
            stats["flag_no_valid_conflict_pair"] += 1

        items.append(Item(
            question_id=f"qacc-{i:04d}",
            dataset="qacc",
            question=row["question"],
            conflict_type=conflict_type_of(row),
            correct_answers=[str(gold)] if gold_n else [],
            wrong_answers=[str(row.get(f)) for f, _ in ANSWER_SLOTS
                           if not is_nan(row.get(f)) and norm_answer(row.get(f)) != gold_n],
            chunks=chunks,
            behavior_track=False,        # 게이트 통과 후 final에서 확정
            self_consistency_track=True,
            exclusion_flag=flag,
            meta={"source_row": i, "split": row.get("split"),
                  "reasons": as_list(row.get("reasons")),
                  "n_answers": 1 + sum(1 for f in ("secondAnswerExist", "thirdAnswerExist",
                                                   "fourthAnswerExist")
                                       if row.get(f) == CONFLICT_FLAG),
                  "n_docs": len(chunks),
                  "doc_len_words": [len(c.text.split()) for c in chunks],  # 게이트 ④ 공변량
                  "annotation_task_id": row.get("annotation_task_id"),
                  # 스키마에 자리가 없는 원본 필드는 meta에 보존한다 (PPT 11p 규약)
                  "explanation": (None if is_nan(row.get("explanation"))
                                  else row.get("explanation"))},
        ))
    return items, stats


def dedup_against_dragged(items: list[Item], dragged_csv: Path) -> tuple[list[Item], list[str]]:
    """게이트 ②: DRAGged 질문 중복 제거. 두 벤치마크의 충돌 판정이 엇갈리는
    문항은 라벨 신뢰의 경계 사례이므로 건수를 따로 보고한다."""
    if not dragged_csv.exists():
        print(f"경고: {dragged_csv} 없음 — 중복 제거 생략 (dragged draft 먼저 실행할 것)")
        return items, []
    dragged = {norm_q(r["question"]): r["rule_conflict_type"]
               for r in read_csv(dragged_csv)}
    kept, dropped = [], []
    for it in items:
        ct = dragged.get(norm_q(it.question))
        if ct is None:
            kept.append(it)
        else:
            dropped.append(f"{it.question_id}|dragged_type={ct}")
    by_type = Counter(d.rsplit("=", 1)[1] for d in dropped)
    # QACC는 충돌로, DRAGged는 비충돌/상보로 본 문항이 경계 사례다 (§3.1.3(4) ②)
    print(f"게이트 ②: DRAGged 중복 {len(dropped)}건 제거 (계획서 실측 47) — "
          f"DRAGged 판정 내역 {dict(by_type)}")
    print(f"   충돌 판정 불일치(DRAGged=none): {by_type['none']}건, "
          f"(DRAGged=complementary): {by_type['complementary']}건 — 라벨 신뢰의 경계 사례로 보고")
    return kept, dropped


def estimate_cost_from_csv(rows: list[dict]) -> None:
    """게이트 ① 판정 비용 예측 — 유료 API 집행 전 승인 절차 (계획서 Phase 1-2, 부록 D)."""
    by_item: dict[str, int] = {}
    for r in rows:
        by_item[r["question_id"]] = by_item.get(r["question_id"], 0) + len(
            (r.get("text") or "").split())
    n = len(by_item)
    avg_words = sum(by_item.values()) / max(n, 1)
    tok_in = int(n * 2 * (avg_words * 1.4 + 500))   # 판정자 2종, 문항당 프롬프트 ~500tok
    tok_out = n * 2 * 150
    print(f"게이트 ① 판정 대상 N={n} (중복 제거 후), 판정자 2종")
    print(f"문항당 평균 문서 {avg_words:.0f}단어")
    print(f"예상 토큰: 입력 ~{tok_in:,} / 출력 ~{tok_out:,}")
    print("→ 오픈 가중치 판정자 2종으로 돌리면 비용 0 (자체 서빙). "
          "상용 판정자를 쓸 경우에만 단가를 곱해 승인 요청 후 집행 (사전등록 §3.3)")


def build_items_from_csv(rows: list[dict],
                         meta_by_qid: dict[str, dict]) -> tuple[list[Item], Counter]:
    """CSV 행 → 최종 Item. 게이트 ①(sharp만 투입)과 유형 확정을 여기서 적용한다."""
    items, stats = [], Counter(label_provenance(rows))
    for it in to_items(rows, meta_by_qid=meta_by_qid):
        verdict = it.meta.get("screen_verdict", "")
        stats[f"verdict_{verdict or 'unjudged'}"] += 1
        if verdict != "sharp":
            continue          # soft(사이비 충돌)·미판정은 채점 트랙에서 드롭 (게이트 ①)
        it.self_consistency_track = True
        # opinion으로 확정되면 단일 정답이 없어 채점 대상이 아니다 (§3.2 이중 트랙)
        it.behavior_track = (it.exclusion_flag is None
                             and bool(it.correct_answers)
                             and it.conflict_type != "opinion"
                             and any(c.label == "correct" for c in it.chunks)
                             and any(c.label == "conflict" for c in it.chunks))
        stats["behavior_track" if it.behavior_track else "excluded"] += 1
        items.append(it)
    return items, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["draft", "estimate-cost", "build"])
    ap.add_argument("--raw-dir", default="data/raw/qacc", type=Path)
    ap.add_argument("--review-dir", default="data/review/qacc", type=Path)
    ap.add_argument("--out-dir", default="data/processed", type=Path)
    ap.add_argument("--dragged-draft",
                    default="data/review/dragged/dragged.draft.csv", type=Path)
    ap.add_argument("--csv", type=Path, help="build 입력 CSV (기본: qacc.llm.csv → qacc.draft.csv)")
    args = ap.parse_args()
    draft_csv = args.review_dir / "qacc.draft.csv"
    llm_csv = args.review_dir / "qacc.llm.csv"
    meta_path = args.review_dir / "qacc.meta.json"

    if args.stage == "draft":
        items, stats = build_items(load_raw(args.raw_dir))
        items, dropped = dedup_against_dragged(items, args.dragged_draft)
        write_csv(items, draft_csv)
        write_meta(items, meta_path)
        print(f"\n초안 CSV: {draft_csv} (충돌 {stats['conflict']}건 → 중복 제거 후 {len(items)}건, "
              f"행 {sum(len(it.chunks) for it in items)})")
        flags = Counter(it.exclusion_flag for it in items if it.exclusion_flag)
        print(f"플래그 {sum(flags.values())}건 (채점 트랙 진입 차단): {dict(flags)}")
        print("conflict_type(초벌):", dict(Counter(it.conflict_type for it in items)))
        print("→ 다음: llm_assist qacc로 llm_verdict·llm_conflict_type·llm_label을 채운다")
    elif args.stage == "estimate-cost":
        estimate_cost_from_csv(read_csv(draft_csv))
    else:  # build
        src = args.csv or (llm_csv if llm_csv.exists() else draft_csv)
        if not src.exists():
            raise SystemExit(f"입력 CSV 없음: {src} — `draft` 단계 먼저 실행")
        rows = read_csv(src)
        items, stats = build_items_from_csv(rows, read_meta(meta_path))
        if not items:
            raise SystemExit("sharp 판정 문항이 없다 — llm_assist qacc 실행 후 "
                             "final_verdict(또는 llm_verdict)를 채울 것 (게이트 ①)")
        write_jsonl(items, args.out_dir / "qacc.jsonl")
        print(f"입력: {src}")
        print(f"확정: {args.out_dir / 'qacc.jsonl'} (게이트 통과 N={len(items)}, "
              f"behavior_track {stats['behavior_track']}건)")
        print("판정 내역:", {k.replace("verdict_", ""): v for k, v in stats.items()
                             if k.startswith("verdict_")})


if __name__ == "__main__":
    main()
