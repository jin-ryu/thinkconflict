# FaithfulRAG: Fact-Level Conflict Modeling for Context-Faithful Retrieval-Augmented Generation

- 저자/발표: Xiamen University 외, ACL 포맷. 디렉토리명은 "Faithful Retrieval-Augmented Generation via Self-Fact Alignment"이지만 PDF 실제 제목은 FaithfulRAG.
- 원문: `literature/papers/Faithful Retrieval-Augmented Generation via Self-Fact Alignment/acl_latex.pdf`

## 1. 핵심 요약

검색 컨텍스트와 파라메트릭 지식이 충돌할 때, 기존 context-faithful 기법(프롬프팅/디코딩)은 파라메트릭 지식을 강제 억제해 충실성을 얻는데, 이것이 컨텍스트 오독 위험을 오히려 증가시킨다는 것을 실증한다(unfaithful error 6.65% 감소 대가로 incorrect-match error 6.42% 증가). FaithfulRAG는 억제 대신 fact 수준에서 충돌을 명시적으로 모델링: LLM의 내부 지식을 fact 단위로 외재화(self-fact)하고 컨텍스트와 정렬한 뒤 Self-Think 모듈로 충돌을 추론적으로 해소한다. 무학습(training-free) 추론 시점 프레임워크.

## 2. 방법론

### 파이프라인 (3 모듈, 5단계)

**(I) Self-Fact Mining**: 파라메트릭 지식의 계층적 외재화
1. Self-Knowledge Extraction: 질문만 주고(컨텍스트 없이) 답에 필요한 개념·사실 전제를 추상 수준으로 나열
2. Self-Context Generation: 추상 지식을 약 100단어 위키형 배경 문서로 서술화(K_self에 명시적 조건화, GenRead류와의 차별점)
3. Self-Fact Extraction: 원자적 사실 문장으로 분해(해석·의견·추측 금지 지시)

**(II) Contextual Knowledge Alignment**: 충돌 지점 국소화
- 원본 컨텍스트를 고정 크기 청킹(chunk=20), all-MiniLM-L6-v2로 self-fact와 청크의 코사인 유사도 계산, top-K=5 청크 선택 → C_aligned

**(III) Self-Think**: 충돌 해소 추론
- Think 단계: C_aligned 기반 초안 답 + 신뢰성·충분성 자기평가. 불충분 시 원본에서 선택적 보강(fusion)
- Reasoning 단계: 4단계 구조화 CoT — [Fact Analysis] → [Option Matching] → [Context Check] → [Final Verification]

### 태스크/데이터/평가
- 데이터: MuSiQue, SQuAD(KRE 버전, 엔티티 치환 충돌 + golden 비충돌), FaithEval Counterfactual(논리/추론 체인 수준 충돌), RealtimeQA
- 백본: Llama3.1-8B, Qwen2.5-7B, Mistral-7B (+ 3B~16B MoE)
- 지표: ACC(정답 포함 여부), M_R(Memorization Ratio), 에러 케이스 분포(Case 1 over-confidence / Case 2 incorrect-match)
- 베이스라인: Self-RAG, ChatQA, Opin/ATTR/KRE(프롬프팅), CAD/COIECD(디코딩)

## 3. 주요 결과

- FaithEval 81.7(최강 베이스라인 +8.5), SQuAD 86.3(+9.3) 등 3개 백본 전반에서 안정적 우위.
- 비충돌(golden) 세팅에서도 +1.3~1.4로 성능 유지(KRE는 −13.8, CAD −4.1로 훼손).
- 에러 분석: 기존 기법은 Case 1↓/Case 2↑ 트레이드오프인데 FaithfulRAG는 둘 다 감소(−6.8 / −1.6).
- Ablation(평균 81.9 기준): w/o whole Self-Think −22.2로 최대, self-fact mining 각 단계는 −1.1 ~ −1.9에 불과.
- M_R은 Mistral에서 최저이나 Llama/Qwen 백본에서는 COIECD가 더 낮음(ACC 우위로 방어).

## 4. 한계점

### (a) 저자 명시 한계
Limitations 섹션은 "텍스트 입력에 국한, 멀티모달 미지원" 한 가지뿐. 실질적 한계 서술이 매우 빈약하다.

### (b) 암묵적 한계 (비판적 분석)

**추론 비용 미보고**
- 질의당 LLM 호출 최소 4~5회 + 임베딩 유사도 계산. 프롬프팅 베이스라인은 1회, 디코딩은 2 forward. latency/토큰/비용 비교표가 전혀 없다. 동일 예산 self-consistency 베이스라인 부재.

**핵심 novelty와 ablation의 불일치**
- 성능 대부분이 Self-Think(-22.2)에서 나오는데, 그 비교 variant는 "단순 prepend"라 사실상 구조화 프롬프트 유무의 효과. 논문의 핵심 novelty인 self-fact mining 제거는 −1.1 ~ −1.9에 불과. "self-fact 없는 구조화 CoT만" 베이스라인이 없어 novelty의 실제 기여분이 미검증.

**베이스라인 프롬프트 비대칭**
- FaithfulRAG만 정교한 4단계 지시 + few-shot. KRE의 급락(거부 응답)은 파싱/포맷 실패에 가까운데 그대로 대비 효과로 사용.

**데이터 현실성**
- 충돌이 엔티티 치환 합성이라 표층적으로 깨끗한 충돌. 치환된 반사실 답을 정답으로 채점하므로, 향상이 "충돌 해소 능력"인지 "이상 엔티티 탐지 능력"인지 분리 안 됨.
- golden context에도 일부 충돌이 남아있음을 저자 스스로 인정(엄밀한 비충돌 대조 아님).
- RealtimeQA는 극소 서브셋이라 1%p 차이는 통계적으로 무의미할 수 있음. 전 실험에 신뢰구간·유의성 검정·시드 반복 없음.

**충돌 유형의 구조적 공백**
- 컨텍스트 1개 vs 파라메트릭 지식의 이항 충돌만 전제. inter-context conflict(검색 문서 간 상호 모순)는 구조적으로 미처리: top-K 청크가 서로 모순되면 C_aligned 안에 모순이 그대로 들어가고 Self-Think에 중재 절차가 없음.
- 어느 쪽이 옳은지 판정할 외부 근거(출처 시각, 신뢰도)가 없음. Self-Think의 신뢰성 평가는 같은 LLM의 자기평가라 self-preference와 calibration 실패가 전이. self-fact 자체가 환각일 때 걸러낼 장치 전무: 잘못된 self-fact가 잘못된 청크를 끌어올려 오류 증폭 가능. self-fact의 사실성 측정이 없음.

**정렬 모듈의 취약성**
- 코사인 유사도는 의미 유사도이지 모순 탐지가 아님: 동의 청크도 똑같이 유사도가 높다. 정렬 모듈은 충돌 탐지기가 아니라 관련성 재랭커에 가까운데 논문은 이 구분을 하지 않음. NLI 기반 모순 탐지와의 비교 없음.
- chunk=20은 문장 경계·대명사 참조가 끊길 만큼 작고, 긴 컨텍스트에서 top-5 고정은 recall 병목. "민감하지 않아 분석 생략"은 근거 없는 주장.

**평가 지표**
- ACC가 "정답 문자열 포함"이라 verbose 출력에 유리(FaithfulRAG는 Reason+Answer를 길게 생성). 장문 생성 faithfulness(FactScore, 인용 정확도, 인간 평가) 미측정.
- faithfulness 논문이면서 faithfulness 지표(M_R)에서 지는 지점을 정면으로 다루지 않음.

## 5. 후속 연구 여지

1. inter-context conflict의 명시적 중재: fact 그래프 + 출처 메타데이터 증거 가중. 이항 가정을 multi-source로 일반화
2. 유사도가 아닌 모순 기반 정렬: NLI entailment/contradiction으로 동의/모순/무관 3분류 후 유형 라벨과 함께 전달, 유사도 정렬과 직접 비교
3. self-fact 신뢰도 캘리브레이션: 확신도(토큰 확률, self-consistency 빈도) 부여 + 어려운 질의에서만 심층 추론을 트리거하는 적응적 라우팅(비용-정확도 파레토)
4. 비용-정확도 정직한 벤치마킹: 동일 토큰 예산 하 multi-stage 프레임워크 재평가(메타 연구)
5. 현실적 충돌 벤치마크: 시간 변화, 부분적 진실, 전문가 이견, 수치·단위 불일치 유형별 실패 모드 프로파일링
6. self-fact와 실제 파라메트릭 지식의 일치도 검증(probing/knowledge editing): 불일치가 크면 프레임워크의 이론적 전제가 흔들림. 그 자체로 비판 논문 주제
7. 장문 생성 + 문장 수준 attribution 확장
8. 멀티모달 충돌(저자 제안이나 우선순위 낮음)
9. Self-Think 실패 모드 분석: multi-hop(MuSiQue)에서의 상대적 저성능, reasoning 모델에서 명시적 스캐폴딩의 필요성 검증
