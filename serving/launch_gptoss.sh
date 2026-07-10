#!/usr/bin/env bash
# gpt-oss-20b vLLM 서빙 (교차 계열·MoE 검증, 계획서 §3.3.1).
# 사고는 <think>가 아니라 Harmony 포맷 analysis 채널로 출력됨 —
# 파싱은 diagnosis/trace_parser.py의 Harmony 파서가 담당하고,
# 파싱 규약 상이는 계열 간 비교의 교란 변인으로 분리 보고한다(§5).
# reasoning effort 조절은 참고용 보조 신호로만 사용(§3.3.3(b)) — client.py --effort.
set -euo pipefail

MODEL_ID="${GPTOSS_MODEL_ID:-openai/gpt-oss-20b}"
PORT="${GPTOSS_PORT:-8003}"

exec vllm serve "$MODEL_ID" \
  --dtype bfloat16 \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --tensor-parallel-size "${TP:-1}" \
  --seed 0
