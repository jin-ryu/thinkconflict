"""전처리 LLM 초벌 라벨러 (PPT 12·13p, 계획서 §3.1.1·§3.1.3 — Phase 1의 LLM 소요 전부).

전처리에서 LLM이 필요한 곳은 딱 두 군데이며, 이 모듈이 둘 다 담당한다.
어느 쪽도 값을 확정하지 않는다 — **초벌 제안을 검토 시트에 채울 뿐, 확정은 사람**이다.

  dragged — 청크 라벨 초벌 (PPT 12p ①: "LLM이 초벌 분류한 뒤 사람이 전수 검토").
            **사실 충돌 67문항 전수**가 기본 대상이다(--only-flagged로 축소 가능).
            규칙은 '정답 문자열을 담았는가'만 볼 수 있어 correct만 확정할 수 있고,
            '다른 답을 주장하는가(conflict)' vs '무관한가(noise)'는 가르지 못한다
            — 예: 정답 "at least 1,759"에 "1,762"를 주장하는 문서는 매칭에 실패하지만
            명백한 충돌 문서다. 그 판정을 LLM이 초벌하고 사람이 확정한다.
            제안은 dragged_llm_labels.csv에 쌓이고, `dragged_prep sheet`가 이를
            dragged_review.csv의 llm_label 열로 프리필한다.

  qacc    — 게이트 ① sharp/soft 재분류 + conflict_type 초벌 (PPT 13p ①: "QACC엔
            충돌 유형이 없어 LLM이 먼저 나누고 사람이 검수" — 시간차 temporal,
            사실오류 misinfo, 관점 opinion, 표기만 다른 사이비 충돌은 soft로 드롭).
            판정자 2종(--judge 1/2, 서로 다른 계열)을 각각 돌려 qacc_screen.csv의
            judge1/judge2 열을 채운다. 사람이 verdict 열을 확정한다.

  ramdocs — LLM 불필요 (라벨이 원본에 내장, 그대로 승계).

비용: OpenAI 호환 엔드포인트면 무엇이든 쓸 수 있다 — 자체 서빙 오픈 모델이면 0원.
      상용 API를 쓸 때만 `qacc_prep estimate-cost`로 예측·승인 후 집행(사전등록 §7.5).

usage:
    python -m preprocessing.llm_assist dragged --base-url http://localhost:8003/v1 --model gpt-oss-20b
    python -m preprocessing.llm_assist qacc --judge 1 --base-url ... --model ...
    python -m preprocessing.llm_assist qacc --judge 2 --base-url ... --model ...   # 다른 계열로
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from openai import OpenAI

from preprocessing.schema import Item, read_jsonl

REVIEW_DIR = Path("preprocessing/review")
MAX_SNIPPET_WORDS = 200  # 판정 프롬프트에 넣는 문서 발췌 상한


def make_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def ask(client: OpenAI, model: str, prompt: str, max_tokens: int = 60) -> str:
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        temperature=0.0, max_tokens=max_tokens)
    return (resp.choices[0].message.content or "").strip()


def first_token(text: str, allowed: tuple[str, ...]) -> str | None:
    """형식-채움 응답에서 처음 등장하는 허용 라벨을 골라낸다 (부록 A(a) G-Eval 방식).
    "label = support" 같은 폼 에코를 건너뛰기 위해 허용 라벨이 나올 때까지 훑는다."""
    for tok in re.findall(r"[a-z_]+", text.lower()):
        if tok in allowed:
            return tok
    return None


# ── DRAGged: 문서별 정답 지지 판정 (골드 매핑 초벌) ──────────────────────────

DRAGGED_PROMPT = """You are labeling retrieved web documents for a QA dataset.

Question: {question}
Gold answer: {answer}

Document (excerpt):
{doc}

Does this document SUPPORT the gold answer, CONTRADICT it by asserting a different
answer to the same question (e.g. an outdated date or a wrong figure), or is it
IRRELEVANT to deciding the answer?

Fill the form with one word.
label ∈ {{support, contradict, irrelevant}} = """

LLM_TO_CHUNK_LABEL = {"support": "correct", "contradict": "conflict",
                      "irrelevant": "noise"}


def run_dragged(client: OpenAI, model: str, draft_path: Path, out_csv: Path,
                only_flagged: bool) -> None:
    items = [it for it in read_jsonl(draft_path)
             if it.conflict_type in ("temporal", "misinfo")]
    if only_flagged:
        items = [it for it in items if it.exclusion_flag]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    n_calls = 0
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["question_id", "doc_id", "exclusion_flag", "rule_label",
                    "llm_label", "llm_model"])
        for it in items:
            answer = it.correct_answers[0] if it.correct_answers else ""
            for c in it.chunks:
                doc = " ".join(c.text.split()[:MAX_SNIPPET_WORDS])
                raw = ask(client, model, DRAGGED_PROMPT.format(
                    question=it.question, answer=answer, doc=doc))
                verdict = first_token(raw, ("support", "contradict", "irrelevant"))
                w.writerow([it.question_id, c.doc_id, it.exclusion_flag or "",
                            c.label, LLM_TO_CHUNK_LABEL.get(verdict, ""), model])
                n_calls += 1
    print(f"DRAGged LLM 초벌 제안 {n_calls}건(문서) → {out_csv}")
    print("→ 사람이 dragged_review.csv를 채울 때 이 제안을 참조한다 (확정은 사람 전수 검토).")


# ── QACC: sharp/soft + conflict_type 초벌 (게이트 ①) ─────────────────────────

QACC_PROMPT = """You are screening a QA item whose retrieved snippets give conflicting answers.

Question: {question}
Candidate answers found in the snippets: {answers}
Annotated correct answer: {gold}

Snippets (excerpts):
{docs}

Two judgments:
1. Is this a SHARP factual contradiction (the answers are genuinely incompatible),
   or a SOFT pseudo-conflict (same fact written at different granularity or notation,
   e.g. "September 1915" vs "25 September 1915", unit or spelling variants)?
2. If sharp, what drives the conflict?
   temporal — the answers differ because sources are from different times
   misinfo  — at least one source asserts a factually wrong claim
   opinion  — the question admits multiple defensible views, no single fact

Fill the form with one word per line.
verdict ∈ {{sharp, soft}} =
type ∈ {{temporal, misinfo, opinion, na}} = """


def run_qacc(client: OpenAI, model: str, draft_path: Path, sheet_path: Path,
             judge_idx: int) -> None:
    items = list(read_jsonl(draft_path))
    if not sheet_path.exists():
        raise SystemExit(f"{sheet_path} 없음 — 먼저 `python -m preprocessing.qacc_prep screen` 실행")
    with open(sheet_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = {r["question_id"]: r for r in reader}
    vcol, tcol = f"judge{judge_idx}(sharp/soft)", f"judge{judge_idx}_type"
    if tcol not in fieldnames:  # 유형 초벌 열이 없으면 추가 (PPT 13p: 유형도 LLM이 나눈다)
        fieldnames.insert(fieldnames.index(vcol) + 1, tcol)

    n = 0
    for it in items:
        row = rows.get(it.question_id)
        if row is None or row.get(vcol, "").strip():
            continue  # 시트에 없거나 이미 판정됨 → 재개 가능
        docs = "\n".join(f"[{c.doc_id + 1}] {' '.join(c.text.split()[:60])}"
                         for c in it.chunks)
        raw = ask(client, model, QACC_PROMPT.format(
            question=it.question,
            answers=" | ".join([*it.correct_answers, *it.wrong_answers]),
            gold=it.correct_answers[0] if it.correct_answers else "(재검증 필요)",
            docs=docs), max_tokens=40)
        lines = [l for l in raw.splitlines() if l.strip()]
        row[vcol] = first_token(lines[0] if lines else "", ("sharp", "soft")) or ""
        row[tcol] = first_token(lines[1] if len(lines) > 1 else "",
                                ("temporal", "misinfo", "opinion", "na")) or ""
        n += 1
    with open(sheet_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows.values():
            w.writerow({k: r.get(k, "") for k in fieldnames})
    done = sum(1 for r in rows.values() if r.get(vcol, "").strip())
    print(f"판정자 {judge_idx} ({model}): 이번에 {n}건 판정, 누적 {done}/{len(rows)} → {sheet_path}")
    print("→ 판정자 2종을 서로 다른 계열로 모두 돌린 뒤, 사람이 verdict 열을 확정한다.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", choices=["dragged", "qacc"])
    ap.add_argument("--base-url", required=True, help="OpenAI 호환 엔드포인트 (자체 서빙이면 무료)")
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default="EMPTY")
    ap.add_argument("--judge", type=int, choices=[1, 2], default=1,
                    help="qacc 전용: 판정자 번호 (2종은 서로 다른 계열이어야 함)")
    ap.add_argument("--only-flagged", action="store_true",
                    help="dragged 전용: 전수(기본) 대신 규칙이 못 푼 플래그 문항만 판정")
    ap.add_argument("--out-dir", default="data/processed", type=Path)
    args = ap.parse_args()

    client = make_client(args.base_url, args.api_key)
    if args.dataset == "dragged":
        run_dragged(client, args.model, args.out_dir / "dragged.draft.jsonl",
                    REVIEW_DIR / "dragged_llm_labels.csv", only_flagged=args.only_flagged)
    else:
        run_qacc(client, args.model, args.out_dir / "qacc.draft.jsonl",
                 REVIEW_DIR / "qacc_screen.csv", args.judge)


if __name__ == "__main__":
    main()
