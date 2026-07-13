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
# 내용어 판정용 불용어 — 앵커 커버리지 계산에서 제외한다
_STOP = frozenset(
    "the a an of in on at to for and or is are was were be been by with from as that "
    "this it its his her their there here no not do does did will would can could "
    "about into over under above below between during since until".split())


def normalize(s: str) -> str:
    """표기 정규화 (사전등록 §1.4 — 표기 노이즈가 AIR로 새는 것을 막는다).

    실측 gold 문자열이 요구한 처리: 천 단위 쉼표("3,559") · 하이픈("EL-Capitan") ·
    서수("November 27th") · 괄호("Jannik Sinner ( ITA )") · 마침표.
    """
    s = unicodedata.normalize("NFKD", s).lower().strip()
    # 천 단위 구분자는 구두점 제거보다 먼저 접는다 ("3,559" → "3 559"가 되지 않도록)
    while re.search(r"\d,\d{3}(?!\d)", s):
        s = re.sub(r"(\d),(\d{3})(?!\d)", r"\1\2", s)
    s = re.sub(r"(\d+)(?:st|nd|rd|th)\b", r"\1", s)     # 27th → 27
    s = re.sub(r"[-–—/]", " ", s)                        # EL-Capitan → el capitan
    s = re.sub(r"[.,;:!?\"'’()\[\]]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for art in _ARTICLES:
        if s.startswith(art):
            s = s[len(art):]
    return s


def _numbers(norm_s: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", norm_s))


def _content(norm_s: str) -> list[str]:
    """수치를 뺀 내용어. 앵커 커버리지의 분모가 된다."""
    return [t for t in re.findall(r"[a-z]+", norm_s) if t not in _STOP]


def _as_date(s: str):
    try:
        d = dateparser.parse(s, fuzzy=False)
        return (d.year, d.month, d.day)
    except (ValueError, OverflowError):
        return None


def equivalent(pred: str, gold: str) -> bool:
    """동치 판정 (문자열 EM 아님 — 사전등록 §1.4).

    DRAGged gold는 답의 핵심만 담기도 하고("at least 1,759") 문장으로 서술되기도 한다
    ("For 2025 it is November 27th", 사실 충돌 67건 중 10건). 후자에서 모델이 핵심만
    답하면("November 27, 2025") 단순 포함 검사는 오답 처리해 AIR을 부풀린다.
    따라서 gold의 **수치 앵커는 전부**, **내용어는 다수** 재현했는지로 판정한다.
    수치는 엄격히 요구하므로 "November 20"을 "November 27th"의 동치로 받지 않는다.
    """
    p, g = normalize(pred), normalize(gold)
    if not p or not g:
        return False
    if p == g or g in p:               # gold가 핵심만 담은 일반적 경우
        return True
    dp, dg = _as_date(pred), _as_date(gold)
    if dp and dg and dp == dg:
        return True

    gnums, pnums = _numbers(g), _numbers(p)
    gtok, ptok = _content(g), _content(p)
    if gnums and not gnums <= pnums:   # gold의 수치를 하나라도 놓치면 동치가 아니다
        return False

    if p in g:                         # 모델 답이 서술형 gold의 연속 부분 = 답의 핵심
        if gnums:
            return True                # 수치 앵커를 모두 담았음이 위에서 보장됨
        return len(ptok) >= 2 and set(ptok) <= set(gtok)
    if gnums and gtok:                 # 어순이 바뀐 재서술 — 내용어 다수 재현을 요구
        return len(set(gtok) & set(ptok)) / len(set(gtok)) >= 0.6
    return False


def is_abstain(answer: str) -> bool:
    return any(re.search(pat, answer, re.IGNORECASE) for pat in ABSTAIN_PATTERNS)


def grade(answer: str | None, correct_answers: list[str]) -> str:
    """Final Action 라벨을 반환한다: 'correct' | 'wrong' | 'abstain'.

    any-gold: correct_answers 중 하나라도 동치면 correct (사전등록 §1.5).
    abstain 판정이 동치 판정보다 우선한다 — 단, 기권 표지가 있어도 정답을
    함께 확정 표출한 경우(예: "정확히 단정할 수 없으나 답은 X")는 correct다.

    오답의 '종류'(오정보 문서의 답을 채택했는지 vs 엉뚱한 답인지)는 이 라벨을
    바꾸지 않는다 — 사전등록 지표는 correct/wrong/abstain 3분류이므로. 그 구분이
    필요하면 adopted_wrong_answer()로 별도 관측한다.
    """
    if answer is None or not answer.strip():
        return "abstain"
    if any(equivalent(answer, gold) for gold in correct_answers):
        return "correct"
    if is_abstain(answer):
        return "abstain"
    return "wrong"


def adopted_wrong_answer(answer: str | None, wrong_answers: list[str]) -> str | None:
    """모델이 **문서에 실린 특정 오답을 그대로 채택**했는지 (부가 관측, 지표 아님).

    "충돌 문서의 오정보를 삼켰다"와 "엉뚱한 답을 지어냈다"는 실패의 성격이 다르므로
    구분해 볼 수 있게 한다. FA 라벨(correct/wrong/abstain)에는 영향을 주지 않는다.
    wrong_answers가 원본에 있는 데이터셋(RAMDocs·QACC)에서만 의미가 있다.
    """
    if not answer or not wrong_answers:
        return None
    return next((w for w in wrong_answers if equivalent(answer, w)), None)


def abstain_rate(labels: list[str]) -> float:
    """환경 간 의무 보고 기권율 (사전등록 §1.3 — AIR과 나란히 보고)."""
    return labels.count("abstain") / len(labels) if labels else 0.0
