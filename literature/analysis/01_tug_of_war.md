# Tug-of-War Between Knowledge: Exploring and Resolving Knowledge Conflicts in Retrieval-Augmented Language Models

- 저자/발표: Jin et al. (CASIA/UCAS + China Merchants Bank), LREC-COLING 2024
- 코드: https://github.com/jinzhuoran/KConflict/
- 원문: `literature/papers/Tug-of-War Between Knowledge; .../lrec-coling2024-example.pdf`

## 1. 핵심 요약

RALM이 내부 기억(parametric memory)과 외부 검색 근거가 충돌할 때 어떻게 행동하는지를 체계적으로 측정하는 평가 프레임워크를 제시하고, RALM이 Dunning-Kruger 효과, availability bias, majority rule, confirmation bias라는 네 가지 인지편향적 실패 패턴을 보인다는 것을 실증한다. 완화 기법으로 모델 confidence를 재보정하는 디코딩 기법 CD²(Conflict-Disentangle Contrastive Decoding)를 제안한다.

## 2. 방법론

### 태스크 설정: 두 축의 충돌 분류
- 축 1: 내부 기억 vs 외부 소스 충돌
- 축 2: truthful / irrelevant / misleading 근거 간 충돌(외부 소스 내부의 충돌)
- 추가로 multi-hop 추론 하 충돌(충돌 hop 수를 0→4로 증가)

모두 open-book QA 형식, frozen LLM + in-context learning 패러다임.

### 데이터 구성: Memory Induction & Conflict Generation
1. 내부 기억 유도: closed-book QA + greedy decoding으로 내부 답을 추출한 뒤, 그 답을 뒷받침하는 근거를 모델 스스로 생성.
2. 충돌 근거 생성: ChatGPT(τ=1.0)로 counterfactual 답과 문맥적으로 일관된 충돌 근거를 distill. 단순 엔티티 치환이 아니라 coherent한 반사실 문서.
3. 내부 기억이 맞는/틀린 질문으로 나누고 각각 K=3개의 상반된 외부 근거 제공.
4. 외부 소스 내 충돌 세팅에서는 K=10 근거에 misleading 근거를 주입. K ∈ {5,10,20}, truthful:misleading 비율 ∈ {2:0, 2:1, 2:2, 1:2, 0:2}로 변주.
5. confirmation bias 검증: 모델의 내부 기억을 외부 근거로 되집어넣어 자기 기억과 일치하는 근거 선호를 측정.

데이터셋: NQ, TriviaQA, PopQA(long-tail), MuSiQue(multi-hop). 외부 소스는 Wikipedia(KILT).
모델: FLAN-T5-XL/XXL, FLAN-UL2, Baichuan2 7B/13B, LLaMA2 7B/13B, gpt-3.5-turbo.

### 평가 지표
- Correctness: EM, F1, Recall(R)
- Faithfulness: K-Precision(KP). 근거 종류별로 Tru KP / Mis KP / Irr KP 분해.
- Memorization: MR = f_m / (f_m + f_s). 내부 기억이 맞을 때(CMR)와 틀릴 때(IMR)를 나눠 IMR − CMR로 "틀린 기억에 대한 집착"을 측정.

### 제안 기법 CD²
- 내부-외부 충돌용(무학습): `y_t = argmax( s_e(y_t | d, x, y_<t) − α · s_i(y_t | x, y_<t) )`. 외부 소스 있는 로짓에서 없는 로짓을 α배 빼서 틀린 내부 기억 성분을 상쇄.
- truthful/misleading 충돌용(fact-aware instruction tuning): expert LM과 amateur LM("일부러 틀리게 답하라"로 튜닝)의 로짓 대조. `y_t = argmax( s_e − β · s_a )`, β = 0.5.
- 학습: LLaMA2 7B + LoRA, NQ 3,000 예제.

## 3. 주요 결과

- 충돌 근거 제공 시 Con R ≫ Mem R: 외부 근거에 쉽게 흔들린다.
- Dunning-Kruger: 모델이 커질수록 IMR − CMR이 커진다. ChatGPT는 NQ에서 +32.55로, 강한 모델일수록 틀린 기억을 고집.
- Availability bias(PopQA): popularity가 높을수록 내부 기억 쪽으로 기운다.
- Majority rule: 답변이 다수 근거를 따라간다. 단 K=20에서는 오히려 성능 하락.
- 대부분 모델에서 Mis KP > Tru KP: 오도 근거를 더 인용.
- Confirmation bias: 자기 기억과 일치하는 근거 선택률이 일관되게 높음(ChatGPT correct 86.37% 등).
- Multi-hop: 충돌 hop 수 증가에 따라 Recall 단조 하락.
- CD²: NQ-Conf에서 In-context 42.59 → 72.42 R(+29.83), Mis KP 66.43 → 39.62로 감소. Finetune_Conf보다 우위.

## 4. 한계점

### (a) 저자 명시 한계
1. 충돌을 성능과 confidence 두 관점에서만 조사. 내부 메커니즘(뉴런 수준) 해석 부재.
2. CD²는 로짓 접근을 전제로 하므로 블랙박스 LLM에는 적용 불가.

### (b) 암묵적 한계 (비판적 분석)
- **충돌 데이터의 인공성·순환성**: 충돌 근거를 ChatGPT로 생성했고 평가 대상에도 ChatGPT가 포함된다. 실제 웹 오정보(오래된 문서, 부분적으로 맞는 문서, 출처 신뢰도 차이)와 분포가 다르다.
- **충돌 유형 협소**: 단일 정답 엔티티 치환형 factoid QA뿐. 시간적 충돌, 부분적 충돌, 수치·단위 충돌, 논쟁적 사안, 근거 내부 자기모순, unanswerable 케이스 미커버.
- **내부 기억 유도 절차의 타당성**: greedy decoding 1회 출력을 내부 기억으로 간주. self-generated 근거를 재입력하므로 self-preference bias와 충돌 효과가 뒤섞인다.
- **지표 약점**: Recall/K-Precision 모두 토큰 겹침 기반. "근거가 상충한다"고 밝히는 abstention, 충돌 탐지 정확도, calibration(ECE) 미측정.
- **Dunning-Kruger 주장의 교란**: 모델 크기 축과 학습 방식 축(FLAN instruction-tuning vs base vs RLHF)이 얽혀 있다. 동일 계열 내 스케일링 신호는 약하거나 비일관적.
- **CD² 실험 범위 협소**: 백본 LLaMA2 7B 하나, NQ/TriviaQA 2개. 진단에서 강조한 PopQA(availability bias)와 MuSiQue(multi-hop)에는 CD² 미적용.
- **CD² 부작용 미검증**: 내부 기억이 맞고 외부 근거가 틀린 경우의 회귀, 충돌 없는 일반 QA에서의 성능 유지 여부 미보고. α·β 튜닝 민감성.
- **비용**: expert/amateur 두 LM 유지, 토큰당 2~3회 forward.
- **재현성**: 표준편차·seed 반복 없음. 검색기를 실제로 돌리지 않아 검색 노이즈·순서 효과 통제 밖(position bias와 majority rule의 교란 가능성).

## 5. 후속 연구 여지

1. 블랙박스 LLM용 충돌 해소(근거별 독립 답변 후 집계, self-consistency 기반 충돌 탐지 등)
2. 메커니즘 해석: 충돌 시 내부 기억 회로 vs in-context copying 회로의 중재, activation steering
3. abstention·충돌 인지 능력 벤치마크(현재 이 축이 완전히 비어 있음)
4. 현실적 충돌 유형 확장: temporal, 부분적 진실, 출처 신뢰도 메타데이터, 자연 발생 충돌 코퍼스
5. calibration 관점 정식화: 내부/외부 신뢰도의 베이지안 가중 결합
6. popularity에 따라 α를 적응적으로 조절하는 CD² 변형
7. multi-hop 충돌 전용 기법(hop 단위 검증, 충돌 hop 국소화 후 재검색)
8. 컨텍스트 길이·위치 효과와의 상호작용 분리 분석
9. majority rule 기반 RAG poisoning 공격 비용 곡선과 방어 평가
10. CD² 안전성 검증(내부 기억이 옳은 케이스 회귀 측정) 및 백본 일반화
