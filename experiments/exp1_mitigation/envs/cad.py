"""CAD / AdaCAD 디코딩 환경 (계획서 §3.3.2 ②; Shi et al., 2024; Wang et al., 2025).

문맥 유무 두 분포의 로짓 차이를 대비 증폭해 생성을 제공 문맥 쪽으로 민다:
    logits_cad = (1 + α) · logits(문맥 포함) − α · logits(문맥 제거)
AdaCAD는 α를 두 분포의 JSD로 스텝마다 적응 조정한다.

사전등록된 절제(ablation) 2방식 — 대비 적용 구간:
    (i)  full   — 사고 + 답변 전 구간
    (ii) answer — `</think>` 이후 답변 구간 한정

구현 노트 (Phase 4): 표준 OpenAI 엔드포인트로는 이중 패스 로짓 결합이 불가하므로
vLLM 파이썬 API로 프롬프트 2종(문맥 포함/제거)을 병렬 스텝 디코딩하며 로짓을 결합하는
커스텀 루프가 필요하다. 이 모듈은 그 루프의 설정·인터페이스를 소유한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CADConfig:
    alpha: float = 1.0          # CAD 고정 α (원 논문 기본값 계열; Phase 4에서 스윕 확정)
    adaptive: bool = False      # True = AdaCAD (JSD 기반 적응 α)
    span: str = "full"          # "full" | "answer" — 사전등록 절제 2방식


def contrast_logits(logits_with_ctx, logits_without_ctx, alpha: float):
    """logits_cad = (1+α)·with − α·without. (vLLM 커스텀 루프에서 스텝마다 호출)"""
    return (1 + alpha) * logits_with_ctx - alpha * logits_without_ctx


def run(cfg: CADConfig, *args, **kwargs):
    raise NotImplementedError(
        "Phase 4에서 구현: vLLM 파이썬 API 이중 패스 스텝 디코딩. "
        "go/no-go 게이트(Phase 2-3) 통과가 선행 조건이다.")
