#!/usr/bin/env bash
# Gemma-3-27B vLLM 서빙 (교차 계열 일반화 대조, 연구보고 PPT 19p).
# 추론 채널이 없는 비-thinking 모델 — 진단된 현상이 계열을 넘어 재현되는지,
# 그리고 AIR·Shortcut 같은 실패 양식이 사고 채널 고유인지 가르는 기준이 된다.
# thinking 토글이 없으므로 RQ3(b) 레짐 토글에는 참여하지 않는다 (PPT 23p).
set -euo pipefail

MODEL_ID="${GEMMA_MODEL_ID:-google/gemma-3-27b-it}"
PORT="${GEMMA_PORT:-8002}"

exec vllm serve "$MODEL_ID" \
  --dtype bfloat16 \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --tensor-parallel-size "${TP:-1}" \
  --seed 0
