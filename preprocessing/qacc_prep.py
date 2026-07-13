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

from preprocessing.schema import Chunk, Item, read_jsonl, write_jsonl

CONFLICT_FLAG = "A"          # secondAnswerExist == "A" 이면 충돌 (실측 381건)
RECENCY_CODE = "A"           # reasons 코드 A = 최신성 (48건, 계획서와 일치)
JUDGE_SHEET = Path("preprocessing/review/qacc_screen.csv")
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


def dedup_against_dragged(items: list[Item], dragged_path: Path) -> tuple[list[Item], list[str]]:
    """게이트 ②: DRAGged 질문 중복 제거. 두 벤치마크의 충돌 판정이 엇갈리는
    문항은 라벨 신뢰의 경계 사례이므로 건수를 따로 보고한다."""
    if not dragged_path.exists():
        print(f"경고: {dragged_path} 없음 — 중복 제거 생략 (dragged draft 먼저 생성할 것)")
        return items, []
    dragged = {norm_q(it.question): it.conflict_type for it in read_jsonl(dragged_path)}
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


def estimate_cost(items: list[Item]) -> None:
    """게이트 ① 판정 비용 예측 — 유료 API 집행 전 승인 절차 (계획서 Phase 1-2, 부록 D)."""
    n = len(items)
    avg_words = sum(sum(it.meta["doc_len_words"]) for it in items) / max(n, 1)
    tok_in = int(n * 2 * (avg_words * 1.4 + 500))   # 판정자 2종, 문항당 프롬프트 ~500tok
    tok_out = n * 2 * 150
    print(f"게이트 ① 판정 대상 N={n} (중복 제거 후), 판정자 2종")
    print(f"문항당 평균 문서 {avg_words:.0f}단어")
    print(f"예상 토큰: 입력 ~{tok_in:,} / 출력 ~{tok_out:,}")
    print("→ 오픈 가중치 판정자 2종으로 돌리면 비용 0 (자체 서빙). "
          "상용 판정자를 쓸 경우에만 단가를 곱해 승인 요청 후 집행 (사전등록 §3.3)")


def write_screen_template(items: list[Item], out_csv: Path) -> None:
    """게이트 ①·③ 판정 시트 템플릿. 판정자 2종 결과와 인간 스팟체크를 채워 넣는다."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["question_id", "question", "correct_answer", "conflicting_answers",
                    "conflict_type", "exclusion_flag",
                    "judge1(sharp/soft)", "judge1_type",
                    "judge2(sharp/soft)", "judge2_type",
                    "human_spotcheck(sharp/soft)", "gold_reverified(y/n/corrected)",
                    "verdict(sharp/soft)", "final_type"])
        for it in items:
            w.writerow([it.question_id, it.question,
                        it.correct_answers[0] if it.correct_answers else "",
                        " | ".join(it.wrong_answers), it.conflict_type,
                        it.exclusion_flag or "", "", "", "", "", "", "", "", ""])
    print(f"판정 시트 템플릿: {out_csv} (N={len(items)})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["convert", "estimate-cost", "screen", "final"])
    ap.add_argument("--raw-dir", default="data/raw/qacc", type=Path)
    ap.add_argument("--out-dir", default="data/processed/qacc", type=Path)
    ap.add_argument("--dragged-draft",
                    default="data/processed/dragged/dragged.draft.jsonl", type=Path)
    args = ap.parse_args()
    draft_path = args.out_dir / "qacc.draft.jsonl"

    if args.stage == "convert":
        items, stats = build_items(load_raw(args.raw_dir))
        items, dropped = dedup_against_dragged(items, args.dragged_draft)
        write_jsonl(items, draft_path)
        print(f"\n초안 생성: {draft_path} (충돌 {stats['conflict']}건 → 중복 제거 후 {len(items)}건)")
        # 플래그는 중복 제거 후 남은 문항 기준으로 센다 (최종 산출물과 일치시킨다)
        flags = Counter(it.exclusion_flag for it in items if it.exclusion_flag)
        print(f"플래그 {sum(flags.values())}건 (채점 트랙 진입 차단): {dict(flags)}")
        print("conflict_type:", dict(Counter(it.conflict_type for it in items)))
        print(f"  temporal(최신성 사유) {sum(1 for it in items if it.conflict_type == 'temporal')}건 "
              f"— 계획서 실측 48건 대비 (중복 제거분 반영)")
    elif args.stage == "estimate-cost":
        estimate_cost(list(read_jsonl(draft_path)))
    elif args.stage == "screen":
        write_screen_template(list(read_jsonl(draft_path)), JUDGE_SHEET)
        print("\n다음: 판정자 2종을 돌려 judge1/judge2 열을, 인간 스팟체크로 verdict 열을 채운 뒤 "
              "`final` 단계를 실행한다.")
    else:  # final
        if not JUDGE_SHEET.exists():
            raise SystemExit(f"게이트 ① 판정 시트 없음: {JUDGE_SHEET} — screen 단계 선행")
        verdicts: dict[str, dict] = {}
        with open(JUDGE_SHEET, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                verdicts[r["question_id"]] = r
        if not any(r.get("verdict(sharp/soft)", "").strip() for r in verdicts.values()):
            raise SystemExit("verdict 열이 비어 있다 — llm_assist qacc(판정자 2종) 후 인간 확정 필요")
        items = []
        for it in read_jsonl(draft_path):
            row = verdicts.get(it.question_id, {})
            if row.get("verdict(sharp/soft)", "").strip() != "sharp":
                continue  # soft(사이비 충돌)·미판정은 채점 트랙에서 드롭 (게이트 ①)
            # 유형 확정: 인간 확정 열 > 판정자 일치 > reasons prior (PPT 13p)
            j1, j2 = row.get("judge1_type", "").strip(), row.get("judge2_type", "").strip()
            human_type = row.get("final_type", "").strip()
            if human_type in ("temporal", "misinfo", "opinion"):
                it.conflict_type = human_type
            elif j1 and j1 == j2 and j1 in ("temporal", "misinfo", "opinion"):
                it.conflict_type = j1
            it.meta["type_provenance"] = ("human" if human_type else
                                          "judges_agree" if j1 and j1 == j2 else "reasons_prior")
            # opinion으로 확정되면 단일 정답이 없으므로 채점 트랙에서 제외 (§3.2 이중 트랙)
            it.behavior_track = (it.exclusion_flag is None and bool(it.correct_answers)
                                 and it.conflict_type != "opinion")
            it.meta["screen"] = "sharp"
            items.append(it)
        write_jsonl(items, args.out_dir / "qacc.jsonl")
        n_behav = sum(1 for it in items if it.behavior_track)
        print(f"확정: qacc.jsonl (게이트 통과 N={len(items)}, behavior_track {n_behav}건 "
              f"— 보수 가정 ~134)")
        print("유형 출처:", dict(Counter(it.meta["type_provenance"] for it in items)))


if __name__ == "__main__":
    main()
