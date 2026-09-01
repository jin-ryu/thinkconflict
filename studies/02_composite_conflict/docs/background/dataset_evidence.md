# 다중·복합 충돌 데이터셋 논문 분석과 연구 주장 논리

> 작성일: 2026-08-26
> 범위: 기존 보유 데이터의 실제 재집계가 아니라, 다중 충돌 관련 데이터셋 논문이 문제를 어떻게 정의하고 필요성을 입증하는지 분석한다.
> 목적: 활용할 데이터셋을 먼저 선정하고, 이후 prevalence audit과 방법 실험으로 검증할 연구 주장을 확정한다.
> 문서 구성: **Part I은 검색 문서 conflict**, **Part II는 장기 메모리 conflict**를 다룬다. 두 환경의 데이터와 근거를 서로 바꾸어 해석하지 않는다.

---

# Part I. 검색 문서 conflict

## 1. 결론부터

다중 충돌 관련 데이터셋은 존재하지만, 논문마다 “다중”의 의미가 다르다.

1. **여러 요인의 동시 존재:** RAMDocs의 ambiguity + misinformation + noise
2. **모순 위치의 개수 증가:** MAGIC의 1~4 conflict locations
3. **복수 답·관점 cluster 및 pair graph:** QACC·NatConfQA·ConfRAG·GroupQA
4. **여러 conflict type 중 하나를 instance에 부여:** CONFLICTS/DRAGged
5. **implicit reasoning이 필요한 모순:** Ragability

따라서 “다중 충돌을 처음 다룬다”거나 “충돌 유형마다 다른 행동이 필요하다는 것을 처음 보인다”는 주장은 성립하지 않는다. 특히 RAMDocs는 한 질의에서 유효한 ambiguity는 보존하고 misinformation과 noise는 제거해야 한다는 문제를 이미 정의했고, MADAM-RAG으로 함께 해결하려 했다.

현재 문헌에서 직접 채워지지 않은 공백은 다음과 같이 좁혀야 한다.

> 기존 데이터는 다중 충돌을 모순의 개수, 답 cluster의 개수, 고정된 요인 조합, 또는 instance-level 단일 유형으로 표현한다. 그러나 하나의 실제 retrieval set 내부에서 **어떤 claim pair가 어떤 관계이고, 각 관계가 어떤 해결 행동을 요구하며, 여러 행동 사이에 어떤 의존관계가 있는지**는 주석하지 않는다.

우리의 문제는 단순한 multi-conflict가 아니라 **within-instance heterogeneous conflict composition**이다.

### 1.1 “충돌 개수가 여러 개”와 “충돌 유형이 여러 개”의 구분

두 정의는 다음 변수로 분리한다.

- **Conflict cardinality `K`:** 한 instance 안에서 서로 독립적으로 localization되는 conflict claim/span의 수
- **Conflict heterogeneity `H`:** 한 instance 안에서 필요한 서로 다른 resolution action의 수
- **Dependency `D`:** conflict unit이 evidence를 공유하거나 resolution action 사이에 선행·순서 제약이 있는 정도. `D`는 복합 충돌의 정의가 아니라 고난도 하위 조건이다.

| 조건 | 예시 | 주요 난점 |
|---|---|---|
| `K=1, H=1` | 하나의 factual contradiction에서 정답 선택 | 기본 conflict resolution |
| `K>1, H=1` | 네 위치에서 모두 잘못된 사실을 배제 | 다중 탐지·localization과 반복 실행 |
| `K>1, H>1` | outdated fact는 교체하고 ambiguity는 보존하며 misinformation은 배제 | action 식별·합성·상호간섭 |

`H>1`이면 일반적으로 둘 이상의 claim relation이 필요하므로 `K>1`도 동반한다. 반면 `K>1`이라고 해서 반드시 `H>1`인 것은 아니다.
본 연구의 메인 대상은 `K>1, H>1`이며, 이 중 `D>0` 사례에서 graph·plan search의 추가 필요성을 분석한다. 따라서 연산 의존성이 없어도 서로 다른 action을 합성해야 하면 복합 충돌에 포함한다.

### 1.2 두 후보의 비판적 비교

| 기준 | 충돌 개수 `K>1` | 충돌 유형·action `H>1` |
|---|---|---|
| 정의·주석의 명확성 | 높음. conflict span 수로 셀 수 있음 | 낮음. taxonomy 경계와 multi-label 합의가 필요 |
| 기존 선점 | **강함. MAGIC이 1~4개를 직접 통제** | 부분 선점. RAMDocs와 ContraPRT가 특정 조합을 다룸 |
| 기존 데이터 즉시 사용 | MAGIC 사용 가능 | RAMDocs는 가능하지만 더 넓은 유형은 재주석 필요 |
| 방법론 기여 가능성 | localization·coverage 개선으로 한정되기 쉬움 | 서로 다른 action의 계획·실행이라는 방법 기여 가능 |
| 자연 발생 근거 | 여러 답·cluster 근거는 있으나 conflict span 수 prevalence는 제한적 | DRAGged 유형들의 자연 동시 발생률은 아직 미측정 |
| 위험 | MAGIC의 후속 incremental work로 보일 위험 | 문제를 인위적으로 만들었다는 비판, annotation 비용 |
| 예상 논문 기여도 | 안전하지만 중간 | 성공 시 높지만 empirical validation이 필수 |

### 1.3 선택

메인 문제는 **충돌 유형의 단순 개수**보다 더 직접적으로, **서로 다른 resolution action이 한 instance에서 필요한 경우(`H>1`)**로 정한다. 충돌 개수 `K`는 버리지 않고 난이도 통제축과 baseline 분석축으로 사용한다.

선택 이유는 다음과 같다.

1. `K>1`만으로는 MAGIC의 문제정의·데이터·분석과 너무 가깝다.
2. 같은 action을 여러 번 수행하는 것은 구조화된 해결 pipeline의 필요성을 충분히 설명하지 못한다.
3. `H>1`은 “왜 단일 type routing이나 하나의 arbitration rule이 부족한가”를 직접 설명한다.
4. 현재 목표인 training-free claim factorization과 selective action planning에 자연스럽게 연결된다.

단, 논문에서는 “여러 DRAGged label이 흔하다”를 전제하지 않는다. 다음 순서로 증거를 쌓는다.

```text
자연 검색에서 복수 답·문서 충돌이 존재한다 — QACC
                ↓
한 conflict set에서 여러 요인이 함께 있으면 행동이 충돌한다 — RAMDocs
                ↓
복수 conflict type 자체도 구성·관측 가능하다 — ContraPRT
                ↓
DRAGged식 semantic action type이 실제 한 instance에서 함께 나타나는가 — 후속 multi-label audit
```

### 1.4 중단·전환 기준

후속 pilot에서 `H>1`의 strict 사례가 거의 없거나 annotator가 action type에 합의하지 못하면 자연 prevalence 주장을 포기한다.

- strict `H>1` 비율이 충분하고 multi-label IAA가 안정적: natural heterogeneous composition을 메인으로 유지
- strict 사례는 적지만 controlled composition에서 명확한 interaction이 있음: robustness stress-test로 축소
- strict 사례와 interaction 모두 약함: `K>1` localization/coverage 문제로 전환하되 MAGIC 대비 새 기여를 다시 설계

비율 임계값은 pilot 전에 별도 사전등록한다. 결과를 본 뒤 임계값을 정하면 연구 방향 선택에 researcher degree of freedom이 생긴다.

---

## 2. 논문별 “다중 충돌” 정의와 필요성 근거

## 2.1 RAMDocs / Retrieval-Augmented Generation with Conflicting Evidence

- 논문: [Retrieval-Augmented Generation with Conflicting Evidence](https://arxiv.org/abs/2504.13079)
- 등재: COLM 2025
- 데이터: RAMDocs, 500 queries
- 다중 충돌의 의미: 하나의 query에 ambiguity, misinformation, noise가 동시에 존재

### 논문이 정의한 문제

동일한 검색 집합 안에서도 disagreement의 원인이 다르면 기대 행동이 반대가 된다.

| 원인 | 논문이 요구하는 행동 |
|---|---|
| ambiguous query·동명이인 | 서로 다른 유효 답을 모두 제시하고 대상을 구분 |
| misinformation | 사실이 아닌 답을 억제 |
| noise·irrelevant document | 답 생성에서 제외 |

즉 “충돌이면 하나를 고른다”는 전략은 ambiguity에서 실패하고, “모든 관점을 보존한다”는 전략은 misinformation에서 실패한다. 논문은 이 상충을 **present valid conflicts while filtering invalid conflicts**라는 trade-off로 설명한다.

### 데이터 구성과 빈도 해석

- AmbigDocs를 바탕으로 query당 1~3개의 유효 답을 표본화한다.
- 유효 답 하나당 1~3개의 supporting documents를 둔다.
- query마다 misinformation 0~2개와 noise 0~2개를 무작위로 추가한다.
- 평균 2.20 valid answers, 5.53 documents, 그중 3.84개는 valid answer support이고 1.70개는 misinformation/noise다.

이 수치는 **자연 검색에서 복합 충돌이 이 비율로 발생한다는 prevalence가 아니다.** 저자가 복합 상황을 평가하기 위해 구성한 controlled distribution이다.

### 왜 해결해야 하는가

- 강한 Llama3.3-70B 기반 prompt baseline도 RAMDocs에서 최대 32.60 EM에 그쳤다.
- MADAM-RAG도 같은 표에서 34.40 EM으로 절대 성능이 낮다.
- 유효 답 사이의 supporting-document imbalance가 증가하면 minority valid answer가 누락된다.
- misinformation 문서가 늘어나면 모든 방법의 성능이 저하된다.

### 우리와 겹치는 지점과 남은 공백

가장 직접적인 선행연구다. `KEEP_BOTH + PREFER/FILTER`를 함께 수행한다는 문제와 multi-agent 해결은 이미 선점됐다. 차별점은 다음에 있어야 한다.

- debate가 아니라 명시적인 claim relation과 resolution action을 산출
- 한정된 ambiguity+misinformation+noise 조합을 넘어 temporal·scope·opinion·complementary까지 표현
- action을 최종 aggregator가 암묵적으로 수행하게 두지 않고 plan과 실행 결과를 평가
- 문서 수×debate round 비용 대신 필요한 단계만 실행하는 selective inference

## 2.2 MAGIC

- 논문: [MAGIC: A Multi-Hop and Graph-Based Benchmark for Inter-Context Conflicts](https://aclanthology.org/2025.findings-emnlp.466/)
- 등재: Findings of EMNLP 2025
- 데이터: 1,080 context pairs
- 다중 충돌의 의미: 두 context 사이에 존재하는 contradiction location의 수가 1~4개

### 데이터 구성

Wikidata5M subgraph를 추출한 뒤 node·edge를 교란하고 KG-to-text로 원문과 교란 문맥을 만든다. 다음 두 축을 교차한다.

- single-hop vs. multi-hop
- 1 conflict vs. N conflicts; 실제 세부 구간은 1·2·3·4개

1,080개 중 2~4개 conflict를 가진 instance는 572개다. 이 비율도 설계로 배분한 값이므로 자연 prevalence가 아니다.

### 왜 해결해야 하는가

- conflict 수가 늘면 conflict 존재 여부의 detection은 쉬워진다.
- 반대로 모든 conflict span을 정확히 찾는 localization은 악화된다.
- 평균 localization score는 conflict 수가 1에서 4로 늘 때 크게 감소한다.
- multi-hop conflict는 single-hop보다 detection과 localization 모두 어렵다.

### 우리와의 관계

MAGIC은 “충돌이 많으면 더 어렵다”를 단순 accuracy가 아니라 localization failure로 보여주는 강한 근거다. 그러나 여러 conflict가 모두 같은 종류의 contradiction이고, 주된 task가 detection/localization이다. 서로 다른 resolution action의 조합은 제공하지 않는다.

따라서 MAGIC은 주 데이터셋보다는 다음 용도로 적합하다.

- claim relation extractor의 다중 위치 recall 평가
- conflict count와 reasoning-hop 증가에 따른 scaling curve
- 해결에 들어가기 전 conflict localization 상한 측정

## 2.3 QACC

- 논문: [Open Domain Question Answering with Conflicting Contexts](https://aclanthology.org/2025.findings-naacl.99/)
- 등재: Findings of NAACL 2025
- 데이터: unambiguous open-domain questions + Google top-10 contexts
- 다중 충돌의 의미: 검색 문맥에서 서로 다른 answer candidates가 둘 이상 발견됨

### 자연 발생 근거

QACC는 이 목록에서 prevalence 주장에 가장 유용하다.

- unambiguous open-domain questions의 약 25%에서 서로 다른 답을 주장하는 검색 문맥이 발견됐다.
- conflict subset의 distinct answer 수는 평균 2.47개다.
- 전체 질문 중 10%는 적어도 3개, 3%는 적어도 4개의 distinct answers를 가진다.
- conflict subset의 29%에서는 하나의 답이 문맥 절반 이상에서 반복된다.

annotator는 정답 선택 이유로 majority, source trust, common sense, recency를 복수 선택할 수 있었다. 논문은 여러 요인이 동시에 사람의 adjudication에 영향을 준다고 명시한다.

### 왜 해결해야 하는가

- 문제를 conflict-enriched query로 먼저 골라낸 것이 아니라, 명확한 open-domain question을 Google에 검색해 관측했다.
- 따라서 conflicting retrieval이 예외적인 synthetic failure만은 아니라는 근거가 된다.
- 동시에 사람이 majority·source·memory·time 같은 여러 기준을 섞어 판단하므로 단순 문서 투표가 충분하지 않음을 보여준다.

### 한계와 활용

- subjective·unanswerable·multiple-valid-answer question은 범위 밖이다.
- 여러 답은 존재하지만 conflict relation type과 resolution action은 주석하지 않는다.
- 이유 목록은 정답 선택 근거이지 action precedence가 아니다.

QACC는 **자연 발생 필요성**과 factual adjudication을 보여주는 핵심 real-world validation set으로 적합하다. 기존 답·문서 주석 위에 claim relation과 action을 추가 주석할 가치가 가장 크다.

## 2.4 CONFLICTS / DRAGged

- 논문: [DRAGged into Conflicts](https://arxiv.org/abs/2506.08500)
- 상태: arXiv preprint 확인 기준
- 데이터: 458 queries, query당 평균 9.2 search results
- 다중 충돌의 의미: 서로 다른 conflict type taxonomy를 한 benchmark에서 다룸

### 논문이 정의한 유형과 행동

| 유형 | N | 기대 행동 |
|---|---:|---|
| no conflict | 161 | 직접적이고 명확하게 답함 |
| complementary information | 115 | 호환 가능한 부분 답을 통합 |
| conflicting opinions/research | 115 | 상충 관점을 균형 있게 제시 |
| outdated information | 62 | 최신 정보를 선택하고 시간 맥락을 반영 |
| misinformation | 5 | 부정확한 source를 배제하고 검증된 답을 선택 |

저자들은 유형이 중요한 이유를 **유형마다 desired behavior가 다르기 때문**이라고 명시한다. 실제로 type을 먼저 예측하고 생성하는 pipeline prompt도 실험했으며 vanilla보다 expected-behavior accuracy가 평균 약 9점 높았다.

### 빈도 해석

458개 중 297개, 즉 65%가 저자 taxonomy상 conflict 범주였다. 그러나 query 자체를 다양한 conflict가 나타날 것으로 알려진 데이터에서 수집했으므로 일반 검색 traffic의 prevalence로 사용하면 안 된다. 특히 자연 top-10에서 misinformation은 5건뿐이었고, 저자들은 검색엔진의 저품질 source 억제 때문일 가능성을 제시한다.

### 우리와 겹치는 지점과 공백

“유형별 행동”과 “classify then generate pipeline”은 이미 선점됐다. 그러나 각 instance에는 하나의 상호배타적 type만 부여된다. 예를 들어 한 retrieval set 안에 outdated claim과 complementary claim이 함께 있어도 현재 annotation으로는 표현되지 않는다.

따라서 DRAGged는 다음 용도로 적합하다.

- 자연 web 문서에서 type별 action을 검증하는 데이터
- 기존 단일 label을 claim-pair multi-label로 재주석해 mixed-type co-occurrence를 확인하는 후보
- 단, misinformation 표본이 5개뿐이므로 misinformation 성능의 주 benchmark로는 부적합

## 2.5 NatConfQA / Consensus or Conflict?

- 논문: [Consensus or Conflict? Fine-Grained Evaluation of Conflicting Answers in Question-Answering](https://aclanthology.org/2025.uncertainlp-main.13/)
- 등재: UncertaiNLP 2025
- 데이터·코드: [EN555/ContraQA](https://github.com/EN555/ContraQA)
- 공개 v1.0: 855개 문항; Conflict 269, Support 408, Neutral 178
- 다중 충돌의 의미: 한 질문의 복수 answer와 모든 answer pair에 대한 conflict graph

### 논문이 정의한 문제

NatConfQA는 multi-answer QA에서 여러 답을 모두 생성하는 것만으로 충분하지 않고, **어떤 answer pair가 서로 충돌하는지**까지 식별해야 한다고 정의한다. fact-checking 자료의 support·refute evidence를 이용해 자연 문장과 근거를 구성하고, 각 답을 evidence에 연결하며 `conflicting_answer_pairs`를 제공한다. 따라서 문서나 답의 개수를 곧바로 충돌 수로 간주하지 않고, pair graph를 통해 실제 양립 불가능 관계를 분리할 수 있다.

공개 v1.0을 재집계하면 conflict WH 문항은 89개다. 그중 적어도 하나의 conflicting pair와 하나의 non-conflicting pair가 함께 있는 strict WH-mix는 22개다. 이 22개는 한 instance 안에서 모든 answer pair가 같은 관계라고 가정할 수 없음을 직접 보여준다. 다만 이것은 공개 파일에 대한 본 연구의 파생 조건이며, 일반 web prevalence 수치가 아니다.

### 왜 해결해야 하는가

원 논문은 강한 LLM도 conflict 존재 여부, 전체 답 coverage, 특정 conflict pair 식별을 동시에 안정적으로 수행하지 못하며, 모델이 일부 답을 누락하거나 모든 답을 서로 충돌한다고 과잉 일반화할 수 있음을 보인다. 이는 복수 answer를 단순 나열하는 것과 unit별 관계를 정확히 구조화하는 것이 다른 과제라는 근거다.

### 우리와의 관계와 한계

NatConfQA의 answer-pair graph는 `K` 후보와 unit 병합 규칙을 검증하기에 가장 직접적이다. 특히 같은 proposition을 공유하는 여러 pair를 한 conflict unit으로 병합해야 하므로 문서 수·pair 수·`K`가 다르다는 점을 시험할 수 있다.

그러나 원 gold는 주로 factual support/refute 관계이며 `SUPERSEDE`, `CONDITION`, `KEEP_BOTH` 같은 resolution operator를 제공하지 않는다. 따라서 NatConfQA만으로 `H>1` prevalence를 주장하지 않고 다음 역할로 제한한다.

- answer-pair graph에서 atomic conflict unit과 `K`를 파생하는 구조 검증
- conflicting/non-conflicting pair가 섞인 strict WH-mix의 과분해 방지
- ConfRAG에서 만든 넓은 operator taxonomy가 factual graph에 무리하게 적용되지 않는지 보는 보조 자료

## 2.6 ConfRAG

- 논문: [Benchmarking LLM’s Capability in Reasoning over Conflicting Web References](https://aclanthology.org/2026.acl-long.11/)
- 등재: ACL 2026 Main, Long
- 데이터: 1,814 questions, 17,372 web documents, 질문당 평균 9.58 paragraphs
- 다중 충돌의 의미: 질문마다 여러 answer clusters와 각 cluster를 지지하는 reason clusters가 존재

### 데이터와 난이도

- answer cluster 수는 2~8개이며 대다수는 2~3개다.
- 1,037개, 즉 57.2%가 answer clusters 사이의 strong contradiction으로 판정됐다.
- GPT-4.1도 NMI 0.47, answer coverage 0.45, reason coverage 0.15 수준이다.
- 2개에서 4개 cluster로 증가할 때 GPT-4.1 answer coverage가 0.48에서 0.32로 감소하고 reason coverage도 거의 절반으로 줄었다.

### 빈도 해석의 주의점

57.2%는 일반 web query prevalence가 아니다. 논문은 controversial 또는 commonly misunderstood question을 생성·선별한 뒤 web 문서를 수집했다. 따라서 이 수치는 **conflict-rich real documents 안에서 strong contradiction이 얼마나 남는지**를 나타낸다.

### 우리와의 관계

ConfRAG은 여러 answer·reason cluster를 보존하는 능력을 평가하기에 좋다. 하지만 객관적 단일 truth adjudication보다는 관점의 분리·coverage가 중심이고, 문서 하나가 여러 conflicting cluster를 동시에 지지하는 경우를 제외한다. temporal supersession이나 misinformation rejection용 gold도 제한적이다.

활용한다면 다음 external generalization에 적합하다.

- `KEEP_BOTH/PRESENT_VIEWS + MERGE_REASONS + FILTER_IRRELEVANT`
- cluster 수 증가에 따른 compositional degradation
- long-form answer에서 evidence attribution과 reason coverage

## 2.7 GroupQA

- 논문: [Rational Synthesizers or Heuristic Followers?](https://aclanthology.org/2026.findings-acl.2003/)
- 등재: Findings of ACL 2026
- 데이터: 1,635 controversial yes/no questions, 15,058 documents
- 다중 충돌의 의미: 찬성과 반대 evidence group이 동시에 존재하고 각 group 안에 여러 문서가 존재

### 논문이 입증한 문제

- 모델 선택이 evidence quality뿐 아니라 반복 빈도와 위치에 영향을 받는다.
- balanced conflicting context에서도 먼저 제시된 evidence가 anchor로 작용한다.
- redundant evidence는 독립적인 추가 근거가 아닌데도 belief update를 일으킬 수 있다.

### 활용과 한계

모든 질문이 yes/no 양측 evidence를 갖도록 선별됐으므로 prevalence 데이터가 아니다. 또한 최종 action은 주로 두 stance 중 arbitration이어서 heterogeneous action composition과는 다르다.

다만 다음 stress test에 유용하다.

- `COLLAPSE_DUPLICATES` 전후의 결과 비교
- evidence order와 repetition bias
- 동일 정보의 반복과 독립 근거를 구분하는 counterfactual test

## 2.8 Ragability

- 논문: [Ragability Benchmark](https://aclanthology.org/2026.lrec-1.182/)
- 등재: LREC 2026
- 다중 충돌의 의미: 직접 표현되지 않고 두 문맥을 함께 추론해야 드러나는 implicit inter-context conflict

현재 모델은 “모순이 있는가?” 같은 binary 질문에는 비교적 답하지만, 실제 내용을 묻는 QA에서는 충돌을 적절히 반영하지 못한다. 이는 detection 성공이 resolution 성공을 보장하지 않는다는 근거다.

주요 활용은 implicit-relation detector와 no-conflict gate 검증이며, 복수 action composition의 주 데이터셋으로는 적합하지 않다.

## 2.9 ContraPRT / Cross-Validated Re-ranking

- 논문: [Eliminating Retrieval Knowledge Conflicts: Cross-Validated Re-ranking with Large Language Models](https://doi.org/10.1109/IJCNN64981.2025.11228012)
- 등재: IJCNN 2025
- 데이터: ContraPRT
- 다중 충돌의 의미: 하나의 conflicting passage pair가 negation·content·causal·perspective/view/opinion·numeric·emotion/mood/feeling·relation 중 복수 aspect를 동시에 가질 수 있음

### 직접적인 복수 유형 근거

이 연구는 single conflict type과 multiple conflict types 조건을 명시적으로 구분한다. 논문 예시는 동일 passage pair가 `Negation`과 `Perspective/View/Opinion`을 함께 갖는 것으로 주석하며, 본문에서는 `negation + relation + content`가 동시에 나타나는 사례를 설명한다.

따라서 “한 충돌 사례가 반드시 하나의 type에만 속한다”는 가정에 대한 직접적인 반례다.

### DRAGged와의 차이

ContraPRT의 type은 주로 **모순이 표현되는 언어·논리 형식**이다.

- negation, numeric, causal, relation, content

DRAGged의 type은 주로 **충돌 원인과 기대 출력 행동**이다.

- complementary → 통합
- opinion → 관점 보존
- outdated → 최신 정보 선택
- misinformation → 부정확한 정보 배제

따라서 ContraPRT는 multi-label conflict가 가능하다는 근거지만, `SUPERSEDE + KEEP_BOTH`처럼 서로 다른 해결 action이 자연스럽게 공존한다는 직접 증거는 아니다. 또한 task가 passage re-ranking이므로 모든 유형을 “잘못된 passage 제거”로 환원하는 경향이 있다.

### 활용

- multi-label annotation schema가 실현 가능하다는 선행근거
- `K`와 type/aspect 수를 분리하는 참고 benchmark
- 우리 taxonomy가 원인·표현 형식·해결 action을 혼합하지 않도록 하는 경고 사례

## 2.10 DRUID와 CONFACT: 간접적인 현실성 근거

### DRUID

- 논문: [A Reality Check on Context Utilisation for RAG](https://aclanthology.org/2025.acl-long.968/)
- 등재: ACL 2025 Main, Long

DRUID는 실제 web evidence에 stance뿐 아니라 unreliable, insufficient, difficult-to-understand, implicit, uncertain, source·시점 관련 특성을 함께 측정한다. 저자들은 real-world context가 synthetic benchmark보다 복잡하고 다양하며, 하나의 singleton context characteristic과 모델 행동의 상관은 작다고 보고한다.

이는 실제 문서가 여러 특성을 동시에 가질 수 있고 단일 속성으로 failure를 설명하기 어렵다는 근거다. 다만 이 특성들은 모두 DRAGged conflict type이 아니므로, semantic conflict type co-occurrence의 직접 prevalence로 인용해서는 안 된다.

### CONFACT

- 논문: [Resolving Conflicting Evidence in Automated Fact-Checking](https://arxiv.org/abs/2505.17762)
- 데이터: CONFACT

CONFACT는 사실검증 claim 3,180개에 대해 Google top-10을 수집했고, support와 refute 문서가 함께 있는 611개(17.8%)를 자동 선별한 뒤 사람 검증 split을 구성했다. 각 source의 stance와 credibility도 함께 주석한다.

이 자료는 하나의 retrieval set에 상반된 stance, source credibility 차이, majority imbalance가 함께 나타날 수 있음을 보여준다. 그러나 최종 task는 binary factual adjudication이므로 complementary·opinion·outdated가 함께 발생한다는 직접 증거는 아니다.

### 해석

RAMDocs와 ContraPRT는 복수 요인·복수 type의 **직접 가능성**을, DRUID와 CONFACT는 실제 검색 문맥이 단일 속성보다 복잡하다는 **간접 현실성**을 제공한다. 현재까지 확인된 문헌만으로는 DRAGged의 semantic 유형들이 자연 web retrieval의 동일 instance에서 얼마나 자주 공존하는지 알 수 없다. 이것이 바로 후속 multi-label audit이 필요한 이유다.

---

## 3. 데이터셋 비교와 활용 우선순위

| 데이터셋 | 자연 문서 | 자연 prevalence 근거 | 한 instance의 다중성 | 다양한 기대 행동 | action gold | 권장 역할 |
|---|:---:|:---:|---|:---:|:---:|---|
| RAMDocs | 일부 검색 + synthetic misinfo | X | ambiguity+misinfo+noise 동시 | O | 문서 type에서 일부 파생 | **주 controlled benchmark** |
| QACC | O | **O: 약 25%** | 평균 2.47 answer candidates | 일부 | X | **주 real-world factual validation** |
| NatConfQA | fact-checking 기반 자연 evidence | X, conflict-enriched | answer-pair conflict graph; strict WH-mix 22 | 주로 factual select | pair-level conflict gold | **K·unit graph 구조 검증** |
| CONFLICTS/DRAGged | O | X, conflict-enriched sampling | instance-level 단일 type | **O** | type별 behavior | **다양한 action과 재주석 후보** |
| ConfRAG | O | X, controversy-filtered | 2~8 answer/reason clusters | 관점 보존 중심 | cluster gold | external multi-view test |
| MAGIC | KG 기반 synthetic text | X | 1~4 locations, single/multi-hop | X | conflict spans | detector/localizer stress test |
| GroupQA | O | X, 양측 evidence 필수 | stance별 여러 documents | 단일 arbitration | stance·strength | duplication/order stress test |
| Ragability | 사례 기반 후 entity 치환 | X | implicit relation | 제한적 | conflict 여부 | implicit gate test |
| ContraPRT | 구성형 | X | 한 pair에 복수 linguistic/logical aspects | 모든 type을 제거로 처리 | multi-type aspect | multi-label 가능성·taxonomy 참고 |
| DRUID | O | 일부 현실 분포 | 한 evidence의 복수 context properties | 직접 action 없음 | stance·properties | 단일 속성 가정 비판 |
| CONFACT | O | conflict-likely claim에서 17.8% 자동 선별 | stance+credibility+imbalance | factual select | stance·credibility | 실제 factual conflict 보조 검증 |

### 2026년 10월 ARR을 고려한 현실적 구성

파일럿 1 필수 세트:

1. **ConfRAG:** 자연 web에서 `K/H` 재주석과 제한된 conflict-rich prevalence
2. **NatConfQA:** answer-pair graph를 이용한 `K`·unit 병합 규칙 검증
3. **QACC:** factual conflict가 주로 `H=1`로 수렴하는지 보는 대조군

발견·후속 세트:

4. **ConflictingQA:** 희귀 operator 후보 탐색; prevalence 계산 제외
5. **RAMDocs·MAGIC·DRAGged:** 파일럿 통과 후 각각 mixed-factor, `K`, single-type 외부 평가에 사용

새 데이터 전체를 처음부터 구축하기보다 기존 세 데이터에 공통 claim-relation-action annotation layer를 얹는 편이 현실적이다. 다만 실제 annotation 규모는 별도의 prevalence pilot 이후 결정한다.

---

## 4. 문헌에서 직접 지지되는 주장과 지지되지 않는 주장

### 4.1 지금 직접 주장할 수 있는 것

**주장 A — conflicting retrieval은 드문 synthetic corner case가 아니다.**
QACC는 명확한 open-domain question의 약 25%에서 Google top-10 contexts가 서로 다른 답을 포함한다고 보고했다.

**주장 B — conflict set은 흔히 둘 이상의 후보를 포함한다.**
QACC conflict subset은 평균 2.47개 답을 가지며, NatConfQA는 모든 answer pair의 conflict graph를 제공하고, ConfRAG은 질문당 2~8개의 answer clusters를 제공한다.

**주장 C — 다중성은 단순 detection보다 localization·coverage·resolution을 어렵게 한다.**
MAGIC에서는 conflict 수가 늘수록 localization이 악화되고, ConfRAG에서는 cluster 수가 늘수록 answer/reason coverage가 감소한다.

**주장 D — conflict 원인에 따라 요구 행동이 서로 양립하지 않을 수 있다.**
RAMDocs는 valid ambiguity를 보존하면서 misinfo/noise를 제거해야 한다고 정의한다. CONFLICTS도 complementary는 통합, opinion은 균형 제시, freshness/misinformation은 선택·배제하도록 행동을 구분한다.

**주장 E — 현재 방법의 headroom이 크다.**
RAMDocs에서 강한 baseline과 MADAM-RAG 모두 낮은 EM을 보이고, ConfRAG에서 GPT-4.1의 answer/reason coverage도 낮다. CONFLICTS에서는 oracle type을 제공했을 때 predicted-type pipeline보다 expected behavior가 크게 높다.

### 4.2 아직 주장하면 안 되는 것

- 일반 web query의 상당수가 서로 다른 **conflict type을 한 instance에서 동시에** 포함한다.
- `SUPERSEDE`, `KEEP_BOTH`, `CONDITION`, `COLLAPSE_DUPLICATES`, `ABSTAIN` 사이의 순서 의존 사례가 자연 분포에서 흔하다.
- 기존 연구는 다중 충돌이나 유형별 행동을 전혀 다루지 않았다.
- RAMDocs·MAGIC·ConfRAG의 내부 비율이 일반 검색 traffic prevalence를 나타낸다.
- 명시적 operator plan이 multi-agent debate보다 우수하다.

위 항목은 이후 dataset audit과 실험으로 증명해야 할 가설이다.

---

## 5. 우리 논문의 주장 논리

논문의 서론 논리는 다음 순서가 가장 방어 가능하다.

### 5.1 현상

실제 검색에서는 서로 다른 답이 자주 함께 검색된다. QACC가 자연 open-domain retrieval에서 약 25%의 conflict incidence와 평균 2.47개 distinct answers를 보고했다.

### 5.2 기존 benchmark가 보여준 난점

다중성에는 서로 다른 형태가 있다. MAGIC은 conflict location과 hop이 늘면 localization이 어려워짐을, ConfRAG은 answer cluster가 늘면 answer/reason coverage가 떨어짐을, RAMDocs는 ambiguity·misinformation·noise를 동시에 처리할 때 절대 성능이 낮음을 보였다.

### 5.3 기존 해결의 불완전성

- 단일 conflict label 기반 pipeline은 CONFLICTS가 이미 제안했지만, 한 instance 전체를 하나의 유형으로 축약한다.
- MADAM-RAG은 여러 요인을 함께 처리하지만 debate와 aggregator 내부에서 해결 행동이 암묵적으로 일어나며 비용이 크다.
- MAGIC은 다중 위치를 주석하지만 resolution action을 제공하지 않는다.
- ConfRAG은 여러 관점을 보존하지만 objective truth selection·temporal supersession·misinformation rejection을 함께 다루지 않는다.

### 5.4 연구 공백

> 기존 benchmark는 “충돌이 몇 개인가” 또는 “이 문항은 어떤 유형인가”를 알려주지만, **한 retrieval set의 각 claim conflict가 무엇을 요구하고 이 행동들을 어떻게 합성해야 하는가**는 나타내지 않는다.

### 5.5 제안 과제

**Compositional Conflict Resolution**을 다음 입력과 출력으로 정의한다.

- 입력: query와 heterogeneous retrieved documents
- 중간 표현: query-conditioned atomic claims와 pairwise relations
- action: `SELECT/PREFER`, `PRESERVE`, `CONDITION`, `MERGE`, `SUPERSEDE`, `COLLAPSE_CORRELATED`, `DISCARD_IRRELEVANT`, `ABSTAIN`
- plan: 한 instance에 필요한 action set과 dependency graph
- 출력: action 결과에 일치하고 source가 귀속된 답

이때 “순서”를 논문의 출발 전제로 강하게 주장하지 않는다. 먼저 dependency를 더 일반적인 개념으로 두고, 실제 annotation과 intervention에서 비가환적인 action pair가 확인될 때 **order-sensitive resolution**을 핵심 결과로 승격한다.

### 5.6 방법 가설

> 하나의 전역 label 또는 전역 arbitration rule보다 claim-level relation을 factorize하고 필요한 action만 계획·실행하는 training-free resolver가, unseen conflict composition에서 더 정확하고 multi-agent debate보다 비용 효율적일 것이다.

---

## 6. 예상 contribution 문장

현재 단계에서 가장 안전한 contribution 초안은 다음과 같다.

1. 기존 다중 충돌 benchmark를 통합적으로 분석해 conflict multiplicity를 **location multiplicity, answer multiplicity, factor multiplicity, action multiplicity**로 구분한다.
2. 기존 데이터에 없는 claim-level relation, required action, action dependency를 표현하는 **Compositional Conflict Resolution** task와 annotation schema를 제안한다.
3. RAMDocs·QACC·CONFLICTS를 공통 schema로 확장해 controlled composite conflict와 natural web conflict를 함께 평가한다.
4. 학습 없이 relation을 factorize하고 action plan을 선택적으로 실행하는 resolver를 제안하고, oracle relation과 automatic relation 조건을 분리 평가한다.
5. conflict count가 아니라 **action composition complexity**에 따른 성능·비용·오류 전파를 분석한다.

2번과 3번은 prevalence pilot 결과에 따라 범위를 조정한다. 실제 mixed-action 사례가 적다면 “자연적으로 흔하다”는 주장을 버리고, controlled stress test와 retrieval-factor composition 연구로 낮춰야 한다.

---

## 7. 다음 단계: 데이터 분석에서 확인해야 할 질문

이 문서에서는 데이터셋 자체를 재집계하지 않는다. 후속 prevalence audit에서 다음을 확인한다.

1. QACC·NatConfQA·ConfRAG의 한 instance에 둘 이상의 claim relation type이 실제로 나타나는가?
2. 둘 이상의 서로 다른 action이 필요한 instance 비율은 얼마인가?
3. action들이 단순 병렬 적용 가능한가, 아니면 dependency·order가 필요한가?
4. mixed-action 사례가 모델의 정답률·coverage·attribution을 실제로 더 낮추는가?
5. RAMDocs의 controlled composition에서 발견한 실패가 natural web 사례에서도 재현되는가?
6. 자동 relation detector 오류를 제외한 oracle-action 조건에서도 composition failure가 존재하는가?

이 질문에 답한 뒤에만 prevalence와 order-sensitive resolution을 논문의 강한 empirical claim으로 사용한다.

---

# Part II. 장기 메모리 conflict

> 이 Part는 파일럿 2인 **Compositional Memory Conflict**에 사용할 데이터셋을 조사한 결과다.
> 검색 문서 conflict와 memory conflict는 근거·시간·사용자 상태의 의미가 다르므로 데이터, taxonomy, 실험 주장을 분리한다.

## 8. 결론부터

파일럿 2에 바로 쓸 수 있는 완성형 `K>1,H>1` memory-conflict 데이터셋은 아직 확인되지 않았다. 기존 데이터는 대체로 하나의 query가 하나의 attribute 또는 하나의 conflict policy만 평가한다. 따라서 우리 데이터 기여는 단순한 새 대화 생성이 아니라, **공개된 동일-persona history에서 여러 query-relevant conflict unit을 찾아 하나의 자연스러운 multi-goal query로 조합하고 unit별 policy gold를 추가하는 것**이다.

현 시점의 권장 구성은 다음과 같다.

1. **주 구성 source — MemConflict:** 같은 persona의 장기 history, dynamic/static/conditional metadata와 정답 memory가 공개되어 가장 직접적이다.
2. **자연성·외부 검증 — Memora 또는 HaluMem-Medium:** 같은-user 장기 history와 update를 제공하지만 복합 policy gold는 새로 주석해야 한다.
3. **암시적·의존적 갱신 stress test — STALE:** 명시적 부정 없이 이전 memory가 무효화되거나 관련 상태로 전파되는 경우를 제공한다.
4. **동질 다중 충돌 통제군 — MemoryAgentBench/FactConsolidation:** 여러 later-wins fact pair가 있어 `K`는 늘고 policy는 `SUPERSEDE` 하나인 조건을 만들기 좋다.
5. **조건부 외부 검증 — TANGLE:** action 공간은 가장 풍부하지만 2026-08-26 현재 공식 공개 artifact 링크를 확인하지 못해 필수 경로에서는 제외한다.

LongMemEval은 update 문항과 자연스러운 질문 형식 참고에 유용하지만, 서로 다른 persona의 문항을 합쳐서는 안 된다. Mem2ActBench는 구축 과정에서 conflict를 해소하므로 conflict source가 아니라 후속 task-oriented transfer 평가용이다.

### 8.1 메모리 환경의 `K/H/D`

- **Memory conflict cardinality `K`:** 현재 query의 서로 다른 answer/action slot과 관련된 독립 conflict unit 수
- **Memory conflict heterogeneity `H`:** gold response에 필요한 서로 다른 core resolution policy 수
- **Dependency `D`:** 한 상태 변화가 다른 memory의 유효성을 바꾸거나, 한 unit의 해결이 다른 unit의 판단에 영향을 주는 정도

History 전체에 conflict pair가 여러 개 있어도 현재 질문이 한 사실만 묻는다면 query-level `K=1`이다. 데이터셋의 전체 conflict 수와 query-relevant `K`를 혼동하지 않는다.

---

## 9. 논문별 데이터셋 분석

## 9.1 MemConflict

- **논문:** [MemConflict: Evaluating Long-Term Memory Systems Under Memory Conflicts](https://arxiv.org/abs/2605.20926)
- **등재 상태:** arXiv preprint, 2026-05-20 공개
- **공식 데이터·코드:** [TaoZhen1110/MemConflict](https://github.com/TaoZhen1110/MemConflict), 최종 공개 파일 `Data/Step4_4.jsonl`

### 논문이 정의한 문제

장기 memory의 유효성을 query-conditioned fitness-for-use로 보고 세 종류를 구분한다.

| 원 유형 | 유효성 차원 | 본 연구 policy 대응 |
|---|---|---|
| Dynamic conflict | 실제 상태가 시간에 따라 갱신됨 | `SUPERSEDE` |
| Static conflict | 안정된 사실 뒤에 거짓 모순이 등장함 | `VERIFY_PREFER` |
| Conditional conflict | 조건에 따라 선호·값의 적용 범위가 달라짐 | `CONDITION` |

각 instance에는 multi-session history, conflict metadata, query, gold label과 supporting-memory 평가용 필드가 있다. 논문은 긴 history, distractor, implicit query와 먼 conflict distance가 성능을 낮춘다고 보고한다.

### 왜 주 source인가

- 세 policy가 이미 같은 schema와 생성 pipeline 안에 있다.
- persona와 timeline이 유지되므로 서로 다른 사람의 문항을 억지로 붙이지 않고 같은-persona 조합 가능성을 audit할 수 있다.
- answer뿐 아니라 supporting memory gold가 있어 retrieval failure와 resolution failure를 나눌 수 있다.
- 원 benchmark는 대체로 한 query가 한 target attribute와 한 conflict type을 평가하므로 multi-slot action composition이 직접적인 확장점이다.

### 한계와 우리 활용

논문은 controlled simulation, 제한된 유형, nested/overlapping conflict와 더 넓은 query space의 부재를 한계로 둔다. 이는 우리 문제의 직접적인 근거지만 자연 발생 prevalence를 증명하지는 않는다.

먼저 persona별로 다음을 audit한다.

1. 동일 history에 서로 다른 type의 conflict-bearing attribute가 몇 개 있는가?
2. 하나의 생활 과제에서 함께 물을 수 있는 attribute pair가 있는가?
3. 원 claim, timestamp, provenance를 유지한 채 연결 문장과 query만 최소 수정할 수 있는가?

1차 조합은 원 gold에 충실한 `SUPERSEDE + CONDITION`, `SUPERSEDE + VERIFY_PREFER`, `CONDITION + VERIFY_PREFER`로 제한한다. MemConflict만으로 `KEEP_BOTH`와 고위험 `ABSTAIN_QUALIFY`까지 충분히 만든다고 전제하지 않는다.

## 9.2 TANGLE

- **논문:** [When Personal Memory Has No Single Answer: Evaluating LLM Agents under Irreducible Conflict](https://arxiv.org/abs/2608.13921)
- **등재 상태:** arXiv preprint, 2026-08-14 공개
- **규모:** 541 instances, 40 personas
- **공식 데이터·코드:** 2026-08-26 현재 논문에서 공개 artifact 링크를 확인하지 못함. 실행 직전에 재확인 필요

### 논문이 정의한 문제

TANGLE은 더 최신 값을 고르면 끝나는 reducible conflict가 아니라, query에 조건·시점·source authority가 부족해 하나의 정답으로 환원할 수 없는 conflict를 다룬다.

| 원 유형 | 핵심 | 가능한 행동 |
|---|---|---|
| Context-Partitioned Conflict (CPC) | 조건별 선호가 다르지만 query가 조건을 충분히 주지 않음 | conditionalize, clarify |
| Behavior-Oscillation Conflict (BOC) | 행동이 오가며 안정된 최신값을 확정할 수 없음 | verify, defer, reversible trial |
| Source-Contradiction Conflict (SCC) | 서로 다른 source가 양립 불가능한 정보를 줌 | preserve uncertainty, clarify/verify |

CAAP는 `{commit, conditionalize, clarify, verify, defer, reversible_trial}` 중 conflict에 맞는 action을 선택한다. 따라서 “유형을 탐지해 적절한 action으로 routing한다”만으로는 TANGLE과 차별화되지 않는다.

### 우리와의 관계와 한계

각 instance는 한 persona-aspect의 하나의 unresolved slot과 하나의 중심 conflict type을 평가한다. 우리의 차별점은 action 하나의 선택이 아니라, **한 query의 여러 slot에 서로 다른 action을 선택해 서로 모순 없는 한 응답으로 합성하는 것**이다.

같은 persona에 여러 aspect/type이 있어 조합 source로 유망하지만, artifact 확보 전에는 실제 pair 가능성과 license를 확인할 수 없다. 공개되면 irreducible-conflict 외부 검증셋으로 쓰고, 공개되지 않으면 taxonomy와 rubric 참고에만 사용한다.

## 9.3 STALE

- **논문:** [STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?](https://arxiv.org/abs/2605.06527)
- **등재 상태:** arXiv preprint, 2026-05-07 공개
- **공식 데이터·코드:** [icedreamc/STALE](https://github.com/icedreamc/STALE), [Hugging Face dataset](https://huggingface.co/datasets/STALEproj/STALE)
- **규모:** 400 expert-validated scenarios, 1,200 queries, 100개 이상 일상 주제, 최대 150K-token context

### 논문이 정의한 문제

나중 observation이 앞선 memory를 명시적으로 부정하지 않지만 문맥·상식상 무효화하는 **implicit conflict**를 다룬다.

- **Type I, co-referential:** 같은 속성의 뒤 observation이 이전 상태를 암시적으로 갱신한다.
- **Type II, propagated:** 관련 속성의 변화가 기존 belief나 downstream policy를 무효화한다.
- **평가:** State Resolution, Premise Resistance, Implicit Policy Adaptation

논문은 최신 evidence를 retrieval하는 것과 실제 응답·행동을 새 상태에 맞추는 것 사이의 간극을 보이며, 평가된 최고 모델도 전체 55.2%였다.

### 우리 활용과 한계

STALE의 강점은 `D>0`을 직접 stress-test할 수 있다는 점이다. 그러나 각 scenario는 하나의 conflict pair 중심이고 삽입된 LongMemEval distractor는 동일 persona의 별도 conflict unit이 아니다. 따라서 자연스러운 복합 충돌 prevalence 근거로 쓰지 않고 다음 역할로 제한한다.

1. implicit `SUPERSEDE`와 propagation-aware unit의 원자적 source
2. MemConflict 조합에 Type II dependency를 더한 별도 `D>0` stress set
3. retrieval 성공 후 action adaptation이 실패하는지 보는 외부 평가

STALE의 CUPMem이 write-time consolidation과 invalidation을 이미 제안하므로, 우리의 방법 기여는 단일 stale state 갱신이 아니라 query-level multi-policy composition이어야 한다.

## 9.4 Memora

- **논문:** [From Recall to Forgetting: Benchmarking Long-Term Memory for Personalized Agents](https://arxiv.org/abs/2604.20006)
- **등재:** ACL 2026
- **공식 데이터·코드:** [geniesinc/Memora](https://github.com/geniesinc/Memora)

### 논문이 정의한 문제

수주에서 수개월의 사용자 대화에서 remembering, reasoning, recommending을 평가한다. FAMA(Forgetting-Aware Memory Accuracy)는 맞는 정보를 기억하는 것뿐 아니라 삭제되거나 갱신되어 obsolete가 된 memory를 다시 사용하지 않는지도 벌점화한다. 논문은 memory agent들이 invalid memory를 반복 사용하고 evolving memory를 충분히 reconcile하지 못함을 보인다.

### 우리 활용과 한계

실제 장기 사용에 가까운 update·deletion과 downstream recommendation을 볼 수 있어 자연성 검증과 `SUPERSEDE/forget` 외부 전이에 유용하다. 다만 unit별 heterogeneous policy와 action dependency gold를 주지는 않는다.

원 history 안에서 아래를 audit한 뒤 보조 source로 쓴다.

- 하나의 query가 두 개 이상의 updated/deleted memory를 실제로 필요로 하는가?
- update와 stable/conditional preference가 같은 사용자 목표에 연결되는가?
- FAMA의 obsolete-memory annotation을 unit-level forbidden evidence로 변환할 수 있는가?

Memora 자체로 `H>1` prevalence를 주장하지 않고, 자연스러운 장기 update와 행동 형식을 검증하는 역할로 둔다.

## 9.5 HaluMem

- **논문:** [HaluMem: Evaluating Hallucinations in Memory Systems of Agents](https://arxiv.org/abs/2511.03506)
- **등재 상태:** 2025 arXiv/OpenReview manuscript; 확정 학회는 실행 전 재확인
- **공식 데이터·코드:** [MemTensor/HaluMem](https://github.com/MemTensor/HaluMem), [Hugging Face dataset](https://huggingface.co/datasets/IAAR-Shanghai/HaluMem)
- **규모:** Medium/Long 각 20 users, 약 14,948 memory points와 3,467 QA pairs. Medium은 사용자당 약 160K tokens, Long은 약 1M tokens

### 논문이 정의한 문제

Memory-system hallucination을 end-to-end 점수 하나가 아니라 memory extraction, memory updating, memory QA 단계로 나눈다. user-centric 장기 session, persona·event·relationship memory point와 QA의 direct evidence link를 제공한다.

### 우리 활용과 한계

동일 user 안에 많은 session과 update가 있어 같은-persona 복합 query를 찾는 raw source로 유망하다. 그러나 각 update에 `SUPERSEDE`, `CONDITION`, `VERIFY_PREFER` 같은 policy gold가 있는 것은 아니다.

비용이 낮은 **HaluMem-Medium만 먼저 schema audit**한다.

1. update record에서 old/new memory edge와 timestamp를 복원할 수 있는가?
2. 한 user 안에 서로 다른 relation의 query-relevant pair가 있는가?
3. direct evidence link를 유지한 multi-slot query를 만들 수 있는가?
4. consistency filtering이 conflict를 이미 제거하지 않았는가?

조건이 만족되지 않으면 생성 source에서 제외하고 long-context robustness 평가에만 사용한다.

## 9.6 LongMemEval

- **논문:** [LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://arxiv.org/abs/2410.10813)
- **등재:** ICLR 2025
- **공식 데이터·코드:** [xiaowu0162/LongMemEval](https://github.com/xiaowu0162/LongMemEval)
- **규모:** 500개 manually curated questions

### 활용과 한계

Information extraction, multi-session reasoning, temporal reasoning, knowledge update, abstention을 포함해 질문 형식과 장기 retrieval baseline에 유용하다. 그러나 multi-session reasoning은 multi-conflict가 아니며 knowledge-update도 보통 하나의 현재 상태를 묻는다. 서로 다른 item은 사용자 배경이 다를 수 있으므로 결합하지 않는다.

- MemConflict multi-goal query가 실제 assistant 질문과 비슷한지 비교한다.
- 원 knowledge-update 문항은 `K=1,H=1` 외부 baseline으로만 쓴다.

## 9.7 MemoryAgentBench / FactConsolidation

- **논문:** [Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions](https://arxiv.org/abs/2507.05257)
- **등재:** ICLR 2026
- **공식 데이터·코드:** [HUST-AI-HYZ/MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench)

### 데이터 구성

FactConsolidation은 MQUAKE의 counterfactual edit pair를 사용한다. 각 pair는 원래 사실과 나중에 등장한 모순된 수정 사실이며, 여러 pair를 이어 6K, 32K, 64K, 262K context를 만든다. Single-Hop과 Multi-Hop 질문 모두 나중 정보를 우선하도록 명시한다.

### 우리 활용과 한계

모든 conflict가 같은 `SUPERSEDE` policy라 `H>1` source로는 부적합하다. 대신 길이와 query-relevant conflict 수를 늘리면서 policy는 하나로 고정하는 **`K>1,H=1` 통제군**에 적합하다.

긴 context에 pair가 여러 개 있다는 이유만으로 query-level `K>1`이라 하지 않는다. 질문이 실제로 둘 이상의 edit pair를 함께 요구할 때만 `K`로 센다.

## 9.8 Mem2ActBench

- **논문:** [Mem2ActBench: A Benchmark for Evaluating Long-Term Memory Utilization in Task-Oriented Autonomous Agents](https://aclanthology.org/2026.acl-long.370/)
- **등재:** ACL 2026 Long Paper
- **공식 데이터·코드:** [Cantaloupe-M/Mem2ActBench](https://github.com/Cantaloupe-M/Mem2ActBench)
- **규모:** 2,029 sessions, 400 tool-use tasks

### 활용과 제외 이유

개인 선호와 task state를 tool action에 적용하는 평가라 최종 downstream 목표와 맞는다. 그러나 구축 과정에서 conflict를 해소해 globally consistent evolution chain을 만들기 때문에 원본은 memory-conflict source가 아니다. 파일럿 2에서는 제외하고, 추후 controlled conflict 주입 후 action parameter별 policy compliance를 평가하는 transfer set으로만 고려한다.

---

## 10. 데이터셋 비교와 우선순위

| 데이터셋 | 공개 상태 | 동일 persona 장기 history | 원 conflict/action gold | 원 query `H>1` | 파일럿 2 역할 | 우선순위 |
|---|---|---:|---:|---:|---|---:|
| MemConflict | 공개 | 예 | 세 유형, supporting memory | 아니오 | 주 구성 source | 1 |
| Memora | 공개 | 예 | update/deletion, obsolete-memory 평가 | 아니오 | 자연성·외부 검증 | 2 |
| HaluMem-Medium | 공개 | 예 | update/evidence, policy gold 불명확 | 아니오 | schema audit 후 보조 source | 3 |
| STALE | 공개 | scenario 단위 | implicit type과 세 probe | 아니오 | `D>0` stress test | 4 |
| FactConsolidation | 공개 | 개인 memory 아님 | later-wins edit pair | 아니오 | `K>1,H=1` 통제 | 5 |
| TANGLE | 공개 artifact 미확인 | 논문상 예 | type과 action rubric | 아니오 | 확보 시 외부 검증 | 조건부 |
| LongMemEval | 공개 | item 단위 history | update/temporal QA | 아니오 | 질문 형식·single-unit transfer | 보조 |
| Mem2ActBench | 공개 | 예 | conflict는 구축 중 해소 | 아니오 | 후속 action transfer | 제외 |

### 10.1 빠른 파일럿의 현실적 최소 구성

1. **MemConflict audit:** persona별 type/attribute 분포와 자연스러운 pair 후보를 계산한다.
2. **MemConflict matched set:** `K=2,H=1` 24개와 `K=2,H=2` 24개를 같은 persona·길이·slot 수로 맞춘다.
3. **STALE stress set:** Type II를 포함한 `D=0/D>0` 각 10~20개로 dependency 효과만 별도 확인한다.
4. **Memora/HaluMem-Medium 중 하나만 외부 검증:** schema audit 결과 자연 pair가 더 많은 쪽을 선택한다.
5. **FactConsolidation 통제:** later-wins policy만 반복될 때 `K` 증가와 `H` 증가 효과를 분리한다.

TANGLE은 artifact가 확보되면 우선적인 irreducible-conflict 외부 검증으로 승격하지만 일정의 필수 경로에는 두지 않는다.

---

## 11. 직접 지지되는 주장과 아직 검증할 주장

### 11.1 지금 직접 주장할 수 있는 것

- MemConflict는 temporal, factual, contextual validity가 서로 다른 memory conflict임을 보이고 시스템 강점이 유형별로 불균일함을 보고한다.
- TANGLE은 모든 personal-memory conflict가 단일 정답으로 환원되지 않으며 fixed rule보다 conflict-conditioned action이 필요함을 보인다.
- STALE은 updated evidence retrieval과 downstream behavior 수정이 별개이고 implicit propagation이 어렵다는 것을 보인다.
- Memora는 obsolete memory 재사용과 evolving-memory reconciliation 실패가 장기 평가에서 문제임을 보인다.
- 대표 공개 benchmark의 query는 주로 하나의 target attribute/aspect 또는 하나의 중심 policy를 평가한다.

### 11.2 파일럿 전에는 주장하면 안 되는 것

- 실제 사용자의 한 요청에서 `K>1,H>1` memory conflict가 흔하다.
- MemConflict의 같은 persona 안에 자연스럽게 결합할 서로 다른 유형이 충분히 많다.
- HaluMem update record만으로 unit별 policy gold를 안정적으로 복원할 수 있다.
- `H` 증가가 길이·slot 수를 통제한 뒤에도 성능 저하의 원인이다.
- graph 또는 plan-search가 CoT보다 항상 낫다.

파일럿이 입증할 최소 주장은 **공개 memory history에서 자연스러운 heterogeneous composition을 구성할 수 있고, 동일 `K`에서 heterogeneous policy가 homogeneous policy와 다른 오류를 만든다**는 것이다.

---

## 12. 파일럿 2 데이터 결정 규칙

### 12.1 Go 조건

1. MemConflict 동일-persona history에서 최소 40개의 자연스러운 `K=2,H=2` 후보를 만들 수 있다.
2. 연구자 검토 후 최소 24개 matched pair가 자연성·gold 보존 기준을 통과한다.
3. 최소 세 policy 조합 중 둘 이상에서 사례를 확보한다.
4. `K=2,H=2`가 `K=2,H=1`보다 all-unit success 또는 policy-collapse rate에서 일관된 악화를 보인다.
5. oracle unit/policy를 주면 성능이 회복되어 실패가 단순 정보 부족만은 아님을 보인다.

### 12.2 축소·전환 조건

- 서로 다른 type은 많지만 한 goal로 묶기 부자연스러우면 **multi-query memory batch resolution**로 축소한다.
- `H>1` 효과가 없고 `D>0`에서만 실패하면 **dependency-aware stale-memory resolution**로 좁힌다.
- controlled 조합만 가능하면 “현실에서 흔하다”는 주장을 버리고 **compositional stress benchmark**로 명시한다.
- HaluMem·Memora에서도 mixed-policy pair가 거의 없으면 prevalence가 아니라 benchmark blind spot과 worst-case reliability를 기여로 삼되 주장 강도를 낮춘다.

### 12.3 최종 권고

파일럿 2는 **MemConflict로 controlled matched set을 만들고, Memora/HaluMem 중 하나로 자연성을 보강하며, STALE과 FactConsolidation으로 `D`와 `K` 통제축을 분리**하는 구성이 가장 방어 가능하다. 각 데이터셋이 잘 주석한 현상만 가져와 가설별 역할을 분리해야 한다.
