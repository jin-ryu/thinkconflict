"""실험 1 — 5개 평가 환경 (계획서 §3.3.2).

| 환경               | 분류      | 적용 데이터셋                              |
|--------------------|-----------|--------------------------------------------|
| standard           | 대조군    | 전체                                       |
| cad                | 디코딩    | 전체 (이중 패스 — cad.py 참조)             |
| cd2                | 디코딩    | 전체 (이중 패스 — cd2.py 참조)             |
| recency_authority  | 프롬프트  | DRAGged·QACC만 — RAMDocs는 date/url 부재로 미적용(결측 셀 명시) |
| reflection         | 프롬프트  | 전체                                       |

프롬프트 환경은 여기서 메시지를 완결하고, 디코딩 환경(cad/cd2)은 standard와 동일한
프롬프트를 쓰되 생성 시 로짓 대비가 별도로 걸린다(env 이름은 기록·집계 키로 유지).
"""
from __future__ import annotations

SYSTEM = (
    "You are a careful assistant answering questions from retrieved web documents. "
    "Read the documents and answer the question. Give a single final answer."
)

RECENCY_AUTHORITY_GUIDE = (
    "The documents may conflict with each other. When they do, resolve the conflict "
    "by explicitly comparing (1) recency — prefer the document with the most recent "
    "date for time-sensitive facts — and (2) source authority — prefer official or "
    "reputable sources (check the URL) over unreliable ones. State which document "
    "you rely on, then give a single final answer."
)

REFLECTION_GUIDE = (
    "After drafting your answer, reflect before finalizing: (1) Is your conclusion "
    "actually supported by the documents you cited? (2) Did you check whether any "
    "documents conflict, and did you resolve the conflict correctly? (3) Does your "
    "final answer match the conclusion you reached while reasoning? Revise if any "
    "check fails, then give a single final answer."
)  # Self-RAG의 반추 전략만 프롬프트로 차용 (원본은 학습된 별도 모델 — §3.3.2 ⑤)


def _user(question: str, documents: str, guide: str | None = None) -> str:
    parts = [f"Documents:\n\n{documents}"]
    if guide:
        parts.append(guide)
    parts.append(f"Question: {question}")
    return "\n\n".join(parts)


ENVS = {
    "standard": lambda q, docs: [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": _user(q, docs)}],
    "cad": lambda q, docs: [  # 프롬프트는 standard와 동일 — 대비는 디코딩에서 (cad.py)
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": _user(q, docs)}],
    "cd2": lambda q, docs: [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": _user(q, docs)}],
    "recency_authority": lambda q, docs: [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": _user(q, docs, RECENCY_AUTHORITY_GUIDE)}],
    "reflection": lambda q, docs: [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": _user(q, docs, REFLECTION_GUIDE)}],
}

# 환경×데이터셋 결측 셀 (§3.3.2 적용성 — 완전 격자 아님, 표에 명시)
INAPPLICABLE = {("recency_authority", "ramdocs_a"), ("recency_authority", "ramdocs_b")}


def build_messages(env: str, question: str, documents: str) -> list[dict]:
    return ENVS[env](question, documents)


def applicable(env: str, dataset: str) -> bool:
    return (env, dataset) not in INAPPLICABLE
