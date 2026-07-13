"""전처리 LLM 초벌 (PPT 12·13p — Phase 1의 LLM 소요 전부).

**입력도 CSV, 출력도 CSV다.** `<ds>.draft.csv`의 빈칸을 채워 `<ds>.llm.csv`로 쓴다.
사람은 그 CSV를 열어 `final_*` 열만 확정하면 되고(빈칸이면 LLM 제안이 그대로 쓰인다),
`<ds>_prep build`가 그걸 읽어 JSONL을 만든다.

    dragged  →  llm_label 열 (문서별 support / contradict / irrelevant)
                규칙은 '정답을 담았는가'만 알 뿐 '다른 답을 주장하는가(conflict)'와
                '무관한가(noise)'를 가르지 못한다 — 그 판정을 LLM이 초벌한다.
                실측 반례: 정답 "at least 1,759"에 "1,762"를 주장하는 문서.

    qacc     →  judge{N}_verdict(sharp/soft) + judge{N}_type 열 (게이트 ①)
                두 판정자가 일치하면 llm_verdict·llm_conflict_type에 반영하고,
                불일치는 빈칸으로 남겨 사람이 adjudication하게 한다(부록 A(b)).
                문서 라벨은 원본 귀속 주석에 이미 있어 건드리지 않는다.

    ramdocs  →  LLM 불필요. 문서 라벨·정답이 원본에 내장돼 있어 승계만 한다
                (LLM을 태우면 원본 골드 라벨을 추측으로 덮어쓰는 셈이라 품질이 낮아진다).

판정자는 대상 모델과 다른 계열이어야 한다(부록 A(a) 자기선호 편향 통제).
중단 후 다시 실행하면 이미 채워진 행은 건너뛴다(재개 가능).
비용: OpenAI 호환 엔드포인트면 무엇이든 쓸 수 있다 — 자체 서빙 오픈 모델이면 0원.

usage:
    python -m preprocessing.llm_assist dragged --base-url http://localhost:8003/v1 --model gpt-oss-20b
    python -m preprocessing.llm_assist qacc --judge 1 --base-url ... --model MODEL_A
    python -m preprocessing.llm_assist qacc --judge 2 --base-url ... --model MODEL_B
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from preprocessing.tabular import read_csv, write_rows

MAX_DOC_WORDS = 200        # 판정 프롬프트에 넣는 문서 발췌 상한
FACT_CONFLICT_TYPES = ("temporal", "misinfo")


def make_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def ask(client: OpenAI, model: str, prompt: str, max_tokens: int = 40) -> str:
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        temperature=0.0, max_tokens=max_tokens)
    return (resp.choices[0].message.content or "").strip()


def first_token(text: str, allowed: tuple[str, ...]) -> str | None:
    """형식-채움 응답에서 처음 등장하는 허용 라벨을 고른다 (부록 A(a) G-Eval 방식).
    "label = support" 같은 폼 에코를 건너뛰기 위해 허용 라벨이 나올 때까지 훑는다."""
    for tok in re.findall(r"[a-z_]+", text.lower()):
        if tok in allowed:
            return tok
    return None


# ── DRAGged: 문서별 정답 지지 판정 → llm_label ────────────────────────────────

DRAGGED_PROMPT = """You are labeling retrieved web documents for a QA dataset.

Question: {question}
Gold answer: {answer}

Document (excerpt):
{doc}

Does this document SUPPORT the gold answer, CONTRADICT it by asserting a different
answer to the same question (e.g. an outdated date or a different figure), or is it
IRRELEVANT to deciding the answer?

Fill the form with one word.
label ∈ {{support, contradict, irrelevant}} = """

TO_LABEL = {"support": "correct", "contradict": "conflict", "irrelevant": "noise"}


def run_dragged(client: OpenAI, model: str, rows: list[dict], only_flagged: bool) -> int:
    """LLM은 **빈칸만** 채운다. 규칙이 이미 확정한 rule_label(=correct, 골드 매핑)은
    건드리지 않는다 — llm_label이 rule_label보다 우선순위가 높으므로, 여기서 덮어쓰면
    애써 찾은 정답 문서를 LLM 추측으로 잃는다."""
    targets = [r for r in rows
               if r.get("rule_conflict_type") in FACT_CONFLICT_TYPES
               and not (r.get("rule_label") or "").strip()      # 빈칸만
               and not (r.get("llm_label") or "").strip()
               and not (r.get("final_label") or "").strip()]
    if only_flagged:
        targets = [r for r in targets if (r.get("exclusion_flag") or "").strip()]
    for r in tqdm(targets, desc=f"dragged/{model}", unit="doc"):
        doc = " ".join((r.get("text") or "").split()[:MAX_DOC_WORDS])
        raw = ask(client, model, DRAGGED_PROMPT.format(
            question=r["question"],
            answer=(r.get("corrected_answer") or r.get("correct_answer") or ""),
            doc=doc))
        r["llm_label"] = TO_LABEL.get(first_token(raw, tuple(TO_LABEL)) or "", "")
    return len(targets)


# ── QACC: sharp/soft + conflict_type 초벌 (게이트 ①) ──────────────────────────

QACC_PROMPT = """You are screening a QA item whose retrieved snippets give conflicting answers.

Question: {question}
Correct answer (annotated): {gold}
Other answers found in the snippets: {wrong}

Snippets:
{docs}

Two judgments:
1. Is this a SHARP factual contradiction (the answers are genuinely incompatible),
   or a SOFT pseudo-conflict (the same fact written at different granularity or
   notation, e.g. "September 1915" vs "25 September 1915", unit/spelling variants)?
2. If sharp, what drives the conflict?
   temporal — the answers differ because the sources are from different times
   misinfo  — at least one source asserts a factually wrong claim
   opinion  — the question admits multiple defensible views, no single fact

Fill the form with one word per line.
verdict ∈ {{sharp, soft}} =
type ∈ {{temporal, misinfo, opinion, na}} = """


def run_qacc(client: OpenAI, model: str, rows: list[dict], judge_idx: int) -> int:
    """QACC 판정은 문항 수준이다 — 같은 question_id의 행들을 한 번에 판정해 함께 채운다."""
    by_item: dict[str, list[dict]] = {}
    for r in rows:
        by_item.setdefault(r["question_id"], []).append(r)

    vcol, tcol = f"judge{judge_idx}_verdict", f"judge{judge_idx}_type"
    other_v, other_t = (f"judge{2 if judge_idx == 1 else 1}_verdict",
                        f"judge{2 if judge_idx == 1 else 1}_type")
    todo = [(qid, rs) for qid, rs in by_item.items() if not (rs[0].get(vcol) or "").strip()]

    for _qid, rs in tqdm(todo, desc=f"qacc/judge{judge_idx}/{model}", unit="item"):
        head = rs[0]
        docs = "\n".join(f"[{i + 1}] {' '.join((r.get('text') or '').split()[:60])}"
                         for i, r in enumerate(rs))
        raw = ask(client, model, QACC_PROMPT.format(
            question=head["question"],
            gold=(head.get("corrected_answer") or head.get("correct_answer")
                  or "(재검증 필요)"),
            wrong=head.get("wrong_answers", ""), docs=docs))
        lines = [l for l in raw.splitlines() if l.strip()]
        verdict = first_token(lines[0] if lines else "", ("sharp", "soft")) or ""
        ctype = first_token(lines[1] if len(lines) > 1 else "",
                            ("temporal", "misinfo", "opinion", "na")) or ""
        ctype = "" if ctype == "na" else ctype
        for r in rs:
            r[vcol], r[tcol] = verdict, ctype
            # 두 판정자가 일치할 때만 llm_* 로 승격한다. 불일치는 빈칸 → 사람이 확정(부록 A(b))
            if (r.get(other_v) or "").strip() == verdict and verdict:
                r["llm_verdict"] = verdict
            if (r.get(other_t) or "").strip() == ctype and ctype:
                r["llm_conflict_type"] = ctype
    return len(todo)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", choices=["dragged", "qacc"])
    ap.add_argument("--base-url", required=True, help="OpenAI 호환 엔드포인트 (자체 서빙이면 무료)")
    ap.add_argument("--model", required=True)
    ap.add_argument("--api-key", default="EMPTY")
    ap.add_argument("--judge", type=int, choices=[1, 2], default=1,
                    help="qacc 전용: 판정자 번호. 2종은 서로 다른 계열이어야 한다")
    ap.add_argument("--only-flagged", action="store_true",
                    help="dragged 전용: 전수(기본) 대신 규칙이 못 푼 플래그 문항만")
    ap.add_argument("--data-dir", default="data/processed", type=Path)
    args = ap.parse_args()

    ds = args.dataset
    draft_csv = args.data_dir / ds / f"{ds}.draft.csv"
    llm_csv = args.data_dir / ds / f"{ds}.llm.csv"
    src = llm_csv if llm_csv.exists() else draft_csv   # 재개: 채우던 파일에 이어 쓴다
    if not src.exists():
        raise SystemExit(f"입력 CSV 없음: {src} — `python -m preprocessing.{ds}_prep draft` 먼저 실행")

    rows = read_csv(src)
    client = make_client(args.base_url, args.api_key)
    if ds == "dragged":
        n = run_dragged(client, args.model, rows, args.only_flagged)
        extra: list[str] = []
    else:
        n = run_qacc(client, args.model, rows, args.judge)
        extra = [f"judge{args.judge}_verdict", f"judge{args.judge}_type"]

    write_rows(rows, llm_csv, extra_columns=extra)
    print(f"\n{n}건 판정 → {llm_csv}")
    print(f"→ 이 CSV의 final_* 열을 확정한 뒤 "
          f"`python -m preprocessing.{ds}_prep build` 실행 (빈칸이면 LLM 제안이 쓰인다)")


if __name__ == "__main__":
    main()
