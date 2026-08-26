# 실행 산출물

- `raw/` — 생성 원문 JSONL. **git 미포함** (`.gitignore`). `serving/client.py` 산출.
- `labels/` — 3단계 라벨 JSONL. `diagnosis/run_labeling.py` 산출.
- `aggregate/` — 집계 표·전환 행렬 JSON. **생성 즉시 커밋**해 지표 계산 시점을 남긴다
  (사전등록 §5). `analysis/aggregate.py` 산출.

집계에는 항상 분모 N과 부트스트랩 95% CI가 병기되며, 유효 분모 N < 20인 셀은
`underpowered`로 표시된다 — 그 셀 위에 환경·모델 간 비교 주장을 세우지 않는다
(사전등록 §2.1).
