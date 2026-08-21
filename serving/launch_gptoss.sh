#!/usr/bin/env bash
# gpt-oss-20b vLLM 서빙 (교차 계열·MoE 검증, 계획서 §3.3.1).
# 사고는 <think>가 아니라 Harmony 포맷 analysis 채널로 출력됨 —
# 파싱은 diagnosis/trace_parser.py의 Harmony 파서가 담당하고,
# 파싱 규약 상이는 계열 간 비교의 교란 변인으로 분리 보고한다(§5).
# reasoning effort 조절은 참고용 보조 신호로만 사용(§3.3.3(b)) — client.py --effort.
set -euo pipefail

MODEL_ID="${GPTOSS_MODEL_ID:-openai/gpt-oss-20b}"
PORT="${GPTOSS_PORT:-8003}"
# 기본은 bf16 비양자화 — 이 모델을 **생성 모델**로 쓸 때의 원칙(로짓·궤적 왜곡 방지)이다.
# 다만 gpt-oss 배포 체크포인트는 원래 MXFP4라, **판정자로만** 쓰는 실행에서는
# DTYPE=auto로 네이티브 정밀도를 그대로 올린다 (판정자는 텍스트만 읽으므로 허용 —
# 부록 A(a), 파일럿 인수인계 §3 B안). 생성 실행에서는 이 값을 건드리지 않는다.
DTYPE="${DTYPE:-bfloat16}"

exec vllm serve "$MODEL_ID" \
  --dtype "$DTYPE" \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --tensor-parallel-size "${TP:-1}" \
  --seed 0
