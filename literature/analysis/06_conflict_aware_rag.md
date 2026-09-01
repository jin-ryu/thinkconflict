# Conflict-Aware RAG: Multi-Stage Learning with Conflict Signals for Robust Retrieval-Augmented Generation

- 저자/발표: Haiyan Wu 외 6인 (Zhejiang University of Finance and Economics), WWW '26
- 코드: https://github.com/cccccchuang/Conflict-aware-RAG
- 원문: `literature/papers/Conflict-Aware RAG: .../conflict_aware_rag.pdf`

## 1. 핵심 요약

검색 문서와 파라메트릭 지식 간 충돌 완화를 위해, 모델 자신의 perplexity 차이로부터 유도한 충돌 신호 ConScore를 정의하고 학습 데이터 선별과 3단계 학습(SFT → DPO → Reranking) 전 과정에 일관되게 주입한다. 외부 LLM API나 사람 주석 없이 타깃 LLM 자체의 선호 신호만으로 학습 데이터를 구성하는 것이 차별점. 6개 QA 벤치마크에서 Self-RAG, DTA, RAG-DDR 등을 상회.

## 2. 방법론

### 충돌 정의
Figure 1에서 3종 분류: inter-parametric / inter-retrieval / parametric-retrieval. 엄밀한 사실적 모순이 아니라 모델이 지각하는(behaviorally manifested) 충돌, 즉 생성 편차·확신도 변화로 정의. 실질적으로 다루는 것은 뒤의 2종.

### ConScore (perplexity 기반)
- **SFT용 ConScore_S**: d_hard = argmax_{d⁻} [PPL(a⁺|q,d⁻) − PPL(a⁺|q,d⁺)]. 정답 확신을 가장 크게 떨어뜨리는 방해 문서 선택.
- **DPO용 ConScore_D**: (1−λ)·ẑ(log PPL(a_c)) − λ·ẑ(chosen/rejected PPL 격차). margin이 작은 경계 샘플을 상위 랭킹(DPO의 KL 제약 하 학습 효율 때문).
- **Reranking용 ConScore_R**: (μ−1)·CC − μ·IG. CC는 충돌 확신, IG는 문서 조건화로 얻는 정보 이득. 소프트맥스 목표 분포 Q를 만들어 BGE reranker를 KL(P_rerank ‖ Q)로 정렬.

### 충돌 데이터 수집 (4-사분면)
파라메트릭 답과 문서 조건 답의 정오 교차: Consistently Correct / Document Interference / Consistently Incorrect / Document Supplement. 학습에는 Interference와 Supplement만 사용.

### 3단계 학습
1. SFT: 지식 통합 + 내부 지식 보존 + 문서 판별 3종 샘플 (25k)
2. DPO: DPO + α·SFT loss on chosen(퇴화 보정), ConScore_D 상위만 사용 (40k)
3. Reranking: LLM 고정, reranker만 KL 정렬 (22k)

### 실험 설정
- 백본: LLaMA2-7B-Chat, LLaMA3-8B-Instruct (LoRA)
- 코퍼스: Wikipedia 2018 + e5-base-v2, 테스트 k=3
- 데이터셋 6개(NQ, SQuAD, TriviaQA, WebQ, 2WikiMultiHopQA, HotpotQA)를 합쳐 한 번 학습 후 전부 평가
- 지표: EM, F1만. "one or few words" 단답 프롬프트 강제
- 베이스라인: w/o RAG, Vanilla RAG, Self-RAG, DTA, RAG-DDR-8B, SFT on Chosen

## 3. 주요 결과

- LLaMA3-8B 기준 Vanilla RAG 대비 대부분 5~10 EM 포인트 향상, RAG-DDR-8B 대비도 우위.
- Ablation: SFT → +DPO → +Rerank 단조 증가, ConScore 선별 제거(랜덤) 시 뚜렷한 하락.
- 노이즈 강건성: 방해 문서 k_int=3(전부 방해)에도 소폭 하락만.
- 효율: 4.21 EFLOPs / 11.76h, 외부 API 미사용(Self-RAG 15.34 EFLOPs 대비).
- "miss" 조건(문서에 정답 없음)에서 WebQ 69.40 vs Vanilla 22.47: 방해 문서를 무시하고 내부 지식으로 회귀하는 능력 향상.

## 4. 한계점

### (a) 저자 명시 한계 (Appendix C)
1. 단답 프롬프트 의존성: 간결 답변 조건에서만 PPL 변화가 유효한 충돌 대리 지표. long-form 미검증.
2. ConScore 합성이 단순 가중합으로 임의적, 최적성 보장 없음.
3. future work: fine-grained/멀티모달 충돌 지표, continual learning, generator-reranker 협응.

### (b) 암묵적 한계 (비판적 분석)

**충돌 정의의 순환성·자기참조성**
- 모든 라벨이 타깃 LLM 자신의 EM 정오와 PPL로 결정됨. Consistently Incorrect 사분면은 학습에서 명시적으로 배제되어, "모델이 원래 몰랐고 문서도 못 살리는" 실패 모드는 구조적으로 개선 불가(Fig 3에서 Consistently Wrong이 오히려 악화).
- **PPL 격차 = 충돌이라는 등식 미검증**: PPL 격차는 문서 길이, 어휘 빈도, 표면 문자열 중첩, 유창성에 교란된다. 실제 사실적 모순 라벨과의 상관 분석이 없어, ConScore가 충돌이 아니라 단순 무관련도를 재는 것일 가능성을 배제 못 함.

**충돌 유형 커버리지**
- 실제 파이프라인은 지지 문서 vs 방해 문서 이분법: inter-retrieval(동등하게 그럴듯한 두 문서의 상호 모순), inter-parametric 충돌은 데이터 구성에 존재하지 않음.
- **시간적 충돌 미통제**: Wikipedia 2018 스냅샷 vs LLaMA3의 2023 컷오프. "구식 문서 vs 최신 파라메트릭 지식"이라는 핵심 충돌이 노이즈로 섞여 있음. 동기는 웹인데 실험엔 웹이 없음.
- 적대적 오염 문서, 오정보, 개체 중의성, 수치 불일치 미포함.

**실험 설계**
- 지표가 EM/F1뿐: faithfulness, attribution, calibration, abstention 전무. 단답 프롬프트는 EM과 PPL 신호를 동시에 안정화시켜 평가와 방법이 공생(co-adapted).
- "한 번 학습 후 6개 평가"는 in-domain 멀티태스크일 뿐 OOD 일반화 근거 아님.
- "miss" 조건은 정답 가능성으로 조건화된 부분집합이라 개선폭이 과대해 보임.
- Fig 3 본문-그림 불일치("slight decline" 서술 vs 절반 하락 막대), y축 정의 불명.
- 단일 seed, 유의성 검정 없음. 2WikiMultiHopQA F1은 ablation의 +SFT가 최종 모델보다 높은 이상치(논의 없음).
- 추론 시점 기법(CAD, COIECD, RPO, FaithfulRAG)을 인용만 하고 비교하지 않아 "학습이 정말 필요한가"에 답하지 못함.

**확장성/구조**
- ConScore 계산이 질의당 O(m) forward pass: 데이터 구성 비용이 효율 분석에서 빠져 있음.
- 파이프라인이 순차적·탐욕적: reranker 학습 후 LLM 재갱신 루프가 없어 목표 분포 drift.
- 검색기 미학습, λ·μ 전역 상수, 테스트 k=3으로 long-context RAG 거동 미검증.

## 5. 후속 연구 여지

1. ConScore 타당성 검증: counterfactual 코퍼스로 ground-truth 충돌 라벨을 만들어 PPL 신호와의 상관 측정, 교란 요인 제거 후 신호 잔존 확인
2. taxonomy-aware conflict signal: temporal/오정보/문서 간 모순/부분 모순을 구분해 정책 분기(문서 신뢰 / 내부 회귀 / 유보)
3. long-form/인용 기반 확장: claim·문장 단위 충돌 신호 + 출처 귀속
4. 충돌 인지 선택적 응답: risk-coverage, ECE 기반 평가
5. λ·μ의 질의별 적응(게이팅 네트워크 또는 RL)
6. retriever-reranker-generator 공동/반복 최적화(drift 해결)
7. 에이전틱 충돌 해소: 충돌 감지를 트리거로 재검색·출처 대조하는 multi-turn RAG
8. 신호 전이성: 작은 모델의 ConScore로 큰 모델 학습 데이터 선별(O(m) 비용 우회)
9. RAG poisoning 방어: PPL을 낮추도록 최적화된 문서에 대한 취약성 분석
10. 시간 민감 코퍼스 벤치마크: "모델이 최신 vs 문서가 최신" 구분 학습
11. 멀티모달·다국어 충돌
