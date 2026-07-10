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

from diagnosis.grading import grade
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
    "temporal": [r"\boutdated", r"\bmore recent", r"\bnewer", r"\bolder (?:article|source|document)",
                 r"\b(?:19|20)\d{2}\b.{0,40}\b(?:19|20)\d{2}\b", r"\bfresher", r"\blatest"],
    "misinfo": [r"\bmisinformation", r"\bunreliable", r"\bcredib", r"\btrustworth",
                r"\bauthorit", r"\bofficial (?:source|site|website)", r"\breputable"],
    "opinion": [r"\bopinion", r"\bsubjective", r"\bperspective", r"\bviewpoint", r"\bdebat"],
}
# "[Document 3]", "document 3", "doc 3" 인용 + 지지/기각 동사 문맥
DOC_REF_RE = re.compile(r"\[?doc(?:ument)?s?\s*(\d{1,2})\]?", re.IGNORECASE)
SUPPORT_CUES = r"(?:correct|right|accurate|valid|reliable|most recent|latest|up.to.date|trust|support|confirm|best answer|should (?:be )?(?:use|follow|trust))"
REJECT_CUES = r"(?:outdated|incorrect|wrong|unreliable|misinformation|stale|old|reject|dismiss|ignore)"


@dataclass
class StageLabels:
    l1: str                     # detected | unrecognized  (언어화 기준)
    l2: str | None              # correct | wrong | unresolved | None(비채점 트랙)
    fa: str                     # correct | wrong | abstain
    path: str | None            # legitimate | shortcut | discordant_hit | blind_hit | None(오답·기권)
    type_recognition: str | None = None   # correct_type | surface_only | None(L1 미탐지)
    l2_flip_count: int = 0      # 번복 횟수 (부가 신호, 부록 B 연계)
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


def last_explicit_support(thinking: str, doc_order: list[int],
                          item: Item) -> tuple[str | None, int, int | None]:
    """마지막 명시적 문서 지지를 찾아 (지지 문서의 원본 라벨 기반 L2, 번복 횟수, 지점)을 반환.

    트레이스의 '[Document k]'는 렌더링 위치 k이므로 doc_order로 원본 doc_id로 환원한다.
    반환 L2: 'correct'/'wrong' (지지 문서 라벨 기준) 또는 None(명시적 지지 없음 → unresolved).
    """
    label_by_id = {c.doc_id: c.label for c in item.chunks}
    stances: list[tuple[int, str]] = []  # (offset, 'correct'|'wrong')
    for m in DOC_REF_RE.finditer(thinking):
        pos = int(m.group(1))
        if not (1 <= pos <= len(doc_order)):
            continue
        window = thinking[m.end(): m.end() + 160]  # 인용 직후 문맥에서 지지/기각 판독
        support = re.search(SUPPORT_CUES, window, re.IGNORECASE)
        reject = re.search(REJECT_CUES, window, re.IGNORECASE)
        if not support and not reject:
            continue
        doc_label = label_by_id.get(doc_order[pos - 1], "unknown")
        if doc_label not in ("correct", "conflicting"):
            continue
        backs_gold = (doc_label == "correct") == bool(support and not reject)
        stances.append((m.start(), "correct" if backs_gold else "wrong"))
    if not stances:
        return None, 0, None
    flips = sum(1 for a, b in zip(stances, stances[1:]) if a[1] != b[1])
    offset, verdict = stances[-1]
    return verdict, flips, offset


def label_generation(parsed: ParsedTrace, item: Item, doc_order: list[int],
                     judge: JudgeFn | None = None) -> StageLabels:
    """생성 1건의 3단계 라벨 + 4경로 귀속 (사전등록 §1.1~1.7)."""
    fa = grade(parsed.answer, item.correct_answers, item.wrong_answers)
    thinking = parsed.thinking or ""
    l1_detected = detect_l1(thinking)
    prov = {"l1": "rule", "l2": "rule", "fa": "rule"}

    l2 = None
    flips, offset = 0, None
    if item.behavior_track and l1_detected:
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
        type_recognition=(recognize_type(thinking, item.conflict_type)
                          if l1_detected and item.conflict_type in TYPE_CUES else None),
        l2_flip_count=flips, l2_char_offset=offset, provenance=prov,
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
        resp = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=8)
        return (resp.choices[0].message.content or "").strip().lower().split()[0]
    return _judge
