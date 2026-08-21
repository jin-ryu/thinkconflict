#!/usr/bin/env bash
# Qwen3.6-27B vLLM 서빙 (주력 분석 모델, 계획서 §3.3.1).
# 비양자화 bf16 고정 — 로짓·궤적 왜곡 방지. thinking on/off는 서버가 아니라
# 요청 시점에 chat_template_kwargs={"enable_thinking": false}로 토글한다
# (serving/client.py --no-thinking; Qwen3의 /think 소프트 스위치는 3.6 미지원 — §3.3.3(b)).
set -euo pipefail

MODEL_ID="${QWEN_MODEL_ID:-Qwen/Qwen3.6-27B}"
PORT="${QWEN_PORT:-8001}"
# Qwen3.6은 하이브리드(Mamba+어텐션)라 디코드 시퀀스마다 Mamba 캐시 블록을 하나씩 쓴다.
# H100 80GB·bf16에서 확보되는 블록이 334개뿐이라 vLLM 기본값 1024로는 CUDA 그래프
# 캡처가 실패한다("max_num_seqs exceeds available Mamba cache blocks"). 서빙 동시성
# 상한일 뿐 디코딩 설정이 아니므로 사전등록과 무관하다.
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"

exec vllm serve "$MODEL_ID" \
  --dtype bfloat16 \
  --port "$PORT" \
  --max-model-len "${MAX_LEN:-32768}" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --tensor-parallel-size "${TP:-1}" \
  --seed 0
