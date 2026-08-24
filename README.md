# ThinkConflict

RAG 문서 간 충돌(inter-context conflict)에서 완화 기법이 올린 정답률이 **진짜 대조 추론에서 온 것인지 경로별로 회계 감사(audit)** 한다 — 추론 모델의 사고→답변 과정을 인지·해소·표출 3단계 전환 행렬로 분해·귀속하는 진단 프레임워크.

## 연구 질문 (RQ)

- **RQ1 (진단 및 불일치 위치):** 추론 모델은 문맥 간 충돌에서 사고와 답변의 자기일관성을 유지하는가? 불일치는 인지→판정→표출 중 어느 단계에서 발생하는가?
- **RQ2 (완화 기법 해부):** 완화 기법(CAD, CD2, Recency/Authority, Reflection)의 EM 상승분은 진짜 대조 논리에서 오는가, 아니면 Shortcut·Discordant Hit·Blind-Hit 경로에서 오는가?
- **RQ3 (충돌 고유성):** 관측된 불일치(AIR)와 특이 경로는 충돌 고유 실패인가, 난이도·문서 수의 부수 효과인가? (충돌 vs 비충돌 대조군)
- **RQ4 (인과 규명):** 사고 결론은 최종 답변을 인과적으로 구동하는가? (truncation·resampling 개입)

연구 계획: [`docs/paper/ThinkConflict_연구보고.md`](docs/paper/ThinkConflict_연구보고.md) · 실험 규약(사전등록): [`docs/experiments/2026-07-10_실험계획_사전등록.md`](docs/experiments/2026-07-10_실험계획_사전등록.md)

## 구조

```
docs/            experiments/ 날짜 접두어(YYYY-MM-DD_실험계획|실험결과_이름)로 페어링된 실험 타임라인 · paper/ 논문 관련(연구보고 md/PPT·학사 양식)
data/1_raw/        원본 데이터셋 (git 미포함 — download.sh로 재현)
data/            raw / review / processed 세 단계, 각 단계 안에 데이터셋별 폴더
  raw/           원본 (git 미포함 — download.sh + checksums.lock으로 재현)
  review/        작업용 CSV — 사람이 검토·수정하는 중간 산출물 (커밋)
  processed/     최종 JSONL — 실험이 읽는 유일한 입력 (커밋, 유형별 파일)
preprocessing/   공통 스키마·CSV 계층 + 데이터셋별 전처리 + LLM 초벌
serving/         3모델 vLLM 서빙 스크립트 + 공통 생성 클라이언트
diagnosis/       트레이스 파서 · L1/L2/FA 라벨러 · 채점기 · 지표 산출기
experiments/     exp1 완화 회계(RQ1·2) · exp2 충돌 고유성(RQ3) · exp3 인과 개입(RQ4)
results/         실행 산출물 (raw 생성물은 git 미포함, 집계만 커밋)
analysis/        집계·그림·표 생성
tests/           진단 파이프라인 회귀 테스트
```

## 시작하기

```bash
pip install -r requirements.txt
pytest tests/                        # 진단 파이프라인 회귀 테스트 (34건)

bash data/1_raw/download.sh            # DRAGged · QACC · RAMDocs 원 출처 다운로드 + 체크섬 고정
python -m preprocessing.ramdocs_prep # 공통 스키마 변환 (LLM 불필요 — Phase 1-1)
python -m preprocessing.dragged_prep draft   # → data/2_review/dragged/dragged.draft.csv
```

Phase 2 이후 (GPU 필요):

```bash
bash serving/launch_qwen.sh &                                       # 모델 서빙
python -m serving.client --data data/3_processed/dragged/dragged_temporal.jsonl \
    --model qwen --env standard --out results/raw/qwen_standard_dragged.jsonl
python -m diagnosis.trace_parser results/raw/*.jsonl                # 파싱 실패율 점검
python -m diagnosis.run_labeling --generations results/raw/qwen_standard_dragged.jsonl \
    --data data/3_processed/dragged/dragged_temporal.jsonl --out results/labels/qwen_temporal.jsonl
python -m experiments.exp2_specificity.regime_control --gate \
    --thinking ... --masked ...                                     # go/no-go 게이트
python -m analysis.aggregate                                        # 집계 → 즉시 커밋
```

## 원칙 (요약)

- 데이터셋은 **풀링하지 않고 분리 보고**, 유효 분모 **N < 20 셀은 비교 주장 금지**.
- 라벨 규약·게이트 기준은 해당 데이터 생성 **전에** `docs/experiments/2026-07-10_실험계획_사전등록.md`(사전등록)으로 커밋 (개정 시 이력 보존).
- 일회성 작업 문서(인수인계 등)는 작업 종료 시 **삭제** — 기록은 git 히스토리로 남는다(`git log --diff-filter=D --summary -- docs/`). 실행 기록은 docs/가 아니라 `results/RUNLOG.md`.
- 커밋은 한 줄, co-author 없음, 푸시는 명시 요청 시만.
