#!/usr/bin/env bash
# Mistral-Small-3.2-24B 서빙 — 판정자 전용 (실험계획서 §3.4: 제3 계열 고정 오픈 판정자).
# 생성(대상) 모델이 아니므로 비양자화 원칙의 적용 대상이 아니며, 네이티브 bf16으로 올린다.
set -euo pipefail
MODEL_ID="${MISTRAL_MODEL_ID:-mistralai/Mistral-Small-3.2-24B-Instruct-2506}"
PORT="${MISTRAL_PORT:-8004}"
exec vllm serve "$MODEL_ID" \
  --tokenizer-mode mistral --config-format mistral --load-format mistral \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --seed 0
