# Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

- 저자/발표: Asai et al. (UW/AI2/IBM), ICLR 2024
- 원문: `literature/papers/Self-RAG; .../iclr2024_conference.pdf`

## 1. 핵심 요약

LM이 언제 검색할지, 검색 문서가 유용한지, 자기 생성물이 근거에 의해 뒷받침되는지를 reflection token이라는 특수 토큰으로 스스로 예측하도록 end-to-end 학습시키는 프레임워크. 고정 개수 문서를 무조건 넣는 기존 RAG의 문제를 on-demand 검색 + 세그먼트 단위 자기비평 + 비평 토큰 기반 재랭킹으로 해결한다. Llama2 7B/13B 기반으로 ChatGPT 등을 6개 태스크에서 능가, 특히 사실성과 citation 정확도에서 큰 이득.

## 2. 방법론

### Reflection tokens
| 토큰 | 입력 | 출력값 | 의미 |
|---|---|---|---|
| Retrieve | x 또는 (x, y) | {yes, no, continue} | 검색 필요 여부 |
| IsRel | (x, d) | {relevant, irrelevant} | 문서 유용성 |
| IsSup | (x, d, y) | {fully, partially, **no support / contradictory**} | y가 d에 entail되는 정도 |
| IsUse | (x, y) | {5..1} | 사실성과 독립적인 perceived utility |

### 학습 (2단계, 오프라인 critic)
1. **Critic C**: GPT-4 few-shot으로 reflection token 라벨 생성(4만여 개), Llama2-7B를 조건부 LM objective로 학습. 정확도: Retrieve 93.8 / IsSup 93.5 / IsRel 80.2 / IsUse 73.5.
2. **Generator M**: critic으로 오프라인 증강한 코퍼스(145,619개, Open-Instruct + KILT 계열)에 표준 next-token objective. 검색 passage는 loss 마스킹. Retriever는 Contriever-MS MARCO 고정.

### 추론
- 적응형 검색: p(Retrieve=Yes) 정규화 확률 > δ이면 검색.
- Tree decoding: K개 문서를 병렬로 각각 붙여 K개 continuation 생성, 세그먼트 빔서치(B=2).
  - f(y_t, d, Critique) = p(y_t | x, d, y_<t) + S(Critique)
  - S = Σ_G w^G · s^G (IsRel 1.0, IsSup 1.0, IsUse 0.5). test-time에 재학습 없이 조정 가능.
- Hard constraint: IsSup=No support인 continuation 필터링 옵션.

### 평가
PopQA, TriviaQA, PubHealth, ARC-Challenge, Bio(FactScore), ASQA(str-em, MAUVE, citation precision/recall).

## 3. 주요 결과

- 전 태스크에서 비독점 모델 상회, citation precision은 ChatGPT(65.1)를 7B(66.9)가 능가.
- Ablation: critic 학습과 IsSup 기반 재랭킹이 핵심 기여.
- IsSup 가중치 조절로 citation precision↑ / MAUVE↓의 trade-off를 test-time에 제어 가능.
- 제공 근거 밖 답변 비율 2%(Alpaca-30B 20%, Llama2-chat-13B 18% 대비).

## 4. 한계점

### (a) 저자 명시 한계
1. 여전히 citation에 의해 완전히 뒷받침되지 않는 출력 생성 가능(환각 미제거).
2. IsUse 정확도 73.5, 인간 일치도 80%로 낮음.
3. IsSup은 attribution 개념이며 사실 여부와 무관.
4. 학습 데이터 150k 제한, scaling curve 상승 중.
5. Retriever 고정. joint training은 future work.

### (b) 지식 충돌 관점의 암묵적 한계 (비판적 분석)
- **B1. IsSup 라벨이 충돌을 지운다**: "no support(침묵)"와 "contradictory(반박)"가 한 클래스로 병합. NLI로 치면 neutral과 contradiction을 묶은 것으로, 충돌 연구의 핵심 신호가 설계 단계에서 소실.
- **B2. 문서 간 충돌을 볼 수 없는 구조**: IsRel/IsSup 모두 단일 문서 d에만 조건화, K개 문서는 병렬 독립 처리. 두 문서가 같은 컨텍스트에 동시에 등장하는 순간이 없어 모순을 원리적으로 관측 불가. 충돌 "해결"은 사실상 승자독식 argmax이며 반대 근거는 조용히 버려진다.
- **B3. 승자가 신뢰·최신·다수가 아니다**: 스코어에 출처 신뢰도, 발행 시점, 문서 간 합의가 전혀 없다. p(y_t | x, d) 항 때문에 파라메트릭 prior와 일치하는 문서가 유리(확증 편향). 날조 문서일수록 자기 주장을 완벽히 지지하므로 IsSup은 poisoning의 증폭 채널.
- **B4. context-memory 충돌 표현 토큰 부재**: "문서가 낡았고 내 지식이 맞다"를 표현할 수단이 없다. 근거 밖 답변 2%는 과잉 grounding의 다른 얼굴.
- **B5. Retrieve=continue의 앵커링**: 첫 세그먼트 선택 문서가 이후로 재사용되어 초기 오류가 문단 전체로 전파.
- **B6. 세그먼트 간 일관성 제약 부재**: 문장 1이 문서 A를, 문장 2가 A와 모순되는 문서 B를 근거로 골라도 각각 Fully Supported를 받으며 전체 출력은 자기모순 가능.
- **B7. 판정 단위가 문장**: temporal/scope/정의 차이 같은 담화 수준 충돌 미포착.
- **B8. critic 감독 신호의 취약성**: GPT-4 single-pass 라벨 distill로 GPT-4의 충돌 편향 계승. 학습 코퍼스(위키/KILT)는 대체로 conflict-free라 모순이 흔한 웹 분포로의 전이 미검증.
- **B9. 평가에 충돌 축 부재**: citation precision이 높으면서 반대 근거를 은폐하는 cherry-picking 모델이 만점 가능. ASQA의 모호성(여러 정답 모두 참)과 진짜 충돌(하나만 참)을 구분하지 않음.
- **B10. 실용 제약**: K×beam 병렬 비용, w^G·δ가 태스크별 수동 조정. 충돌 상황에서 이 가중치가 곧 "누구를 믿을지" 정책이 됨.

## 5. 후속 연구 여지

1. 충돌 전용 reflection token: IsSup을 {Refuted, Neutral}로 분해, IsConflict/Consensus 토큰 추가. vocabulary 확장 + critic 라벨링만 바꾸면 되는 최소 변경 확장.
2. pairwise/set-wise critic: 문서 집합 조건화, NLI 충돌 그래프 + 집계 디코딩. O(K²)를 클러스터링으로 근사.
3. 출처 속성 조건부 비평: 발행일·권위 메타데이터 기반 IsRecent/IsAuthoritative 토큰. temporal 충돌 실증(논문 내 Rory Tapner 사례가 출발점).
4. 충돌 명시(disclosure) 생성과 지표: conflict recall, cherry-picking rate, 충돌 상황 calibration.
5. context-memory 충돌 토큰: RejectEvidence / TrustSource ∈ {context, memory, unresolved}. counterfactual 코퍼스 벤치마크.
6. corpus poisoning 공격 연구: 자기지지적 날조 문서 1개로 빔서치 하이재킹 측정.
7. 전역 일관성 디코딩: 앞 세그먼트와의 NLI contradiction 페널티 추가.
8. 충돌 학습 데이터 합성: 모순 문서 쌍 자동 생성으로 critic 학습, GPT-4 distill 편향 완화.
9. 모호성 vs 충돌 분류: "여러 정답 모두 참"과 "하나만 참"을 구분하는 토큰/태스크.
10. diverse-stance retrieval과 critic의 공동 최적화.
