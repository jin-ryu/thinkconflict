# Retrieval-Augmented Generation with Conflicting Evidence (RAMDocs / MADAM-RAG)

- 저자/발표: Han Wang, Archiki Prasad, Elias Stengel-Eskin, Mohit Bansal (UNC Chapel Hill), COLM 2025
- 코드/데이터: https://github.com/HanNight/RAMDocs
- 원문: `literature/papers/Retrieval-Augmented Generation with Conflicting Evidence/colm2025_conference.pdf`

## 1. 핵심 요약

기존 연구가 모호성, 오정보, 노이즈를 각각 따로 다룬 것과 달리, 셋이 동시에 존재하는 현실적 상황을 상정한다. (i) 하나의 질의에 여러 유효 답변 + 오정보 + 무관 문서 + 근거 문서 수 불균형이 함께 든 벤치마크 RAMDocs(500 질의), (ii) 문서 1개당 에이전트 1개를 할당해 다라운드 토론 후 aggregator가 종합하는 MADAM-RAG를 제안. AmbigDocs 최대 +11.40%, FaithEval 최대 +15.80% 개선하지만 RAMDocs 최고 성능이 34.40 EM에 그쳐 동시 처리 문제가 미해결임을 보인다.

## 2. 방법론

### RAMDocs 데이터 구성 (AmbigDocs 기반, 4단계)
1. 모호성: 모호 질의의 disambiguated answer 중 1~3개 무작위 샘플링(부분 검색 상황 포함).
2. 근거 수 불균형: Brave Search API로 웹 문서 수집, 100단어 청크화, 정답 포함 청크만 채택. 정답당 근거 1~3개로 무작위 변동(빈도 편향 유도).
3. 오정보: 정답 엔티티를 그럴듯한 오답으로 치환(entity-swap)한 문서 0~2개.
4. 노이즈: 무관/저품질 문서 0~2개.

통계: 질의당 문서 평균 5.53개(정답 지지 3.84 / 오답 지지 0.61 / 노이즈 1.08), 유효 답변 평균 2.20개.

### MADAM-RAG
- 독립 에이전트: 문서마다 에이전트 1개, r_i = L_i(q, d_i). 의도: lost-in-the-middle 방지, 문서 빈도 편향 차단.
- Aggregator: 라운드별 에이전트 출력을 종합(순서 셔플로 position bias 완화). 복수 유효 답변은 보존, 오정보 기원 주장은 플래그.
- 다라운드 토론: 이전 라운드 요약을 받아 방어/수정. 전원 답 유지 시 early stopping, 최대 T=3.

### 평가
- 데이터: FaithEval inconsistent(1000), AmbigDocs(1000), RAMDocs(500)
- 모델: Llama3.3-70B, Qwen2.5-72B, GPT-4o-mini (+ Self-RAG-Llama2-13B)
- 지표: 집합 단위 all-or-nothing EM(모든 gold answer 포함 + 오정보 지지 답변 미포함일 때만 정답)
- 베이스라인: No RAG, Concatenated-prompt, Self-reflection, Self-RAG, Speculative RAG, Astute RAG

## 3. 주요 결과

- MADAM-RAG가 전 조합에서 최고(예: Llama3.3-70B에서 43.10 / 58.20 / 34.40).
- RAMDocs는 모든 방법이 최저: 여러 충돌 요인의 동시 처리가 어렵다는 실증.
- 근거 불균형 실험: 베이스라인은 다수 지지 답으로 쏠려 최대 8% 하락, MADAM-RAG는 완화.
- 오정보 1→3개 증가 시 Concatenated·Astute RAG는 46% 하락, MADAM-RAG도 하락하되 최고 유지.
- Aggregator는 precision을 올리고 recall을 소폭 낮추는 보수적 전략.
- 비용: 평균 입력 3186 / 출력 1547 토큰(prompt-based 822/126의 약 4배/12배).

## 4. 한계점

### (a) 저자 명시 한계
별도 Limitations 섹션 없음. 본문에 산재: RAMDocs 34.40 EM은 미해결 과제, 오정보 증가 시 성능 하락, aggregator의 precision-recall trade-off, Speculative RAG 재현 불완전, 멀티에이전트 연산 오버헤드.

### (b) 암묵적 한계 (비판적 분석)

**데이터 현실성**
- 오정보가 entity-swap 단일 전략: 부분적 진실, 프레이밍, 통계 오용, 인용 위조, 낡은 사실의 재유통 등 실제 오정보 형태 미커버. 탐지 난이도가 표면적 엔티티 불일치로 환원.
- 출처 메타데이터(도메인, 발행일, URL) 전무: 권위·최신성·교차검증이라는 인간의 충돌 해소 신호를 쓸 수도, 평가할 수도 없음. 시간적 충돌이 벤치마크에서 완전히 배제됨.
- 오정보 0~2개는 실제 웹의 오염(동일 오정보의 대량 복제) 대비 과소.
- 노이즈 문서 생성 절차가 불명확해 재현성 낮음.

**충돌 유형 커버리지**
- 모호성이 엔티티 동명이인 한 종류(AmbigDocs 상속). 사건/술어/시제 모호성, 단위 차이, 의견 불일치, unanswerable 부재.
- 정답이 모두 짧은 엔티티/연도 문자열: long-form 충돌 종합 미측정.
- 에이전트 1개 = 문서 1개 설계는 문서 결합 근거(multi-hop)를 구조적으로 불가능하게 만든다.
- 파라메트릭 vs 문맥 충돌 축은 명시적으로 설계되어 있지 않음.

**평가 설계**
- all-or-nothing EM: "3개 중 2개 맞춤"과 "0개"가 동일 점수. 부분 크레딧 하 순위 유지 여부 불명.
- 어떤 문서에도 없는 순수 환각 답변이 페널티를 안 받을 수 있는 지표 허점.
- 분산/신뢰구간/시드 반복 미보고(500 질의 규모에서 1~2점 차는 무의미할 수 있음).
- shot 수 불일치(베이스라인 1-shot vs 에이전트 zero-shot vs aggregator few-shot).
- 동일 토큰 예산 self-consistency 베이스라인 부재: 개선분이 토론 구조 덕인지 추가 연산 덕인지 분리 불가.
- 에이전트와 aggregator가 동일 백본이라 오류 상관. 이종 백본 ablation 없음.
- 토론 트랜스크립트 분석 전무: 에이전트의 다수 의견 동조(sycophancy) 통계조차 없음.

**확장성**
- 비용 O(n·T) LLM 호출. 실험 평균 5.53 문서인데 실제 딥리서치는 수십~수백 문서. n 스케일링 실험 없음. 규모가 커지면 aggregator에서 long-context 병목과 position bias가 재발.
- 검색기가 파이프라인에 없는 오라클에 가까운 설정.

## 5. 후속 연구 여지

1. 출처 메타데이터·시간축을 갖춘 충돌 벤치마크: 최신성 vs 다수결 vs 권위가 충돌하는 케이스 명시 설계
2. 오정보 생성 다양화 + 적대적 강화(토론 오염 프롬프트 인젝션 포함)
3. 동조 동역학 분석과 완화: 라운드별 답변 변경 로그, 소수 의견 보존 메커니즘(신뢰도 가중, devil's advocate, 이종 백본)
4. 연산 예산 통제 비교: 동일 토큰 예산에서 토론 vs self-consistency vs long-context 단일 추론
5. 확장 가능한 아키텍처: 계층적 aggregation, 에이전트 가지치기, 비용-정확도 파레토
6. 부분 크레딧·calibration 중심 평가: 집합 F1, attribution 정확도, abstention 품질
7. long-form 충돌 종합 생성(여러 관점 인용 서술 + 오정보 명시 반박)
8. 학습 기반 접근: 충돌 유형 판별 후 분기 행동을 SFT/RL로 학습
9. 문서 간 결합 근거 하의 충돌: 에이전트 간 근거 공유 프로토콜과 빈도 편향의 트레이드오프
10. 검색기 포함 end-to-end: 출처 다양성 정책이 정교한 토론보다 저렴하게 효과적인지 검증
