"""채점기: 동치 판정 · any-gold · 기권 분리 (계획서 §3.2.1, 사전등록 §1.3~1.5).

Final Action 라벨 {correct, wrong, abstain}을 산출한다.
- correct = 정규화(별칭·수치·날짜 형식 통일) + 동치 판정 기반 정확도. 문자열 EM 아님.
- any-gold = 정답 집합 중 하나라도 동치이면 correct.
- abstain = 확정 답을 내지 않음. wrong과 분리하며 AIR·오답률 분모에서 제외(별도 기권율).

규칙 기반 동치가 판정 불가한 표현 차이는 LLM 판정자(diagnosis.labeler의 judge)로
이관한다 — 여기서는 결정적(deterministic) 채점만 담당해 재현성을 보장한다.
"""
from __future__ import annotations

import re
import unicodedata

from dateutil import parser as dateparser

ABSTAIN_PATTERNS = [  # 확정 답 회피 표지 (사전등록 §1.3; 실측 후 개정 이력으로만 추가)
    r"\bcannot (?:be )?determin", r"\bcannot answer", r"\bunable to answer",
    r"\bnot possible to (?:say|determine|answer)", r"\binsufficient information",
    r"\bno definitive answer", r"\bunclear from the (?:documents|context)",
    r"\bI don'?t know", r"\bconflicting (?:information|sources).{0,40}cannot",
]
_ARTICLES = ("the ", "a ", "an ")


def normalize(s: str) -> str:
    """별칭·수치·형식 정규화: 소문자화, 유니코드 정규화, 관사·구두점 제거, 수치 통일."""
    s = unicodedata.normalize("NFKD", s).lower().strip()
    # 천 단위 구분자는 구두점 제거보다 먼저 접는다 ("3,559" → "3 559"가 되지 않도록)
    while re.search(r"\d,\d{3}(?!\d)", s):
        s = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", s)
    s = re.sub(r"[.,;:!?\"'()\[\]]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for art in _ARTICLES:
        if s.startswith(art):
            s = s[len(art):]
    return s


def _as_date(s: str):
    try:
        d = dateparser.parse(s, fuzzy=False)
        return (d.year, d.month, d.day)
    except (ValueError, OverflowError):
        return None


def equivalent(pred: str, gold: str) -> bool:
    """동치 판정: 정규화 일치, 포함(짧은 gold가 pred 안에), 날짜 동치."""
    p, g = normalize(pred), normalize(gold)
    if not p or not g:
        return False
    if p == g or g in p:
        return True
    dp, dg = _as_date(pred), _as_date(gold)
    if dp and dg and dp == dg:
        return True
    return False


def is_abstain(answer: str) -> bool:
    return any(re.search(pat, answer, re.IGNORECASE) for pat in ABSTAIN_PATTERNS)


def grade(answer: str | None, correct_answers: list[str],
          wrong_answers: list[str] | None = None) -> str:
    """Final Action 라벨을 반환한다: 'correct' | 'wrong' | 'abstain'.

    any-gold: correct_answers 중 하나라도 동치면 correct (사전등록 §1.5).
    abstain 판정이 동치 판정보다 우선한다 — 단, 기권 표지가 있어도 정답을
    함께 확정 표출한 경우(예: "정확히 단정할 수 없으나 답은 X")는 correct다.
    """
    if answer is None or not answer.strip():
        return "abstain"
    if any(equivalent(answer, gold) for gold in correct_answers):
        return "correct"
    if is_abstain(answer):
        return "abstain"
    return "wrong"


def abstain_rate(labels: list[str]) -> float:
    """환경 간 의무 보고 기권율 (사전등록 §1.3 — AIR과 나란히 보고)."""
    return labels.count("abstain") / len(labels) if labels else 0.0
