# ConflictRAG: Detecting and Resolving Knowledge Conflicts in Retrieval Augmented Generation

- 저자/발표: Zhengzhou Univ. / Taiyuan Univ. of Tech. / Zhejiang Univ., IEEE 컨퍼런스 포맷 6쪽(투고 중으로 보임)
- 원문: `literature/papers/ConflictRAG; .../main.pdf`

## 1. 핵심 요약

RAG가 암묵적으로 가정하는 검색 문서 간 상호 일관성이 실제로는 자주 깨진다는 문제를 다룬다. 답변 생성 이전에 충돌을 탐지 → 유형 분류 → 유형별 해소 → 충돌 인지 생성하는 4단계 파이프라인. 핵심 구성요소는 (1) 임베딩 MLP + 선택적 LLM 정제의 2단계 충돌 탐지기, (2) Entropy-TOPSIS 기반 출처 신뢰도 평가, (3) CARS 복합 진단 지표. 3개 벤치마크에서 정답성 5.3~6.1%p 향상, 탐지 F1 88.7%, API 비용 62% 절감을 보고.

## 2. 방법론

### 문제 정식화
a = Generate(q, D, Resolve(q, D, Detect(q, D))). 검색은 BM25 + Contriever 하이브리드, K=5 → 쿼리당 C(5,2)=10쌍.

### 2단계 충돌 탐지
- Stage 1(임베딩 MLP): frozen all-MiniLM-L6-v2로 인코딩, InferSent식 상호작용 피처 [e_i; e_j; |e_i−e_j|; e_i⊙e_j] (1536차원). 공유 피처 위 이진 탐지 head + 4-way 유형 분류 head(no-conflict/factual/temporal/opinion). CPU-only 배포 가능성이 설계 이유.
- Stage 2(LLM 정제): confidence < τ_c=0.7인 쌍만 GPT-4o-mini로 라우팅. 전체 쌍의 27%만 LLM 호출.
- 학습 데이터: ConflictQA 750 인스턴스에서 재페어링한 3,000 문서 쌍.
- 파라메트릭-문맥 충돌 탐지(직교 모듈): closed-book 답 vs open-book 답을 구조화 비교, 불일치 시 검색 근거 우선. 100샘플 정확도 81%.

### 유형 적응형 해소
- Factual → Entropy-TOPSIS: LLM이 5개 기준(authority, recency, relevance, specificity, consistency)을 채점, 엔트로피 가중치로 결합해 이상해 근접도로 랭킹.
- Temporal: recency 우선 + 시간적 변화 명시.
- Opinion: 다관점 종합 + 출처 귀속.

### 생성
해소된 컨텍스트 + 충돌 집합을 전달, 출력은 최신뢰 출처 응답 + 충돌 주석 + 출처 귀속 + 신뢰도 한정자.

### 데이터/베이스라인/지표
- 데이터: ConflictQA(2,000), NQ-Conflict(자체 구축, GPT-4o 충돌 주입 500샘플, 20%만 인간 검증), AmbigQA(1,000)
- 베이스라인: Standard RAG, RAG+Reranking, Self-RAG, CRAG, NLI-Filter, CoT Detection
- 지표: Answer Correctness(GPT-4o judge), token F1, 탐지 F1, Resolution/Transparency(LLM 1~5점), CARS = 0.35·AC + 0.25·CDA + 0.25·RA + 0.15·SF

## 3. 주요 결과

- Correctness: ConflictQA 68.9(+5.8), NQ-Conflict 71.4(+6.1), AmbigQA 65.8(+5.3).
- Self-RAG가 Standard RAG보다 낮음(reflection 필터가 모순 근거를 과도 제거).
- 탐지: 이진 F1 88.7, 유형 분류 74.3%(opinion .685 최저). 재학습 없는 AmbigQA 전이 시 F1 83.4.
- 효율: 2단계가 LLM-only 대비 2.77배 speedup, 62% 비용 절감(90.8% 정확도).
- Ablation: w/o Detection −16.6%p, w/o Resolution −13.2, w/o Classification −7.9, w/o Annotation −1.3(단 Transparency 4.35→1.42).
- Entropy-TOPSIS 선택 정확도 82.7%(LLM 직접 선택 78.3 대비). authority(.312) 가중치 최대.

## 4. 한계점

### (a) 저자 명시 한계
1. LLM-as-judge의 잔여 포맷 편향(영향 ≤2.5%p로 bound 주장)
2. NQ-Conflict는 20%만 인간 검증
3. CARS는 충돌 인지 시스템에 유리하게 설계된 진단 지표임을 명시
4. future work: 도메인 특화 인코더 파인튜닝, 다국어

### (b) 암묵적 한계 (비판적 분석)

**실험 설계**
- **CARS의 순환성**: 가중치의 65%(CDA/RA/SF)가 명시적 충돌 모듈 보유 시스템만 점수를 얻는 항목. "우리 방법의 존재 여부"를 지표로 측정한 셈.
- Resolution/Transparency 판정자(GPT-4o)와 생성 모델(GPT-4o-mini)이 동일 계열: self-preference 잔존.
- CoT Detection 대비 end-to-end 비용/지연 비교 부재: +5~6%p가 방법론 덕인지 연산 예산 덕인지 분리 안 됨.
- w/o Detection −16.6%p는 모듈 기여도가 아니라 파이프라인 유무 비교.
- K=5 고정: 쌍 수가 O(K²)로 증가하는데 K=10, 20에서의 정확도/비용 곡선 없음.

**데이터 현실성**
- 학습 쌍 3,000개가 750 인스턴스의 재페어링이라 통계적으로 비독립, 쿼리 단위 분리 불명확(leakage 위험).
- 파라메트릭-문맥 라벨을 pairwise 라벨로 변환한 것은 라벨 semantics 재해석: 서로 다른 답 지지가 실제 모순임을 보장하지 않음.
- NQ-Conflict가 GPT-4o 주입 합성이라 탐지기가 주입 문체 아티팩트를 학습했을 위험. temporal F1 최고는 날짜 표층 신호 때문일 개연성.
- AmbigQA는 충돌이 아니라 질문 모호성: 개념 혼동.

**충돌 유형 커버리지**
- factual/temporal/opinion 3종은 거친 분류: 조건부 충돌(관할/단위/모집단), 부분 정보, 문서 내 자기모순, multi-hop 함의 충돌 누락.
- **pairwise만 다룸**: 3개 이상 문서의 비이행적(non-transitive) 충돌 집합을 전역적으로 병합하는 절차 부재.
- 쌍 단위 단일 라벨이라 factual+temporal 동시 충돌 미처리.

**확장성/신뢰도 평가**
- TOPSIS의 5개 기준 점수를 LLM이 매김: authority를 모델 사전 편향으로 결정. 소수 정답 출처(신생 기관, 최신 정정)를 체계적으로 불리하게 만듦.
- 엔트로피 가중치는 후보 집합 내 분산에만 의존: 문서 2~3개 소집합에서 극히 불안정.
- recency 우선(temporal) 정책의 위험: 최신 문서가 항상 옳지 않음(반례 분석 없음).
- τ_c=0.7이 ConflictQA 분포에서 튜닝됨: 도메인 이동 시 라우팅 비율 유지 보장 없음.
- frozen MiniLM의 256 토큰 한계: 긴 문서는 앞부분만으로 판정.
- 코드/벤치마크 미공개 상태로 재현 불가.

## 5. 후속 연구 여지

1. n-ary/비이행적 충돌의 전역 해소: pairwise 판정을 signed graph로 보고 correlation clustering이나 argumentation framework로 일관 집합 추출
2. 충돌 온톨로지 확장 + 다중 라벨화: 조건부 충돌, 부분 정보, 자기모순, multi-hop 함의 충돌과 대응 해소 전략
3. 외부 근거 기반 출처 신뢰도: citation graph, 도메인 PageRank, 정정 이력으로 LLM 추정 authority 대체. LLM 사전 편향 진단 벤치마크
4. 시간 추론 정교화: temporal validity interval, 철회/개정 관계 모델링, "최신이지만 틀린" 적대적 벤치마크
5. 자연 발생 충돌 벤치마크: 위키 revision, 뉴스 정정, 가이드라인 개정 기반, 합성 학습 → 자연 평가 전이 실험
6. 비용-정확도 파레토: 학습된 라우팅 정책(cascade/conformal), K 스케일링에서 sub-quadratic 쌍 프루닝
7. 충돌 인지 지표 탈편향: 충돌 시 정답 선택률, calibration, abstention 적절성, 사용자 하류 의사결정 기반 인간 연구
8. contradiction-aware retrieval encoder, conflict-aware retrieval(검색 단계에서 충돌 후보를 다양성 있게 회수)
9. 장문서 span-level 충돌 국소화, 다국어/도메인 특화
10. 충돌 표출 방식의 HCI/calibration 연구(annotation의 Transparency 효과에서 출발)
