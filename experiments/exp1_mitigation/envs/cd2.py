"""CD2 디코딩 환경 (계획서 §3.3.2 ③; Jin et al., 2024, Tug-of-War).

CAD가 '문맥 vs 파라메트릭'을 대비한다면, CD2는 **문서 간(inter-context) 충돌 자체**를
겨냥한다: 상충 문서 그룹을 분리해 각 그룹 조건부 분포를 만들고 대비 디코딩으로
정답 지지 그룹 쪽 생성을 강화한다 — 본 진단(충돌 해소)과 가장 직접 맞물리는 기법.

구현 노트 (Phase 4): 공통 스키마의 chunk 라벨(correct/conflicting)로 문서 그룹을
구성할 수 있어 그룹 분리는 자명하다. CAD와 동일한 vLLM 커스텀 스텝 디코딩 루프를
공유하고(logits 결합부만 교체), 그룹별 프롬프트 렌더링은 schema.render_documents를
그룹 부분집합에 적용해 만든다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CD2Config:
    alpha: float = 1.0
    span: str = "full"  # CAD와 동일 절제 축을 공유해 비교 가능하게 유지


def run(cfg: CD2Config, *args, **kwargs):
    raise NotImplementedError(
        "Phase 4에서 구현: cad.py와 스텝 디코딩 루프 공유, 로짓 결합부만 교체.")
