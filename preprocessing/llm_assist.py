"""전처리 LLM 초벌 (PPT 12·13p — Phase 1의 LLM 소요 전부).

**입력도 CSV, 출력도 CSV다.** `<ds>.draft.csv`의 **빈칸만** 채워 `<ds>.llm.csv`로 쓴다.
이미 값이 있는 칸(규칙이 확정한 것)은 건드리지 않는다. 사람은 그 CSV를 열어 아무 칸이나
고쳐 쓰면 되고(맨 나중에 적힌 값이 그대로 최종본이 된다), `<ds>_prep build`가 JSONL을 만든다.

    dragged  →  빈 `label`(correct/conflict/noise)과 `supported_answer`(이 문서가 주장하는 답)
                규칙은 '정답을 담았는가'만 알 뿐 '다른 답을 주장하는가(conflict)'와
                '무관한가(noise)'를 가르지 못한다 — 그 판정을 LLM이 초벌한다.
                실측 반례: 정답 "at least 1,759"에 "1,762"를 주장하는 문서.
                RAMDocs·QACC는 supported_answer가 원본 주석에 있으나 DRAGged는 없으므로,
                같은 판정에서 함께 뽑아 세 데이터셋의 공통 구조를 맞춘다.

    qacc     →  게이트 ①(sharp/soft). 판정자 2종의 **원 판정은 judges/judge{N}.csv에 따로**
                남기고(검토 CSV는 공통 스키마 열만 유지), **둘이 일치할 때만** 검토 CSV에
                반영한다 — sharp면 `exclusion_flag`를 비우고, soft면 `soft_conflict`로 바꾼다.
                불일치하면 `pending_screen` 그대로 두어 사람이 adjudication한다(부록 A(b)).
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
import csv
import re
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from preprocessing.tabular import (PENDING_SCREEN, SOFT_CONFLICT, read_csv,
                                   write_rows)

MAX_DOC_WORDS = 200        # 판정 프롬프트에 넣는 문서 발췌 상한
FACT_CONFLICT_TYPES = ("outdated", "misinformation")


def make_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


def ask(client: OpenAI, model: str, prompt: str, max_tokens: int = 256) -> str:
    """형식-채움 한 줄 판정을 받는다.

    사고형 모델(Qwen3.6 등)은 기본으로 추론을 먼저 뱉으므로 짧은 토큰 예산이 사고에
    다 쓰이고 폼 값에 도달하지 못한다 — 실측: 333건 전부 빈 판정. 전처리 판정은
    한 단어 폼 채움이라 사고가 필요 없으므로 사고 채널을 끈다. 템플릿이 이 인자를
    받지 않는 엔드포인트(비-Qwen 계열)면 인자 없이 한 번 더 시도한다.
    """
    kw = {"model": model, "messages": [{"role": "user", "content": prompt}],
          "temperature": 0.0, "max_tokens": max_tokens}
    # 사고 채널을 끄는 방식이 계열마다 다르다. Qwen은 chat_template_kwargs로 끄고,
    # gpt-oss는 끌 수 없으나 reasoning_effort='low'로 줄이면 폼 값까지 도달한다
    # (실측: effort=medium은 max_tokens 256에서도 final 채널에 도달하지 못한다).
    for extra in ({"chat_template_kwargs": {"enable_thinking": False}},
                  {"reasoning_effort": "low"},
                  None):
        try:
            resp = client.chat.completions.create(**kw, extra_body=extra)
        except Exception:  # noqa: BLE001 — 엔드포인트가 그 인자를 모르는 경우
            continue
        text = (resp.choices[0].message.content or "").strip()
        if text:
            return text
    return ""


def first_token(text: str, allowed: tuple[str, ...]) -> str | None:
    """형식-채움 응답에서 채워진 값을 고른다 (부록 A(a) G-Eval 방식).

    폼 에코를 건너뛰되, **선택지 목록까지 에코하는 모델**을 조심해야 한다. 실측:
    gpt-oss는 "verdict ∈ {sharp, soft} = soft"처럼 통째로 되받아쓴다. 이때 앞에서부터
    허용 라벨을 찾으면 답이 아니라 **첫 번째 선택지**('sharp')를 집어 전 문항이 같은
    값으로 오염된다. 폼 규약상 값은 '=' 뒤에 오므로 '=' 뒤를 우선 판독한다.
    """
    for tok in re.findall(r"[a-z_]+", OPTION_LIST_RE.sub(" ", text).lower()):
        if tok in allowed:
            return tok
    return None


OPTION_LIST_RE = re.compile(r"\{[^}]*\}")   # 되받아쓴 '{sharp, soft}' 같은 선택지 목록


def form_field(text: str, field: str, allowed: tuple[str, ...]) -> str | None:
    """폼 응답에서 `field`에 채워진 값을 뽑는다.

    줄 위치에 의존하지 않는다 — 같은 모델도 응답 모양이 갈린다 (실측, gpt-oss):
        "verdict ∈ {sharp, soft} = sharp"   (값이 같은 줄)
        "verdict\\nsharp"                    (값이 다음 줄)
    앞의 것만 가정하면(lines[0]/lines[1] 고정 배치) 뒤의 모양에서 전 문항이 빈 판정이 된다.
    """
    body = OPTION_LIST_RE.sub(" ", text)
    lines = [ln for ln in body.splitlines() if ln.strip()]
    pat = re.compile(rf"\b{re.escape(field)}\b", re.IGNORECASE)
    for i, line in enumerate(lines):
        m = pat.search(line)
        if not m:
            continue
        tail = line.split("=", 1)[1] if "=" in line else line[m.end():]
        got = first_token(tail, allowed)
        if got:
            return got
        if i + 1 < len(lines):            # 값이 다음 줄에 온 모양
            got = first_token(lines[i + 1], allowed)
            if got:
                return got
    return first_token(body, allowed)     # 필드명 자체가 없으면 전체에서 후퇴 탐색


# ── DRAGged: 문서별 정답 지지 판정 → 빈 `label` 칸 ───────────────────────────

DRAGGED_PROMPT = """You are labeling retrieved web documents for a QA dataset.

Question: {question}
Gold answer: {answer}

Document (excerpt):
{doc}

Two judgments:
1. Does this document SUPPORT the gold answer, CONTRADICT it by asserting a different
   answer to the same question (e.g. an outdated date or a different figure), or is it
   IRRELEVANT to deciding the answer?
2. What answer to the question does this document assert? Quote it briefly from the
   document. Write NONE if the document does not answer the question.

Fill the form, one line each.
label ∈ {{support, contradict, irrelevant}} =
answer = """

TO_LABEL = {"support": "correct", "contradict": "conflict", "irrelevant": "noise"}


def run_dragged(client: OpenAI, model: str, rows: list[dict], only_flagged: bool) -> int:
    """빈 `label` 칸만 채운다. 규칙이 이미 확정한 값(골드 매핑)은 덮어쓰지 않는다 —
    덮어쓰면 애써 찾은 정답 문서를 LLM 추측으로 잃는다."""
    targets = [r for r in rows
               if (r.get("conflict_type") or "").strip() in FACT_CONFLICT_TYPES
               and not (r.get("label") or "").strip()]           # 빈칸만
    if only_flagged:
        targets = [r for r in targets if (r.get("exclusion_flag") or "").strip()]
    for r in tqdm(targets, desc=f"dragged/{model}", unit="doc"):
        doc = " ".join((r.get("text") or "").split()[:MAX_DOC_WORDS])
        raw = ask(client, model, DRAGGED_PROMPT.format(
            question=r["question"], answer=(r.get("correct_answer") or ""), doc=doc),
            max_tokens=60)
        lines = [l for l in raw.splitlines() if l.strip()]
        label = TO_LABEL.get(first_token(lines[0] if lines else "", tuple(TO_LABEL)) or "", "")
        if not label:
            continue
        r["label"] = label
        # noise 문서는 질문에 답하지 않으므로 supported_answer가 없다 (스키마 규약)
        r["supported_answer"] = "" if label == "noise" else _asserted(lines)
    return len(targets)


def _asserted(lines: list[str]) -> str:
    """폼 응답 2번째 줄에서 '이 문서가 주장하는 답'을 뽑는다."""
    if len(lines) < 2:
        return ""
    val = lines[1].split("=", 1)[-1].strip().strip('"\'')
    return "" if val.lower() in ("none", "n/a", "") else val


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
   outdated             — the answers differ because the sources are from different times
   misinformation       — at least one source asserts a factually wrong claim
   conflicting_opinions — the question admits multiple defensible views, no single fact

Fill the form with one word per line.
verdict ∈ {{sharp, soft}} =
type ∈ {{outdated, misinformation, conflicting_opinions, na}} = """


def run_qacc(client: OpenAI, model: str, rows: list[dict], judge_idx: int,
             judge_dir: Path) -> int:
    """QACC 판정은 문항 수준이다 — 같은 question_id의 행들을 한 번에 판정한다.

    판정자의 원 판정은 judges/judge{N}.csv에 증거로 남기고(검토 CSV는 스키마 열만 유지),
    두 판정자가 **일치할 때만** 검토 CSV의 exclusion_flag·conflict_type에 반영한다."""
    by_item: dict[str, list[dict]] = {}
    for r in rows:
        by_item.setdefault(r["question_id"], []).append(r)

    mine = _read_judge(judge_dir / f"judge{judge_idx}.csv")
    other = _read_judge(judge_dir / f"judge{2 if judge_idx == 1 else 1}.csv")
    todo = [(qid, rs) for qid, rs in by_item.items() if qid not in mine]

    for qid, rs in tqdm(todo, desc=f"qacc/judge{judge_idx}/{model}", unit="item"):
        head = rs[0]
        docs = "\n".join(f"[{i + 1}] {' '.join((r.get('text') or '').split()[:60])}"
                          for i, r in enumerate(rs))
        gold = (head.get("correct_answer") or "").strip()
        wrong = sorted({(r.get("supported_answer") or "").strip() for r in rs}
                       - {"", gold})
        raw = ask(client, model, QACC_PROMPT.format(
            question=head["question"], gold=gold or "(재검증 필요)",
            wrong=" | ".join(wrong), docs=docs))
        verdict = form_field(raw, "verdict", ("sharp", "soft")) or ""
        ctype = form_field(raw, "type",
                           ("outdated", "misinformation", "conflicting_opinions",
                            "na")) or ""
        mine[qid] = {"question_id": qid, "verdict": verdict,
                     "conflict_type": "" if ctype == "na" else ctype, "model": model}

    _write_judge(mine, judge_dir / f"judge{judge_idx}.csv")

    # 두 판정자가 모두 판정한 문항만, 그리고 일치할 때만 검토 CSV에 반영한다
    n_applied = 0
    for qid, rs in by_item.items():
        a, b = mine.get(qid), other.get(qid)
        if not a or not b:
            continue
        if a["verdict"] and a["verdict"] == b["verdict"]:
            for r in rs:
                if (r.get("exclusion_flag") or "").strip() != PENDING_SCREEN:
                    continue      # 다른 사유로 이미 제외된 문항은 건드리지 않는다
                r["exclusion_flag"] = "" if a["verdict"] == "sharp" else SOFT_CONFLICT
            n_applied += 1
        if a["conflict_type"] and a["conflict_type"] == b["conflict_type"]:
            for r in rs:
                r["conflict_type"] = a["conflict_type"]
    if other:
        print(f"판정자 2종 일치로 반영된 문항: {n_applied} "
              f"(불일치는 '{PENDING_SCREEN}'로 남아 사람이 adjudication)")
    return len(todo)


def _read_judge(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig") as f:
        return {r["question_id"]: r for r in csv.DictReader(f)}


def _write_judge(records: dict[str, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["question_id", "verdict", "conflict_type", "model"])
        w.writeheader()
        w.writerows(records.values())


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
    ap.add_argument("--data-dir", default="data/2_review", type=Path)
    args = ap.parse_args()

    ds = args.dataset
    review_dir = args.data_dir / ds
    client = make_client(args.base_url, args.api_key)

    if ds == "dragged":
        # 검토가 필요한 것은 사실 충돌뿐 — 나머지 유형은 정답이 없어 라벨이 채점에 쓰이지 않는다
        total = 0
        for ctype in FACT_CONFLICT_TYPES:
            draft = review_dir / f"{ds}_{ctype}.draft.csv"
            llm = review_dir / f"{ds}_{ctype}.llm.csv"
            if not draft.exists():
                raise SystemExit(f"입력 CSV 없음: {draft} — "
                                 f"`python -m preprocessing.{ds}_prep draft` 먼저 실행")
            src = llm if llm.exists() else draft     # 재개: 채우던 파일에 이어 쓴다
            rows = read_csv(src)
            n = run_dragged(client, args.model, rows, args.only_flagged)
            write_rows(rows, llm)
            print(f"  {ctype}: {n}건 판정 → {llm.name}")
            total += n
        print(f"\n총 {total}건 판정")
        print(f"→ {review_dir}/dragged_{{temporal,misinfo}}.llm.csv 를 열어 `label`을 확인·수정한 뒤 "
              f"`python -m preprocessing.{ds}_prep build` 실행")
    else:
        draft_csv = review_dir / f"{ds}.draft.csv"
        llm_csv = review_dir / f"{ds}.llm.csv"
        src = llm_csv if llm_csv.exists() else draft_csv
        if not src.exists():
            raise SystemExit(f"입력 CSV 없음: {src} — "
                             f"`python -m preprocessing.{ds}_prep draft` 먼저 실행")
        rows = read_csv(src)
        n = run_qacc(client, args.model, rows, args.judge, review_dir / "judges")
        write_rows(rows, llm_csv)
        print(f"\n{n}건 판정 → {llm_csv}")
        print(f"→ 이 CSV를 열어 확인·수정한 뒤 `python -m preprocessing.{ds}_prep build` 실행")


if __name__ == "__main__":
    main()
