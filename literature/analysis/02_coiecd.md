# Discerning and Resolving Knowledge Conflicts through Adaptive Decoding with Contextual Information-Entropy Constraint (COIECD)

- 저자/발표: Yuan et al. (CAS/UCAS/BAAI), ACL 2024
- 코드: https://github.com/Stacy027/COIECD
- 원문: `literature/papers/Discerning and Resolving Knowledge Conflicts .../acl_latex.pdf`

## 1. 핵심 요약

파라미터 지식과 컨텍스트 지식이 충돌할 때, 기존 디코딩 기법(CD, CAD)은 "모든 데이터가 충돌한다"는 가정 위에 설계되어 비충돌 데이터에서 성능이 크게 하락한다. COIECD는 토큰 단위로 충돌 여부를 먼저 판별한 뒤 충돌/비충돌 토큰에 서로 다른 디코딩 전략을 적용하는 적응적 디코딩 기법이다. 판별 기준은 Stable Entropy Hypothesis와 Locally Typical Set에 기반한 정보량-엔트로피 시프트의 경계 위반 여부이며, 무학습(training-free)이다.

## 2. 방법론

### 핵심 가정 (Assumption C.1)
컨텍스트 c가 파라미터 지식 K에 포함되어 충돌이 없다면, c는 모델 자신의 자연스러운 생성일 수 있다. 따라서 비충돌 토큰은 안정 엔트로피 밴드를 따르고, 충돌 토큰은 이를 위반한다.

### 정보량-엔트로피 시프트 제약
- H₁(y_t) = H(y_t | x, y_<t): 컨텍스트 없이(파라미터 지식만)
- H₂(y_t) = H(y_t | x, c, y_<t): 컨텍스트 포함
- I(y_t) = −log p(y_t | x, c, y_<t)
- Proposition 3.1: 비충돌 토큰이면 | I(y_t) − H₁(y_t) | < γ (γ = β + ε, 삼각부등식으로 유도)
- 실제 구현은 p_δ(y_t) = softmax(I − H₁)에 상한 u = λ·max p_δ, 하한 l = (1/λ)·min p_δ를 두고, 경계 위반 영역 안에 있으면 충돌 토큰으로 판정. 하한 위반 토큰이 하나뿐이면 하한을 0으로 죽이는 조건부 트릭 사용. λ=0.25 고정.

### 적응적 디코딩
대조 항 g(y_t) = log p₂ − log p₁에 대해:
- 충돌 토큰: log π = log p₁ + α·g (실질적으로 컨텍스트 강화)
- 비충돌 토큰: log π = log p₂ + α·g
- α=1일 때 CAD는 "항상 충돌"로 가정한 COIECD의 특수 케이스(Appendix F).

### 실험 설정
- 모델: LLaMA2-7B/13B, OPT-6.7B/13B, FLAN-T5-3B/11B (최대 13B, 전부 pre-2024)
- 데이터: NQ, SQuAD, StrategyQA(현실적 혼합), Counterfacts(100% 합성 충돌)
- 충돌 라벨: posteriori judgement. 컨텍스트 없이 모델이 맞히면(F1 ≥ 0.5) Non-Conf., 틀리면 Conf.
- 베이스라인: Regular, Self-Consistency, CD, CAD. 지표: EM, F1.

## 3. 주요 결과

- CD/CAD는 Non-Conf.에서 최대 −11.86 EM까지 붕괴. COIECD만 양쪽 모두 안정적(단 COIECD도 Non-Conf.에서 Regular보다 소폭 낮은 경우 다수).
- OPT-6.7B NQ에서 +10.33 EM 등 큰 개선. 단 OPT는 Conf. 비율이 99%에 달하는 극단 레짐.
- 합성 충돌(Counterfacts)과 현실 데이터(NQ)에서 CD/CAD의 곡선 양상이 질적으로 다름: counterfactual 단일 데이터로 디코딩 기법을 검증할 수 없다는 논지.
- Ablation: 하한(lower bound)이 충실성의 핵심 동력. α=0(대조 항 제거) 시 성능 급락: 성능의 상당 부분이 g에서 나오고 엔트로피 제약은 게이팅 역할.

## 4. 한계점

### (a) 저자 명시 한계
1. QA 태스크에만 평가(요약 등 미검증)
2. 연산 비용 2배(p₁, p₂ 두 번의 forward)
3. 엔트로피 스무딩 생략: 개방형 장문 생성에는 부적절할 수 있음

### (b) 암묵적 한계 (비판적 분석)
- **충돌 라벨의 순환성**: Conf./Non-Conf.가 "모델이 틀린 문제"와 사실상 동치다. 진짜 충돌이 아니라 지식 부재(knowledge gap)를 대부분 포착. F1≥0.5 임계값도 임의적이고 민감도 분석 없음.
- **모델 간 비교 불가**: 분할이 모델마다 달라 동일 데이터 비교가 아니다. Conf. 비율이 LLaMA2-13B NQ 76.79% 등 비현실적으로 높음.
- **충돌 판별의 정당성 부족**: Prop 3.1은 "비충돌 → 유계" 한 방향만 증명. 역방향(위반 → 충돌)은 보장 없음. 희귀 고유명사, 문장 시작 토큰, 단순 불확실성에서도 위반 발생 가능. **판별 정확도(precision/recall) 측정 실험이 전혀 없음**: 이 논문의 가장 큰 실증적 공백.
- **이론-구현 간극**: γ, β, ε이 실제 알고리즘에 등장하지 않고 λ 하나로 대체된 휴리스틱.
- **성능 귀속 불명**: "제약 없이 g만"(=CAD) vs "제약+g"의 통제 비교가 불충분.
- **closed/instruction-tuned 모델 적용 불가**: 전체 어휘 분포 필요. GPT-3.5/4에는 미적용. RLHF 모델에서 핵심 가정(Assumption C.1)의 성립 여부 미검증.
- **컨텍스트가 틀린 경우 미처리**: 충돌 감지 시 무조건 컨텍스트 편을 들므로 오염 문서·프롬프트 인젝션 환경에서 오류를 강화하는 방향으로 작동. 안전성 관점에서 치명적이나 논의 없음.
- **토큰 단위 독립 판정**: 충돌은 스팬 수준 의미론적 현상인데 토큰마다 전략이 전환되어 비일관 혼합 답변 가능.
- **지표 협소**: EM/F1만. faithfulness, 환각률, abstention, calibration 미측정. 검색 노이즈 실험의 개선폭(16.80 → 16.84)은 노이즈 수준 이하.
- **확장성**: 2배 forward + 전체 어휘 엔트로피 계산. latency 실측 없음. 장문 컨텍스트에서 KV 캐시 재사용 곤란.

## 5. 후속 연구 여지

1. 충돌 판별기 자체의 벤치마킹: 인간 부여 토큰/스팬 충돌 라벨로 게이팅의 precision/recall/AUC 측정
2. 3방향 정책: {컨텍스트 신뢰 / 파라미터 신뢰 / 유보}. 신뢰도 기반 중재 디코딩
3. instruction-tuned/RLHF 모델에서 stable entropy 가정 재검증
4. API-only 모델용 근사: top-k logprobs 절단 근사, 프록시 모델 게이팅
5. 1-forward 비용화: 어텐션 마스킹, early-exit 로짓(DoLa식), 경량 게이팅 헤드 증류
6. 장문 생성 확장: 스무딩 복원 + 스팬/문장 단위 게이팅, faithfulness 지표 평가
7. 충돌 유형 taxonomy 진단 벤치마크(temporal / 수치 / 부분 모순 / inter-context / multi-hop 분리 측정)
8. 다중 문서 RAG 일반화: 문서별 신뢰도 가중 mixture-of-contexts 디코딩
9. λ의 적응화: calibration·컨텍스트 품질·검색 점수 기반 동적 조정
10. 하한 단독 이론화: 충돌을 단방향 현상으로 재정식화
