# 다중·복합 충돌 데이터셋 논문 분석과 연구 주장 논리

> 작성일: 2026-08-26
> 범위: 기존 보유 데이터의 실제 재집계가 아니라, 다중 충돌 관련 데이터셋 논문이 문제를 어떻게 정의하고 필요성을 입증하는지 분석한다.
> 목적: 활용할 데이터셋을 먼저 선정하고, 이후 prevalence audit과 방법 실험으로 검증할 연구 주장을 확정한다.

---

## 1. 결론부터

다중 충돌 관련 데이터셋은 존재하지만, 논문마다 “다중”의 의미가 다르다.

1. **여러 요인의 동시 존재:** RAMDocs의 ambiguity + misinformation + noise
2. **모순 위치의 개수 증가:** MAGIC의 1~4 conflict locations
3. **복수 답·관점 cluster:** QACC·ConfRAG·GroupQA
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

## 2.5 ConfRAG

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

## 2.6 GroupQA

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

## 2.7 Ragability

- 논문: [Ragability Benchmark](https://aclanthology.org/2026.lrec-1.182/)
- 등재: LREC 2026
- 다중 충돌의 의미: 직접 표현되지 않고 두 문맥을 함께 추론해야 드러나는 implicit inter-context conflict

현재 모델은 “모순이 있는가?” 같은 binary 질문에는 비교적 답하지만, 실제 내용을 묻는 QA에서는 충돌을 적절히 반영하지 못한다. 이는 detection 성공이 resolution 성공을 보장하지 않는다는 근거다.

주요 활용은 implicit-relation detector와 no-conflict gate 검증이며, 복수 action composition의 주 데이터셋으로는 적합하지 않다.

## 2.8 ContraPRT / Cross-Validated Re-ranking

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

## 2.9 DRUID와 CONFACT: 간접적인 현실성 근거

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
| CONFLICTS/DRAGged | O | X, conflict-enriched sampling | instance-level 단일 type | **O** | type별 behavior | **다양한 action과 재주석 후보** |
| ConfRAG | O | X, controversy-filtered | 2~8 answer/reason clusters | 관점 보존 중심 | cluster gold | external multi-view test |
| MAGIC | KG 기반 synthetic text | X | 1~4 locations, single/multi-hop | X | conflict spans | detector/localizer stress test |
| GroupQA | O | X, 양측 evidence 필수 | stance별 여러 documents | 단일 arbitration | stance·strength | duplication/order stress test |
| Ragability | 사례 기반 후 entity 치환 | X | implicit relation | 제한적 | conflict 여부 | implicit gate test |
| ContraPRT | 구성형 | X | 한 pair에 복수 linguistic/logical aspects | 모든 type을 제거로 처리 | multi-type aspect | multi-label 가능성·taxonomy 참고 |
| DRUID | O | 일부 현실 분포 | 한 evidence의 복수 context properties | 직접 action 없음 | stance·properties | 단일 속성 가정 비판 |
| CONFACT | O | conflict-likely claim에서 17.8% 자동 선별 | stance+credibility+imbalance | factual select | stance·credibility | 실제 factual conflict 보조 검증 |

### 2026년 10월 ARR을 고려한 현실적 구성

필수 세트:

1. **RAMDocs:** 이미 mixed-factor resolution과 MADAM-RAG baseline이 있어 직접 비교 가능
2. **QACC:** 충돌의 자연 발생성과 factual adjudication을 뒷받침
3. **CONFLICTS/DRAGged:** temporal·opinion·complementary 등 action 다양성을 확보

시간이 허용될 때 external set:

4. **ConfRAG:** multi-view clustering·reason coverage 일반화
5. **MAGIC:** conflict count·hop에 따른 localization 일반화
6. **GroupQA:** repetition·order counterfactual robustness

새 데이터 전체를 처음부터 구축하기보다 기존 세 데이터에 공통 claim-relation-action annotation layer를 얹는 편이 현실적이다. 다만 실제 annotation 규모는 별도의 prevalence pilot 이후 결정한다.

---

## 4. 문헌에서 직접 지지되는 주장과 지지되지 않는 주장

### 4.1 지금 직접 주장할 수 있는 것

**주장 A — conflicting retrieval은 드문 synthetic corner case가 아니다.**
QACC는 명확한 open-domain question의 약 25%에서 Google top-10 contexts가 서로 다른 답을 포함한다고 보고했다.

**주장 B — conflict set은 흔히 둘 이상의 후보를 포함한다.**
QACC conflict subset은 평균 2.47개 답을 가지며, ConfRAG은 질문당 2~8개의 answer clusters를 제공한다.

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

1. QACC·CONFLICTS·ConfRAG의 한 instance에 둘 이상의 claim relation type이 실제로 나타나는가?
2. 둘 이상의 서로 다른 action이 필요한 instance 비율은 얼마인가?
3. action들이 단순 병렬 적용 가능한가, 아니면 dependency·order가 필요한가?
4. mixed-action 사례가 모델의 정답률·coverage·attribution을 실제로 더 낮추는가?
5. RAMDocs의 controlled composition에서 발견한 실패가 natural web 사례에서도 재현되는가?
6. 자동 relation detector 오류를 제외한 oracle-action 조건에서도 composition failure가 존재하는가?

이 질문에 답한 뒤에만 prevalence와 order-sensitive resolution을 논문의 강한 empirical claim으로 사용한다.
