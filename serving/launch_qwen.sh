#!/usr/bin/env bash
# Qwen3.6-27B vLLM 서빙 (주력 분석 모델, 계획서 §3.3.1).
# 비양자화 bf16 고정 — 로짓·궤적 왜곡 방지. thinking on/off는 서버가 아니라
# 요청 시점에 chat_template_kwargs={"enable_thinking": false}로 토글한다
# (serving/client.py --no-thinking; Qwen3의 /think 소프트 스위치는 3.6 미지원 — §3.3.3(b)).
set -euo pipefail

MODEL_ID="${QWEN_MODEL_ID:-Qwen/Qwen3.6-27B}"
PORT="${QWEN_PORT:-8001}"

exec vllm serve "$MODEL_ID" \
  --dtype bfloat16 \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --tensor-parallel-size "${TP:-1}" \
  --seed 0
