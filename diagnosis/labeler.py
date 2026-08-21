"""L1(탐지)·L2(해소)·FA(표출) 3단계 라벨러 (계획서 §3.2.1, 부록 A).

하이브리드 라벨링: ① 규칙 기반(문서 인덱스 인용, 날짜/URL 키워드) 1차 → ② 규칙이
확신하지 못하는 케이스만 LLM-as-a-Judge로 이관. 판정자는 대상 모델과 다른 계열
2종(오픈+상용), 형식-채움 프로토콜, 옵션 무작위 스왑(부록 A(a)) — 판정자 호출부는
JudgeFn으로 주입해 이 모듈은 결정적 부분과 프로토콜만 소유한다.

사전등록 규칙 반영:
- L2 결론 = 트레이스 내 **마지막 명시적 문서 지지** (§1.2). 번복 횟수는 부가 신호.
- 암묵적 leaning은 L2 본 라벨에 합치지 않고 부가 라벨로만 기록.
- Blind-Hit 등 부재 조건 라벨은 '언어화된' 상태임을 필드명에 유지.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

from diagnosis.grading import adopted_wrong_answer, grade
from preprocessing.llm_assist import form_field
from diagnosis.trace_parser import ParsedTrace
from preprocessing.schema import Item

# ── 규칙 기반 신호 ────────────────────────────────────────────────────────────

CONFLICT_CUES = [  # L1 탐지 표지 (언어화된 충돌 인지)
    r"\bconflict", r"\bcontradict", r"\bdisagree", r"\binconsisten",
    r"\bdiffer(?:s|ent|ing) (?:answers?|dates?|numbers?|figures?|claims?)",
    r"\b(?:however|whereas|while) document", r"\bnot (?:all|every) documents? agree",
    r"\bsome documents? (?:say|state|claim)", r"\boutdated", r"\bmisinformation",
    r"\bdiscrepanc",
]
TYPE_CUES = {  # 유형 인지 (부가 축): 원인 유형까지 짚었는가
    "outdated": [r"\boutdated", r"\bmore recent", r"\bnewer", r"\bolder (?:article|source|document)",
                 r"\b(?:19|20)\d{2}\b.{0,40}\b(?:19|20)\d{2}\b", r"\bfresher", r"\blatest"],
    "misinformation": [r"\bmisinformation", r"\bunreliable", r"\bcredib", r"\btrustworth",
                r"\bauthorit", r"\bofficial (?:source|site|website)", r"\breputable"],
    "conflicting_opinions": [r"\bopinion", r"\bsubjective", r"\bperspective",
                             r"\bviewpoint", r"\bdebat"],
}
# "[Document 3]", "document 3", "doc 3" 인용 + 지지/기각 동사 문맥
DOC_REF_RE = re.compile(r"\[?doc(?:ument)?s?\s*(\d{1,2})\]?", re.IGNORECASE)
SUPPORT_CUES = r"(?:correct|right|accurate|valid|reliable|most recent|latest|up.to.date|trust|support|confirm|best answer|should (?:be )?(?:use|follow|trust))"
REJECT_CUES = r"(?:outdated|incorrect|wrong|unreliable|misinformation|stale|old|reject|dismiss|ignore)"


# 자기일관성 트랙의 답변 입장 라벨 (§3.2 이중 트랙, 사전등록 §1.8)
STANCE_LABELS = ("maintain", "flip", "hedge")
HEDGE_CUES = [
    r"\bboth (?:views|sides|positions|answers)", r"\bexperts? (?:disagree|are divided)",
    r"\bon the one hand\b.{0,200}\bon the other hand\b",
    r"\bsources? (?:disagree|differ|conflict)", r"\bit depends\b",
    r"\bsome (?:say|argue|claim).{0,120}\bothers (?:say|argue|claim)",
    r"\bno (?:clear|single|definitive) (?:answer|consensus)",
]


@dataclass
class StageLabels:
    l1: str                     # detected | unrecognized  (언어화 기준)
    l2: str | None              # correct | wrong | unresolved | None(비채점 트랙)
    fa: str | None              # correct | wrong | abstain | None(정답 없는 문항 = 채점 불가)
    stance: str | None = None   # maintain | flip | hedge | None(자기일관성 트랙 아님)
    path: str | None = None     # legitimate | shortcut | discordant_hit | blind_hit | None
    type_recognition: str | None = None   # correct_type | surface_only | None(L1 미탐지)
    l2_flip_count: int = 0      # 번복 횟수 (부가 신호, 부록 B 연계)
    adopted_wrong: str | None = None   # 문서에 실린 오답을 그대로 채택했는가 (부가 관측)
    l2_char_offset: int | None = None  # 해소 확정 지점 (RCPD·resampling 국소화용)
    implicit_leaning: str | None = None  # 암묵적 기울기 백스톱 (부가 라벨 전용)
    provenance: dict = field(default_factory=dict)  # rule/judge 판정 출처


class JudgeFn(Protocol):
    """LLM 판정자 호출 시그니처: (질문, 트레이스, 문서요약, 과제) → 라벨 문자열."""
    def __call__(self, question: str, trace: str, docs_summary: str, task: str) -> str: ...


def detect_l1(thinking: str | None) -> bool:
    if not thinking:
        return False
    return any(re.search(p, thinking, re.IGNORECASE) for p in CONFLICT_CUES)


def recognize_type(thinking: str, gold_type: str) -> str:
    cues = TYPE_CUES.get(gold_type, [])
    hit = any(re.search(p, thinking, re.IGNORECASE) for p in cues)
    return "correct_type" if hit else "surface_only"


# 문장/절 경계 — 지지 판독은 이 안에서만. 대조 접속사까지 경계로 삼는 이유는 실측:
# "ignore the contradictory Beatles mentions ..., while Doc 2 is explicitly titled ..."
# 에서 앞 절의 'ignore'가 Doc 2의 기각으로 읽혀 correct 문서가 wrong으로 뒤집혔다.
SENT_BREAK_RE = re.compile(
    r"[.!?;:,\n]|\b(?:while|whereas|but|however|although|though|meanwhile|yet)\b",
    re.IGNORECASE)


def _cue_window(thinking: str, refs: list[re.Match], i: int) -> str:
    """인용 refs[i]에 귀속시킬 수 있는 텍스트 구간.

    같은 문장 안에서, 앞뒤로 **인접한 다른 문서 인용을 넘지 않는** 범위만 돌려준다.
    'Doc 2 and Doc 5' 처럼 인용이 연달아 오면 그 사이에는 동사가 없으므로 두 인용
    모두 빈 구간을 받아 기권하게 되고, 문장 앞의 'trust'는 가장 가까운 인용(Doc 2)에만
    귀속된다 — 엉뚱한 인용에 동사가 붙는 것을 막는 것이 목적이다.
    """
    m = refs[i]
    lo = refs[i - 1].end() if i > 0 else 0
    hi = refs[i + 1].start() if i + 1 < len(refs) else len(thinking)
    before = thinking[lo:m.start()]
    after = thinking[m.end():hi]
    # 문장 경계에서 자른다: 앞은 마지막 경계 이후, 뒤는 첫 경계 이전
    breaks = list(SENT_BREAK_RE.finditer(before))
    if breaks:
        before = before[breaks[-1].end():]
    nxt = SENT_BREAK_RE.search(after)
    if nxt:
        after = after[:nxt.start()]
    return before + " " + after


def last_explicit_support(thinking: str, doc_order: list[int],
                          item: Item) -> tuple[str | None, int, int | None]:
    """마지막 명시적 문서 지지를 찾아 (지지 문서의 원본 라벨 기반 L2, 번복 횟수, 지점)을 반환.

    트레이스의 '[Document k]'는 렌더링 위치 k이므로 doc_order로 원본 doc_id로 환원한다.
    반환 L2: 'correct'/'wrong' (지지 문서 라벨 기준) 또는 None(명시적 지지 없음 → unresolved).
    """
    label_by_id = {c.doc_id: c.label for c in item.chunks}
    stances: list[tuple[int, str]] = []  # (offset, 'correct'|'wrong')
    refs = [m for m in DOC_REF_RE.finditer(thinking)]
    for i, m in enumerate(refs):
        pos = int(m.group(1))
        if not (1 <= pos <= len(doc_order)):
            continue
        # 지지/기각 동사는 인용 뒤에도("Doc 3 is outdated") 앞에도("I will trust Doc 2")
        # 온다. 뒤 고정폭만 보면 다음 문장의 동사를 이 인용에 잘못 붙인다 — 실측 실패:
        # "Doc 3's 1885 is a scraping error. I will trust the text in Doc 2 and Doc 5."
        # 에서 'trust'가 Doc 3의 지지로 읽혀 conflict 문서를 지지한 것으로 뒤집혔다.
        # 따라서 **같은 문장 안**만 보고, 그 안에서도 다른 인용을 넘지 않는 구간만 본다.
        window = _cue_window(thinking, refs, i)
        support = re.search(SUPPORT_CUES, window, re.IGNORECASE)
        reject = re.search(REJECT_CUES, window, re.IGNORECASE)
        if not support and not reject:
            continue
        if support and reject:
            continue   # 같은 구간에 지지·기각이 공존 = 판독 불가. 규칙은 기권하고
                       # 판정자에게 넘긴다 (과확신이 무판정보다 나쁘다, 부록 A(a))
        doc_label = label_by_id.get(doc_order[pos - 1], "unknown")
        if doc_label not in ("correct", "conflict"):
            continue
        backs_gold = (doc_label == "correct") == bool(support)
        stances.append((m.start(), "correct" if backs_gold else "wrong"))
    if not stances:
        return None, 0, None
    flips = sum(1 for a, b in zip(stances, stances[1:]) if a[1] != b[1])
    offset, verdict = stances[-1]
    return verdict, flips, offset


def detect_hedge(answer: str | None) -> bool:
    """답변이 양쪽 입장을 나란히 병기했는가 (§3.2: hedge는 불일치가 아니다)."""
    if not answer:
        return False
    return any(re.search(p, answer, re.IGNORECASE) for p in HEDGE_CUES)


def label_stance(parsed: ParsedTrace, item: Item,
                 judge: JudgeFn | None = None) -> str | None:
    """자기일관성 트랙: 트레이스가 잡은 입장을 최종 답변이 유지했는가 (§3.2 이중 트랙).

    정답이 없는 문항(의견 충돌)에서도 "사고에서 A라 해놓고 답변은 B라 했는가"는 잴 수 있다.
    hedge(양쪽 병기)는 **불일치가 아니라 별도 집계**다 — 의견 질의에서 병기는 정당한 행동일
    수 있으므로 오분류를 막는다(사전등록 §1.8).
    """
    if not parsed.thinking or not parsed.answer:
        return None
    if detect_hedge(parsed.answer):
        return "hedge"
    if judge is None:
        return None          # 규칙으로는 입장 대조가 불가 — 판정자가 필요하다
    verdict = judge(item.question, parsed.thinking, parsed.answer,
                    task="answer_stance_vs_trace")
    return verdict if verdict in STANCE_LABELS else None


def label_generation(parsed: ParsedTrace, item: Item, doc_order: list[int],
                     judge: JudgeFn | None = None) -> StageLabels:
    """생성 1건의 3단계 라벨 + 4경로 귀속 (사전등록 §1.1~1.7).

    정답이 없는 문항(의견 충돌 115건)은 채점(FA)이 성립하지 않으므로 fa=None이 되고,
    대신 자기일관성 라벨(stance)만 산출한다 — 이중 트랙(§3.2)."""
    fa = grade(parsed.answer, item.correct_answers)
    thinking = parsed.thinking or ""
    l1_detected = detect_l1(thinking)
    prov = {"l1": "rule", "l2": "rule", "fa": "rule"}

    l2 = None
    flips, offset = 0, None
    # L2(해소)는 정답과 확정된 문서 라벨이 있어야 판정된다 — 의견 충돌엔 성립하지 않는다
    if item.correct_answers and l1_detected:
        verdict, flips, offset = last_explicit_support(thinking, doc_order, item)
        l2 = verdict or "unresolved"
        if verdict is None and judge is not None:
            # 규칙이 명시적 지지를 못 찾은 케이스만 판정자 이관 (하이브리드).
            # 판정 과제는 '입장 독해' 수준 — 골드 매핑이 정답 문서를 제공한 상태 (부록 A(a)).
            docs = "\n".join(f"[{i+1}] label={item.chunks[d].label}"
                             for i, d in enumerate(doc_order))
            j = judge(item.question, thinking, docs, task="l2_last_explicit_support")
            if j in ("correct", "wrong", "unresolved"):
                l2, prov["l2"] = j, "judge"

    path = None
    if fa == "correct":
        if not l1_detected:
            path = "blind_hit"
        elif l2 == "correct":
            path = "legitimate"
        elif l2 == "wrong":
            path = "discordant_hit"
        else:  # unresolved 또는 비채점 트랙
            path = "shortcut"

    return StageLabels(
        l1="detected" if l1_detected else "unrecognized",
        l2=l2, fa=fa, path=path,
        stance=label_stance(parsed, item, judge),
        type_recognition=(recognize_type(thinking, item.conflict_type)
                          if l1_detected and item.conflict_type in TYPE_CUES else None),
        l2_flip_count=flips, l2_char_offset=offset, provenance=prov,
        adopted_wrong=(adopted_wrong_answer(parsed.answer, item.wrong_answers)
                       if fa == "wrong" else None),
    )


# ── 판정자 프로토콜 헬퍼 (부록 A(a): 형식-채움 + 옵션 스왑) ────────────────────

def make_judge_prompt(question: str, trace: str, docs_summary: str,
                      task: str, swap_options: bool) -> str:
    options = ["correct", "wrong", "unresolved"]
    if swap_options:
        options = options[::-1]
    return (
        "You are grading which document a reasoning trace ultimately supports.\n"
        f"Task: {task}. The gold document labels are provided — you only need to "
        "read the trace's final explicit stance, not resolve the conflict yourself.\n\n"
        f"Question: {question}\n\nDocuments:\n{docs_summary}\n\nTrace:\n{trace}\n\n"
        "Fill the form (one word):\n"
        f"final_stance ∈ {{{', '.join(options)}}} = "
    )


def build_openai_judge(client, model: str, *, swap_options: bool = False) -> JudgeFn:
    """OpenAI 호환 클라이언트를 JudgeFn으로 감싼다. 대상 모델과 동일 계열 판정 금지는
    호출부(실험 스크립트)에서 모델 매핑으로 강제한다."""
    def _judge(question: str, trace: str, docs_summary: str, task: str) -> str:
        prompt = make_judge_prompt(question, trace, docs_summary, task, swap_options)
        kw = {"model": model, "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.0, "max_tokens": 256}
        # 사고형 판정자는 짧은 예산을 사고에 다 쓰고 폼 값에 도달하지 못한다. 끄는 방법이
        # 계열마다 달라 순서대로 시도한다 (Qwen: chat_template_kwargs, gpt-oss: effort).
        for extra in ({"chat_template_kwargs": {"enable_thinking": False}},
                      {"reasoning_effort": "low"}, None):
            try:
                resp = client.chat.completions.create(**kw, extra_body=extra)
            except Exception:  # noqa: BLE001 — 엔드포인트가 그 인자를 모르는 경우
                continue
            text = (resp.choices[0].message.content or "").strip()
            if text:
                # 판정자가 선택지 목록을 되받아쓰면 앞에서부터 찾을 때 첫 선택지를
                # 집는다 — 폼 값만 읽도록 필드 기준으로 뽑는다 (llm_assist와 같은 규약).
                return form_field(text, "final_stance",
                                  ("correct", "wrong", "unresolved")) or ""
        return ""
    return _judge
