#!/usr/bin/env bash
# Olmo-3.1-32B-Think vLLM 서빙 (완전 개방형 대조군, 계획서 §3.3.1).
# 레짐 통제(§3.3.3(b))는 동일 베이스의 matched-sibling인 Olmo-3.1-32B-Instruct를
# OLMO_MODEL_ID로 바꿔 병행한다 (post-training 파이프라인이 달라 '순수 토글' 아님 — 명시).
set -euo pipefail

MODEL_ID="${OLMO_MODEL_ID:-allenai/Olmo-3.1-32B-Think}"
PORT="${OLMO_PORT:-8002}"

exec vllm serve "$MODEL_ID" \
  --dtype bfloat16 \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --tensor-parallel-size "${TP:-1}" \
  --seed 0
