# Reference 논문: 문제 정의·해결 방법·한계 정리

> 작성일: 2026-08-25
> 최종 갱신: 2026-08-26
> 대상: 저장소 `literature/papers/`에 포함된 7편 + 복합 충돌 주제 검토 중 추가로 확인한 최근 인접 연구
> 목적: 새로운 연구 주제를 먼저 정하지 않고, 각 논문이 실제로 해결하려는 문제와 해결 접근, 남은 한계를 공통 기준으로 정리한다.

---

## 0. 읽는 방법

이 문서는 한계를 두 종류로 구분한다.

- **명시적 한계:** 저자가 Limitations, Conclusion 또는 분석에서 직접 언급한 범위
- **방법론상 잔여 한계:** 논문의 문제 설정·알고리즘·평가 범위를 비교해 도출한 공백. 저자가 직접 주장한 문장으로 취급하지 않는다.

또한 conflict라는 표현이 논문마다 다른 대상을 가리키므로 다음 세 범위를 구분한다.

| 충돌 범위 | 정의 | 예시 |
|---|---|---|
| Context–memory conflict | 검색 문서와 모델의 parametric knowledge가 충돌 | 모델 기억은 A, 검색 문서는 B |
| Inter-context conflict | 검색된 외부 문서들이 서로 충돌 | 문서 1은 A, 문서 2는 B |
| Composite conflict | ambiguity·misinformation·noise 등이 함께 존재 | 복수의 유효 답, 오정보, 무관 문서가 동시 존재 |

---

## 1. 전체 비교표

### 1.1 등재·공개 정보

| 논문 | 출판 상태 | 학회·트랙 | 개최·출판 시점 | 장소·비고 |
|---|---|---|---|---|
| Self-RAG | 정식 학회 논문 | ICLR 2024 | 2024-05-07~11 | Vienna, Austria; arXiv 최초 공개 2023-10-17 |
| Tug-of-War Between Knowledge | 정식 학회 논문 | LREC-COLING 2024 Main | 2024-05-20~25 | Torino, Italy; main conference 05-22~24 |
| COIECD | 정식 학회 논문 | Findings of ACL 2024 | 2024-08 | ACL 2024 Bangkok, 08-11~16; pp. 3903–3922 |
| FaithfulRAG | 정식 장편 논문 | ACL 2025 Main Conference, Long Paper | 2025-07-27~08-01 | Vienna, Austria; pp. 21863–21882 |
| Retrieval-Augmented Generation with Conflicting Evidence | 정식 학회 논문 | COLM 2025 | 2025-10-07~10 | Montréal, Canada; arXiv 최초 공개 2025-04-17 |
| Conflict-Aware RAG | 정식 학회 논문 | The Web Conference 2026 Research Track | proceedings 2026-04; 학회 2026-06-29~07-03 | Dubai, UAE; 원래 04-13~17에서 일정 변경; pp. 2114–2125 |
| ConflictRAG | preprint | arXiv | 2026-05-17 최초 공개 | 확인 시점 기준 정식 학회 등재를 확인하지 못함 |

학회명에서 ACL Main과 Findings는 구분한다. COIECD는 ACL 2024와 함께 출판됐지만 **ACL Main이 아니라 Findings of ACL 2024**이고, ConflictRAG은 다른 여섯 편과 달리 현재 확인 가능한 상태가 **arXiv preprint**다.

### 1.2 문제·방법 비교

| 논문 | 주된 문제 | 주요 충돌 범위 | 해결 접근 | 학습 필요 | logits/내부 접근 | 핵심 잔여 한계 |
|---|---|---|---|:---:|:---:|---|
| Self-RAG | 무조건 검색·무비판 생성 | 일반 RAG, 직접적인 inter-context 전용 아님 | retrieval·generation·critique reflection token | O | 불필요 | 학습 의존, retrieval 품질 의존, 충돌 전용 판정 부재 |
| Tug-of-War / CD² | 내부 기억·외부 문서 및 외부 evidence 간 편향 | context–memory + inter-context | conflict-disentangled contrastive decoding | X | O | black-box 적용 불가, 모델 행동·confidence 중심 |
| COIECD | conflict decoding이 no-conflict 성능까지 손상 | 주로 context–memory | contextual entropy 기반 adaptive decoding | X | O | QA 한정, 약 2배 decoding 비용, 원인 문서 국소화 부족 |
| FaithfulRAG | 생성이 검색 문맥과 불일치 | fact-level context conflict | self-fact mining + fact alignment + self-think | X | X | context faithfulness와 correctness의 차이, extraction 오류 전파 |
| RAMDocs / MADAM-RAG | ambiguity·misinformation·noise의 동시 처리 | composite inter-context | 문서별 agent debate + aggregator | X | X | 높은 inference cost, evidence imbalance에 취약, 합의 신뢰성 |
| Conflict-Aware RAG | web evidence conflict가 RAG 학습·검색·생성을 오염 | 주로 inter-context | ConScore 기반 SFT→DPO→reranking | O | 학습 시 확률 접근 | 다단계 학습 비용, 새 도메인 이전, test-time 적응 제한 |
| ConflictRAG | 문서 충돌을 generation 전에 명시적으로 처리하지 않음 | inter-context 중심 | detect→classify→resolve→generate | detector 학습 | 일부 불필요 | 초기 detector 오류 전파, credibility와 truth의 차이, pipeline 복잡도 |

---

## 2. 해결 접근 방법론 유형

### 2.1 학습 기반 통합 정렬

대표: **Self-RAG, Conflict-Aware RAG**

#### 공통 원리

모델이 검색 필요성, 문서 적합성, 충돌 신호 또는 답–근거 정합성을 학습하도록 파라미터를 갱신한다.

```text
학습 데이터 또는 critic 신호
        ↓
SFT / DPO / 특수 token / alignment module
        ↓
추론 시 검색·문서 사용·생성 행동 변화
```

#### 장점

- 반복되는 충돌 처리 행동을 모델 안에 내재화할 수 있다.
- 매 문항마다 복잡한 agent pipeline을 실행하지 않아도 된다.
- retriever·generator를 공동 최적화할 수 있다.

#### 공통 한계

- 학습 데이터와 critic 품질에 의존한다.
- backbone이나 도메인이 바뀌면 재학습 또는 재정렬이 필요하다.
- 학습 후 정확도 향상이 실제 충돌 해소에서 왔는지 해석하기 어렵다.
- 현재 연구 목표인 학습 없는 해결과 직접 맞지 않는다.

---

### 2.2 Decoding-time 확률 보정

대표: **CD², COIECD**

#### 공통 원리

서로 다른 조건에서 얻은 token probability 또는 logits를 비교해 internal memory나 잘못된 context의 영향을 억제한다.

```text
전체/문맥 조건 logits
        ↕ 대비
내부 기억 또는 대조 조건 logits
        ↓
다음 token score 재보정
```

#### 장점

- 별도 fine-tuning 없이 즉시 적용할 수 있다.
- token 생성 단계에 직접 개입하므로 효과가 명확하다.
- prompt-only 방법보다 강한 제어가 가능하다.

#### 공통 한계

- open-weight 또는 logits 접근이 필요하다.
- 두 개 이상의 forward/decoding 경로 때문에 비용이 증가한다.
- 어느 외부 문서가 참인지 판단하기보다 context를 얼마나 따를지를 조정하는 경우가 많다.
- context–memory conflict와 inter-context conflict가 동일한 분포 대비로 해결된다고 보장할 수 없다.

---

### 2.3 Fact-level 분해와 정합

대표: **FaithfulRAG**

#### 공통 원리

문서 전체를 하나의 단위로 평가하지 않고, 모델의 self-fact와 검색 문서의 fact를 추출한 뒤 사실 단위로 충돌을 찾고 정렬한다.

```text
질문·모델 지식 → self facts
검색 문서       → contextual facts
                      ↓
             관련 fact 정렬·충돌 판정
                      ↓
                 grounded generation
```

#### 장점

- 문서 안에 올바른 사실과 틀린 사실이 섞인 경우를 다룰 수 있다.
- document-level relevance보다 세밀하다.
- 생성 답의 어떤 claim이 어떤 문서 fact와 연결되는지 설명하기 쉽다.

#### 공통 한계

- fact extraction·segmentation 오류가 이후 단계로 전파된다.
- 모델 self-fact를 기준으로 사용하면 기존 parametric bias가 재도입될 수 있다.
- 틀린 문서에 충실한 답도 context-faithful로 평가될 수 있다.
- 복수 문서가 부분적으로 맞거나 multi-hop support가 필요한 경우 alignment가 복잡하다.

---

### 2.4 Agentic deliberation과 aggregation

대표: **MADAM-RAG**

#### 공통 원리

각 문서 또는 후보 답을 별도 agent가 처리하고, 여러 agent가 토론한 뒤 aggregator가 유효 답·오정보·noise를 구분한다.

```text
문서 1 → agent 1 ┐
문서 2 → agent 2 ├→ multi-round debate → aggregator → 답
문서 3 → agent 3 ┘
```

#### 장점

- 문서를 처음부터 한 prompt에 섞을 때 발생하는 간섭을 줄인다.
- ambiguity처럼 복수 답을 보존해야 하는 경우에 적합하다.
- black-box LLM에도 적용할 수 있다.

#### 공통 한계

- 문서 수와 토론 라운드에 따라 비용과 latency가 증가한다.
- 같은 backbone agent들은 같은 편향과 오류를 공유할 수 있다.
- 토론이 진실보다 설득력·verbosity·majority를 강화할 수 있다.
- aggregator의 합의가 실제 올바른 evidence resolution인지 별도로 검증해야 한다.

---

### 2.5 사전 탐지·분류·유형별 해결 pipeline

대표: **ConflictRAG**

#### 공통 원리

생성 모델에 상충 문서를 그대로 주기 전에 conflict를 탐지하고 유형화한 뒤, factual·temporal·opinion 등에 맞는 해결 규칙을 적용한다.

```text
retrieval
   ↓
conflict detection
   ↓
type classification
   ↓
type-adaptive resolution
   ↓
generation + attribution
```

#### 장점

- 어느 단계가 실패했는지 모듈별로 추적하기 쉽다.
- conflict 유형별로 서로 다른 행동을 적용할 수 있다.
- conflict가 없는 경우 불필요한 복잡한 처리를 피할 수 있다.

#### 공통 한계

- detection 또는 classification 오류가 이후 단계 전체에 전파된다.
- source credibility는 특정 claim의 진실성과 동일하지 않다.
- 여러 모듈의 threshold와 prompt를 관리해야 한다.
- 복수 유형이 겹치거나 부분적으로만 올바른 문서에는 hard type routing이 불안정하다.

---

### 2.6 Conflict signal 기반 다단계 RAG 최적화

대표: **Conflict-Aware RAG**

#### 공통 원리

모델이 느끼는 conflict signal을 단순 진단에 쓰지 않고 학습 데이터 선택, preference optimization, retrieval reranking까지 연결한다.

```text
ConScore
   ├→ SFT용 distracting document 선택
   ├→ DPO preference pair 구성
   └→ conflict confidence + information gain reranking
```

#### 장점

- generator만 수정하지 않고 RAG pipeline 여러 단계에 conflict 정보를 반영한다.
- 학습과 retrieval을 함께 개선할 수 있다.
- 단일 prompt나 decoding trick보다 체계적이다.

#### 공통 한계

- 여러 학습 단계와 데이터 구축 비용이 필요하다.
- conflict signal이 잘못되면 학습 데이터와 preference pair도 오염된다.
- 새 모델·새 corpus에 빠르게 적용하기 어렵다.
- test-time에서 처음 보는 충돌 구조에 동적으로 대응하는 기능은 제한적이다.

---

### 2.7 행동 분석과 평가 프레임

대표: **Tug-of-War의 분석 부분, RAMDocs benchmark 부분**

#### 공통 원리

충돌 evidence의 개수, 비율, relevance, 내부 기억과의 일치 여부를 조절해 모델의 선택 편향과 성능을 측정한다.

#### 대표적으로 드러난 현상

- parametric knowledge에 대한 고집
- common knowledge에 대한 availability bias
- 반복 evidence를 따르는 majority rule
- 내부 기억과 일치하는 문서를 선호하는 confirmation bias
- supporting evidence와 misinformation의 imbalance가 커질수록 성능 악화

#### 공통 한계

- 최종 accuracy와 confidence만으로는 어느 추론 단계에서 실패했는지 알기 어렵다.
- 맞은 답이 실제 문서 비교에서 나온 것인지 parametric memory·우연인지 구분하기 어렵다.
- 특정 완화법의 성능 상승이 legitimate resolution 증가인지 판단하기 어렵다.

---

## 3. 논문별 상세 정리

## 3.1 Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection

### 서지 정보

- 등재: **The Twelfth International Conference on Learning Representations (ICLR 2024)**
- 개최: **2024-05-07~11**, Vienna, Austria
- 최초 공개: arXiv **2023-10-17**
- 상태: 정식 학회 논문

### 해결하려는 문제

일반 RAG는 다음과 같은 고정 행동을 한다.

- 검색이 필요하지 않은 질문에도 항상 검색한다.
- 검색 문서가 관련 있는지 판단하지 않고 사용한다.
- 생성 답이 문서에 의해 지지되는지 자체적으로 검사하지 않는다.
- 고정된 수의 문서를 일률적으로 사용한다.

Self-RAG의 핵심 문제는 직접적인 문서 간 conflict라기보다 **수동적이고 무비판적인 RAG generation**이다.

### 해결 방법

모델이 다음 reflection token을 생성하도록 학습한다.

- Retrieve: 현재 시점에 검색이 필요한가?
- ISREL: 검색 passage가 질문에 관련 있는가?
- ISSUP: 생성 내용이 passage에 의해 지지되는가?
- ISUSE: 생성 답이 과제에 유용한가?

추론 시 여러 passage별 continuation을 생성하고 reflection score와 generation probability를 결합해 선택한다.

### 접근 유형

- 학습 기반 self-reflection
- adaptive retrieval
- passage-level critique
- segment-level beam/tree decoding

### 명시적 한계

- underlying retriever의 품질에 의존한다.
- 특수 reflection token 생성을 위한 모델 학습이 필요하다.
- prompting만으로 세밀한 reflection signal을 안정적으로 얻기 어렵다.
- 평가가 주로 Wikipedia 기반 knowledge-intensive task에 집중되어 있다.

### 방법론상 잔여 한계

- 상충 문서 중 어느 것이 맞는지 판정하는 conflict-specific token이 없다.
- passage별 독립 support 점수가 문서 간 contradiction을 직접 나타내지 않는다.
- self-critique와 generation이 같은 모델에 의존해 자기확증 오류가 생길 수 있다.
- 답이 맞지만 근거 선택이 틀린 경우를 충분히 구분하지 않는다.

---

## 3.2 Tug-of-War Between Knowledge / Conflict-Disentangle Contrastive Decoding

### 서지 정보

- 등재: **LREC-COLING 2024 Main Conference**
- 개최: 전체 일정 **2024-05-20~25**, Torino, Italy; main conference 05-22~24
- 출판: Proceedings of the 2024 Joint International Conference on Computational Linguistics, Language Resources and Evaluation, pp. 16867–16878
- 상태: 정식 학회 논문

### 해결하려는 문제

RAG 모델은 다음 두 종류의 충돌에서 체계적 편향을 보인다.

1. internal memory와 external evidence의 충돌
2. truthful·irrelevant·misleading external evidence의 공존

논문은 모델 크기, 내부 confidence, entity popularity, evidence 수와 비율에 따라 어떤 지식을 선택하는지 분석한다.

### 주요 발견

- 강한 모델이 잘못된 내부 기억을 더 고집할 수 있다.
- 익숙하고 흔한 지식에 availability bias를 보인다.
- 더 많이 반복된 evidence를 따르는 majority rule이 나타난다.
- 내부 기억과 일치하는 외부 evidence를 선호한다.

### 해결 방법: CD²

내부 지식과 외부 문맥의 효과를 서로 다른 decoding 조건으로 분리한 뒤 contrastive score로 token probability를 재보정한다. 목표는 모델이 높은 confidence로 잘못된 내부 기억이나 misleading context를 따르는 것을 완화하는 것이다.

### 접근 유형

- 행동·편향 평가
- inference-time contrastive decoding
- logits calibration

### 명시적 한계

- 분석이 주로 모델 성능과 confidence score에 집중되어 있다. 내부 mechanism 분석은 후속 과제로 남긴다.
- output logits에 접근할 수 없는 black-box LLM에는 CD²를 적용할 수 없다.

### 방법론상 잔여 한계

- confidence 보정이 어느 문서가 사실인지에 대한 외부 검증을 제공하지 않는다.
- 문서별로 부분적으로 맞는 inter-context conflict에는 단순 분리가 어려울 수 있다.
- 최종 답 정확도 향상이 올바른 문서 선택에서 왔는지 별도로 확인하지 않는다.

---

## 3.3 COIECD: Contextual Information-Entropy Constraint Decoding

### 서지 정보

- 등재: **Findings of the Association for Computational Linguistics: ACL 2024**
- 출판: **2024-08**, pp. 3903–3922
- 연계 학회: ACL 2024, **2024-08-11~16**, Bangkok, Thailand
- 상태: 정식 Findings 논문. ACL Main Conference 논문으로 표기하지 않는다.

### 해결하려는 문제

기존 contrastive decoding은 knowledge conflict가 있을 때는 도움을 줄 수 있지만, conflict가 없는 문항에도 계속 적용하면 원래 모델 성능을 손상할 수 있다.

즉 핵심 문제는 다음과 같다.

> conflict가 있는 경우에만 context-faithful decoding을 강화하고, conflict가 없는 경우에는 원래 decoding을 보존할 수 있는가?

### 해결 방법

문맥 유무에 따른 contextual information entropy를 이용해 conflict 여부와 정도를 추정하고, 그 신호에 따라 decoding 보정 강도를 적응적으로 조절한다.

### 접근 유형

- training-free adaptive decoding
- entropy-based conflict signal
- context–memory balance

### 명시적 한계

- QA에서만 평가했으며 summarization 같은 다른 context-intensive task로 확장하지 않았다.
- 두 decoding operation이 필요해 계산 자원이 약 2배 든다.

### 방법론상 잔여 한계

- entropy는 충돌 가능성을 나타내지만 어떤 문서와 claim이 원인인지 바로 알려주지 않는다.
- 문맥 전체와 parametric memory의 충돌에는 적합하지만 여러 외부 문서 사이의 truth adjudication은 별도 문제다.
- entropy가 높다는 이유만으로 외부 문맥이 옳다고 볼 수 없다.

---

## 3.4 Faithful Retrieval-Augmented Generation via Self-Fact Alignment

### 서지 정보

- 정식 제목: **FaithfulRAG: Fact-Level Conflict Modeling for Context-Faithful Retrieval-Augmented Generation**
- 등재: **Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics, ACL 2025 Main Conference, Long Paper**
- 개최: **2025-07-27~08-01**, Vienna, Austria
- 출판: pp. 21863–21882, DOI 10.18653/v1/2025.acl-long.1062
- 상태: 정식 ACL Main 장편 논문

### 해결하려는 문제

RAG가 관련 문서를 검색해도 생성 모델은 자신의 기존 지식이나 일부 문서 fact를 혼합해 문맥과 맞지 않는 답을 생성할 수 있다. document-level relevance만으로는 어느 사실이 충돌하는지 세밀하게 다루기 어렵다.

### 해결 방법

- 질문에 대한 모델의 self-fact 추출
- 검색 문서에서 관련 contextual fact 추출
- self-fact와 contextual fact 사이의 충돌·정렬
- 정렬 결과에 근거한 context-faithful generation

### 접근 유형

- fact-level decomposition
- self-knowledge elicitation
- contextual knowledge alignment
- faithful generation

### 명시적 한계

저장된 원문에서는 독립 Limitations 절보다 방법과 실험 범위에서 제약이 드러난다. 따라서 아래 항목은 주로 방법론상 잔여 한계로 분류한다.

### 방법론상 잔여 한계

- self-fact 추출이 잘못되면 이후 conflict modeling이 오염된다.
- context faithfulness는 correctness와 다르다. 틀린 검색 문서에 충실할 수 있다.
- 여러 문서가 서로 다른 부분에서 맞는 경우 fact alignment가 복잡하다.
- 모델의 최초 self-fact를 중심에 두면 confirmation bias가 재도입될 수 있다.
- fact extraction과 alignment에 필요한 추가 모델 호출·계산 비용이 존재한다.

---

## 3.5 Retrieval-Augmented Generation with Conflicting Evidence / RAMDocs / MADAM-RAG

### 서지 정보

- 등재: **Conference on Language Modeling (COLM 2025)**
- 개최: **2025-10-07~10**, Montréal, Canada; main conference 10-07~09, workshop 10-10
- 최초 공개: arXiv **2025-04-17**
- 상태: 정식 학회 논문

### 해결하려는 문제

기존 연구는 ambiguity, misinformation, irrelevant noise를 각각 따로 평가하는 경우가 많다. 실제 RAG에서는 이 세 요인이 동시에 나타난다.

- ambiguity: 질문에 여러 유효 해석·답이 존재
- misinformation: 그럴듯하지만 잘못된 문서가 포함
- noise: 질문과 무관한 문서가 포함

RAMDocs는 이 요인을 결합한 평가 환경이고, MADAM-RAG은 이를 함께 처리하려는 방법이다.

### 해결 방법: MADAM-RAG

- 각 문서 또는 답 후보를 agent가 독립적으로 검토
- 여러 라운드 debate로 후보의 장단점 비교
- aggregator가 ambiguous entity별 유효 답을 모으고 misinformation·noise를 제거

### 접근 유형

- composite-conflict benchmark
- document-conditioned multi-agent reasoning
- multi-round debate
- answer aggregation

### 명시적 한계·잔여 격차

- RAMDocs는 기존 RAG에 매우 어렵고 절대 성능이 낮다.
- MADAM-RAG도 supporting evidence와 misinformation의 imbalance가 커질수록 큰 성능 격차가 남는다.
- 다중 agent·다중 round로 inference cost가 높다.

### 방법론상 잔여 한계

- 같은 모델을 복제한 agent는 서로 독립적인 오류를 낸다고 보기 어렵다.
- debate가 사실성보다 설득력과 verbosity를 강화할 수 있다.
- 반복된 misinformation이 agent 수 또는 주장 수를 지배할 수 있다.
- aggregator가 올바른 근거를 사용했는지 최종 답만으로는 알기 어렵다.

---

## 3.6 Conflict-Aware RAG: Multi-Stage Learning with Conflict Signals

### 서지 정보

- 등재: **The ACM Web Conference 2026, Research Track (WWW 2026)**
- proceedings 공개: **2026-04**, ACM; 논문 publication history 기준 2026-04-12
- 학회 개최: **2026-06-29~07-03**, Dubai, UAE. 원래 04-13~17 일정에서 변경됨.
- 출판: pp. 2114–2125, DOI 10.1145/3774904.3792289
- 상태: 정식 학회 논문

### 해결하려는 문제

다양한 web 문서를 결합할 때 서로 충돌하거나 방해되는 정보가 generator뿐 아니라 training data 구성과 retrieval–generation 협업까지 오염시킨다. 기존 방법은 conflict를 최종 생성 단계에서만 처리하는 경우가 많다.

### 해결 방법

모델이 서로 다른 knowledge source에 보이는 생성 확률 차이로 **ConScore**를 계산하고, 이를 전체 RAG optimization에 사용한다.

1. SFT: conflict signal을 이용해 대표적인 distracting document를 선택
2. DPO: conflict-aware preference pair 구성
3. Reranking: conflict confidence와 information gain을 함께 사용

### 접근 유형

- learned conflict signal
- multi-stage training
- preference optimization
- conflict-aware reranking

### 논문이 주장한 장점

- conflict signal을 데이터 구축부터 retrieval·generation까지 일관되게 활용
- 여러 QA dataset에서 안정성과 일반화 성능 개선
- 단일 module이 아닌 RAG 시스템 수준 최적화

### 방법론상 잔여 한계

- SFT와 DPO, reranking을 모두 수행해야 해 자원 요구량이 높다.
- ConScore가 잘못되면 selection과 preference data가 함께 오염된다.
- 새로운 backbone·corpus·domain에 이전할 때 재학습 비용이 든다.
- test-time에서 새로운 conflict 구조를 발견하고 계산량을 조절하는 방식은 아니다.
- 성능 향상이 실제 conflict reasoning 개선인지 shortcut인지 직접 분해하지 않는다.

---

## 3.7 ConflictRAG: Detecting and Resolving Knowledge Conflicts

### 서지 정보

- 공개: **arXiv preprint**, arXiv:2605.17301
- 최초 공개: **2026-05-17**
- 확인 시점: 2026-08-25
- 상태: 확인 시점 기준 정식 학회 proceedings 등재를 확인하지 못했으므로 학회 논문으로 표기하지 않는다.

### 해결하려는 문제

기존 RAG는 검색된 문서들이 서로 일관적이라고 암묵적으로 가정한다. 충돌을 탐지·유형화하지 않고 generator에 바로 전달하면 잘못되거나 일관되지 않은 답이 생성된다.

### 해결 방법

1. embedding interaction feature를 사용하는 경량 MLP conflict detector
2. 불확실한 사례만 LLM으로 refinement
3. factual·temporal·opinion 등 conflict type 분류
4. Entropy-TOPSIS 기반 source credibility 평가
5. 유형별 resolution 후 source attribution을 포함한 답 생성
6. correctness·detection·resolution·source fidelity를 결합한 CARS 평가

### 접근 유형

- modular detect–classify–resolve pipeline
- selective LLM refinement
- multi-criteria source credibility
- conflict-aware evaluation score

### 논문이 주장한 장점

- LLM을 전 문서쌍에 호출하지 않아 detection 비용 절감
- 유형별로 다른 resolution 적용
- 모듈별 진단과 source attribution 가능

### 방법론상 잔여 한계

- detector·classifier 오류가 resolution 단계에 누적된다.
- source credibility가 특정 질문에 대한 claim correctness를 보장하지 않는다.
- factual·temporal·opinion이 겹치는 복합 충돌에는 hard classification이 제한적이다.
- 작은 detector의 benchmark 성능이 실제 web corpus distribution shift에서 유지되는지 추가 검증이 필요하다.
- CARS처럼 여러 지표를 하나로 합치면 어떤 단계가 실제 개선됐는지 가려질 수 있다.

---

## 3.8 후속 조사에서 추가로 확인한 최근 인접 연구

이 절은 저장소 `literature/papers/` 원문 7편과 구분한다. 복합 충돌 주제의 선점 여부를 판단하기 위해 추가 조사한 논문이며, 학회 등재 여부는 2026-08-26 확인 기준이다.

### 3.8.1 등재·공개 정보

| 논문·자원 | 학회·상태 | 시점 | 주된 역할 |
|---|---|---:|---|
| [QACC](https://aclanthology.org/2025.findings-naacl.99/) | Findings of NAACL 2025 | 2025-04 | 실제 web 검색의 복수 답 충돌 데이터 |
| [DRUID](https://aclanthology.org/2025.acl-long.968/) | ACL 2025 Main, Long | 2025-07 | 실제 검색 문맥의 unreliable·insufficient·difficult 특성 분석 |
| [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/) | Findings of EMNLP 2025 | 2025-11 | KG 기반 다중 위치·multi-hop conflict benchmark |
| [Multi-LLM Verification](https://aclanthology.org/2025.ranlp-1.116/) | RANLP 2025 | 2025-09 | QACC에서 self/multi-agent verification 비교 |
| [TruthfulRAG](https://ojs.aaai.org/index.php/AAAI/article/view/40489) | AAAI 2026 | 2026 | KG와 entropy를 이용한 conflict filtering |
| [CF-RAG](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1c078897dc08d46091d0d361d9955c6b-Abstract-Conference.html) | ICLR 2026 | 2026 | counterfactual query와 parallel arbitration |
| [ConfRAG](https://aclanthology.org/2026.acl-long.11/) | ACL 2026 Main, Long | 2026-07 | 실제 web의 answer/reason cluster benchmark |
| [Ragability](https://aclanthology.org/2026.lrec-1.182/) | LREC 2026 | 2026 | implicit inter-context conflict benchmark |
| [KCR](https://aclanthology.org/2026.acl-long.1451/) | ACL 2026 Main, Long | 2026-07 | reasoning trace 구조화와 RLVR |
| [GroupQA](https://aclanthology.org/2026.findings-acl.2003/) | Findings of ACL 2026 | 2026-07 | evidence group의 stance·strength와 선택 편향 분석 |
| [ConflictQA / XoT](https://arxiv.org/abs/2604.11209) | SIGIR 2026 논문으로 공개 | 2026 | text–KG 충돌과 cross-source reasoning |
| [ContraPRT / Cross-Validated Re-ranking](https://doi.org/10.1109/IJCNN64981.2025.11228012) | IJCNN 2025 | 2025 | 한 passage pair의 단일·복수 linguistic conflict aspect와 re-ranking |
| [ArbGraph](https://arxiv.org/abs/2604.18362) | arXiv preprint | 2026-04-20 | atomic claim graph와 iterative arbitration |
| [EvidentialRAG](https://arxiv.org/abs/2607.10491) | arXiv preprint | 2026-07-11 | 확률적 evidence fusion과 answer/abstain routing |
| [CONFLICTS / DRAGged](https://arxiv.org/abs/2506.08500) | arXiv preprint | 2025-06 | complementary·opinion·outdated·misinformation 유형 데이터 |

`arXiv preprint`은 정식 학회 채택으로 간주하지 않는다. ConflictQA의 `COMP`는 복합 충돌이 아니라 complementary evidence를 이용하는 multi-hop 구성을 뜻하므로, 이 문서의 heterogeneous composite conflict와 구분한다.

### 3.8.2 데이터·분석 논문의 문제, 방법, 한계

| 논문 | 해결·분석하려는 문제 | 접근 | 복합 충돌 관점의 한계 |
|---|---|---|---|
| QACC | 명확한 factual question도 web 결과에서 서로 다른 답을 갖는 문제 | Google top-10 문맥을 수집하고 충돌 답·정답·선택 이유를 사람 주석 | 여러 answer candidate는 있지만 claim별 원인과 해결 연산은 주석하지 않음 |
| DRUID | synthetic conflict가 실제 검색 문맥의 복잡성을 왜곡하는 문제 | 실제 claim/evidence에 stance·신뢰성·충분성·난이도 주석 | QA용 복합 resolution benchmark가 아니며 operator 조합을 평가하지 않음 |
| MAGIC | single-hop·single-location conflict 평가의 한계 | KG로 multi-hop 문맥을 만들고 conflict location 수를 1~4개로 통제 | multiple은 주로 모순 위치·개수이며 서로 다른 해결 의미의 합성이 아님 |
| ConfRAG | 실제 controversial web 문서의 answer·reason 다양성을 기존 QA metric이 놓치는 문제 | answer cluster와 reason cluster를 구성해 coverage·clustering 평가 | 관점 보존 사례가 많고 서로 다른 operator의 실행 순서는 제공하지 않음 |
| Ragability | 표면 비교만으로 찾기 어려운 implicit contradiction | 실제 사례를 fantasy entity로 치환해 memory 영향을 통제하고 detection·QA 평가 | conflict hint가 no-conflict 성능을 해칠 수 있고 복수 연산 계획은 없음 |
| GroupQA | 여러 evidence group 중 무엇을 따르는지 불투명한 문제 | controversial question에 stance·strength를 주석하고 반복·순서 효과 분석 | stance group 선택 분석이 중심이며 heterogeneous conflict resolution task가 아님 |
| CONFLICTS / DRAGged | 실제 문서 충돌 원인이 factual contradiction보다 다양함 | 사례를 complementary·opinion·outdated·misinformation 등 단일 유형으로 분류 | 상호배타적 instance label이어서 한 사례 내부의 복수 relation/action을 표현하지 못함 |

QACC는 **명확한 open-domain question의 약 25%에서 Google 검색 문맥에 서로 다른 답이 나타났다**고 보고한다. 반면 DRUID는 synthetic conflict와 실제 검색 문맥 사이의 차이가 크다고 지적한다. 따라서 복합 benchmark는 기계적 합성뿐 아니라 실제 web 사례에서 복합 관계의 발생률을 제시해야 한다.

### 3.8.3 해결 방법 논문의 문제, 방법, 한계

| 논문 | 해결하려는 문제 | 핵심 방법 | 학습 | 복합 충돌 관점의 한계 |
|---|---|---|:---:|---|
| Multi-LLM Verification | 한 모델의 self-verification이 충돌 답을 안정적으로 고르지 못함 | 여러 LLM 답 중 별도 verifier가 최선 답 선택 | X | 후보 답 선택 중심이며 claim relation이나 heterogeneous action을 모델링하지 않음 |
| TruthfulRAG | noisy·conflicting triple이 KG-RAG를 오염 | triple/KG 구조화, graph retrieval, entropy filtering | 설정별 상이 | 구조화·filtering은 선점됐지만 보존·병합·조건화 operator plan은 아님 |
| CF-RAG | 다수의 상관된 오정보가 인과적 근거를 압도 | counterfactual query, parallel reasoning, arbitration | X | causal relevance가 중심이며 temporal·scope·ambiguity별 연산 합성은 다루지 않음 |
| KCR | 얽힌 conflict logic과 사례 이질성 때문에 고정 규칙이 일반화하지 못함 | textual/graph reasoning path 분해 후 RLVR | O | dyadic adjudication 중심이며 저자도 binary conflict를 한계로 명시; 학습 비용이 큼 |
| ConflictQA / XoT | text와 KG가 충돌·보완될 때 cross-source reasoning이 어려움 | source별 reasoning 분리 후 cross-source thinking | 설정별 상이 | source modality 조합이며 heterogeneous inter-document operator 조합과 다름 |
| ContraPRT | relevance 중심 re-ranking이 conflicting passage를 상위에 남김 | passage pair cross-validation 후 오류 passage 제거·재정렬 | X | 복수 type을 직접 다루지만 negation·numeric·relation 등 표현 형식 중심이고 모든 충돌을 제거 action으로 환원 |
| ArbGraph | long-form RAG에서 resolution이 generation과 얽힘 | atomic claim support/contradiction graph와 credibility propagation | X | claim graph는 선점됨; 주로 suppression으로 처리해 keep-both·condition·supersede를 계획하지 않음 |
| EvidentialRAG | 충돌을 단일 답으로 정규화하면 uncertainty가 사라짐 | Dirichlet evidence와 conflict-preserving fusion 후 answer/abstain routing | X | uncertainty routing은 선점됨; relation별 operator와 실행 순서는 다루지 않음 |
| ConflictRAG | 생성 전 충돌 탐지·유형화·해결이 없음 | detector, type classification, credibility resolution | detector O | detect→single-type route는 선점됨; hard type은 복수 relation이 겹칠 때 불안정 |

### 3.8.4 방법론 유형과 선점 범위

| 유형 | 대표 논문 | 이미 선점된 핵심 |
|---|---|---|
| 다중 위치·multi-hop benchmark | MAGIC | conflict 개수와 reasoning depth 통제 |
| 다중 answer·stance benchmark | QACC·ConfRAG·GroupQA | 여러 답·관점 cluster와 evidence group 평가 |
| instance-level type 분류 | CONFLICTS/DRAGged·ConflictRAG | conflict taxonomy와 유형별 routing |
| atomic claim graph | ArbGraph·TruthfulRAG | claim/triple 추출, graph edge, 사전 filtering |
| 구조화 reasoning trace | KCR·ConflictQA/XoT | source·후보별 reasoning 분리와 통합 |
| counterfactual arbitration | CF-RAG | 상관된 오정보와 인과적 증거 분리 |
| uncertainty-preserving fusion | EvidentialRAG | 충돌을 불확실성으로 전달하고 abstain routing |
| agent verification·debate | MADAM-RAG·Multi-LLM Verification | 문서·모델별 답 생성과 aggregation |

### 3.8.5 복합 충돌 해결 파이프라인에서 남은 공백

다중 충돌 데이터셋별 정의·발생 근거·활용 우선순위와 논문 주장 논리는 [03_dataset_evidence.md](./03_dataset_evidence.md)에 별도로 상세 정리했다.

“복합 충돌 파이프라인” 전체가 비어 있는 것은 아니다. RAMDocs/MADAM-RAG은 ambiguity·misinformation·noise를 함께 처리하고, ConflictRAG은 탐지·분류·해결 파이프라인을 제공하며, ArbGraph는 atomic claim graph를 만든다. 따라서 **여러 충돌을 유형별로 나눠 pipeline으로 해결한다**는 주장만으로는 신규성이 약하다.

상대적으로 비어 있는 문제는 다음과 같다.

> 하나의 질문 안에서 서로 다른 해결 의미를 가진 claim relation이 동시에 존재하고, 각각 `COLLAPSE_DUPLICATES`, `SUPERSEDE`, `CONDITION`, `PREFER`, `KEEP_BOTH`, `MERGE`, `ABSTAIN`처럼 다른 연산을 요구할 때 어떤 연산을 어떤 순서로 적용해야 하는가?

이를 **heterogeneous compositional conflict resolution**로 정의한다. 단순한 conflict 수 증가와 달리 다음 속성을 요구한다.

1. 한 instance에 둘 이상의 conflict relation이 존재한다.
2. relation들이 둘 이상의 서로 다른 resolution operator를 요구한다.
3. 일부 operator는 순서에 따라 결과가 달라진다. 예를 들어 복제 오정보 제거 전 majority를 계산하면 오답이 강화된다.
4. 최종 행동이 항상 단일 답 선택은 아니다. 조건부 병합, 복수 답 보존, 근거 부족에 따른 보류도 포함한다.

이 공백은 KCR의 dyadic/binary adjudication, ConflictRAG의 hard type routing, ArbGraph의 공통 credibility propagation, MADAM-RAG의 고비용 debate와 구별할 수 있다. 다만 **자연 데이터에서 이런 사례가 충분히 자주 나타난다는 증거는 아직 확보되지 않았다.** 따라서 논문 기여는 다음을 함께 갖춰야 한다.

- 실제 QACC·DRAGged·RAMDocs 또는 web retrieval 표본에서 heterogeneous composite conflict의 발생률과 주석 일치도 제시
- claim relation·resolution operator·operator dependency를 포함한 사람 검증 benchmark 또는 평가 subset 공개
- 학습 없이 operator plan을 만들고 실행하되 oracle structure와 automatic extraction을 분리 평가하는 selective pipeline 제안

결론적으로 복합 충돌 해결 파이프라인으로 진행할 여지는 있다. 신규성의 중심은 pipeline 형식이 아니라 **이질적 해결 연산의 합성, 의존관계, 순서 효과**여야 한다.

---

## 4. 논문들이 문제를 바라보는 축

### 4.1 언제 개입하는가

| 시점 | 해당 접근 | 설명 |
|---|---|---|
| Training-data construction | Conflict-Aware RAG | conflict signal로 학습 사례 선택 |
| Model training | Self-RAG·Conflict-Aware RAG | reflection 또는 preference 행동 학습 |
| Retrieval 후 generation 전 | ConflictRAG·FaithfulRAG | conflict 탐지·fact alignment·source 판정 |
| Generation 중 | CD²·COIECD | token probability 직접 수정 |
| 여러 generation 사이 | MADAM-RAG | agent 답을 토론·집계 |
| Evaluation | Tug-of-War·RAMDocs·CARS | 편향·복합 충돌·단계 성능 측정 |

### 4.2 무엇을 conflict signal로 사용하는가

| 신호 | 논문 | 의미 |
|---|---|---|
| 문맥 유무 logits 차이 | CD² 계열 | internal vs. external knowledge tension |
| contextual entropy | COIECD | conflict 존재·강도 추정 |
| reflection token | Self-RAG | relevance·support·utility 자기평가 |
| self-fact vs. context fact | FaithfulRAG | fact-level disagreement |
| agent disagreement | MADAM-RAG | 문서·답 후보 간 충돌 |
| ConScore | Conflict-Aware RAG | source별 생성 probability 차이 |
| embedding interaction + LLM | ConflictRAG | 문서쌍 conflict 탐지·유형화 |

### 4.3 무엇을 최적화하는가

| 목표 | 논문 |
|---|---|
| 외부 문맥 faithfulness | CD²·COIECD·FaithfulRAG |
| retrieval 필요성·relevance·support | Self-RAG |
| 복수 유효 답 보존과 misinformation 억제 | MADAM-RAG |
| end-to-end RAG robustness | Conflict-Aware RAG |
| conflict detection·resolution·source fidelity | ConflictRAG |
| 편향과 충돌 행동의 이해 | Tug-of-War |

여기서 중요한 차이는 **faithfulness와 correctness가 동일하지 않다**는 점이다. 외부 문맥을 강하게 따르는 방법은 검색 문서가 옳을 때 유리하지만, inter-context conflict에서는 어떤 문맥이 옳은지를 먼저 판정해야 한다.

---

## 5. 공통적으로 남은 한계

### 5.1 올바른 문서 선택과 context faithfulness의 혼동

많은 방법은 parametric memory보다 context를 더 따르게 만든다. 하지만 외부 문서끼리 충돌하면 context를 따른다는 목표만으로는 부족하다.

```text
문서 A: 정답
문서 B: 오정보

문서 B에 충실한 답 = context-faithful이지만 incorrect
```

### 5.2 초기 탐지·추출 오류의 전파

- Self-RAG: reflection token 오류
- FaithfulRAG: fact extraction 오류
- ConflictRAG: detector/type 오류
- Conflict-Aware RAG: ConScore 오류
- MADAM-RAG: document agent 초기 답 오류

모든 방법은 초기에 만든 conflict representation이 틀릴 때 후속 단계 전체가 흔들릴 수 있다.

### 5.3 반복 evidence와 독립 evidence의 구분 부족

같은 오정보를 복제한 여러 문서는 독립된 지지가 아니다. 그러나 majority voting, debate, passage scoring은 문서 수를 증거 강도로 오인할 수 있다.

### 5.4 비용과 적용성의 trade-off

| 접근 | 주요 비용 |
|---|---|
| 학습 기반 | 데이터 구축·SFT·DPO·재학습 |
| contrastive decoding | 다중 forward와 logits 접근 |
| fact alignment | fact extraction·matching 호출 |
| agent debate | agent 수×round 수 generation |
| modular pipeline | detector·classifier·resolver 운영 복잡도 |

### 5.5 최종 정확도 중심 평가

방법이 정답률을 높여도 다음이 구분되지 않는 경우가 많다.

- 충돌을 실제로 발견하고 올바른 문서를 선택해 맞힘
- 해소하지 못했지만 parametric memory로 맞힘
- 잘못된 문서를 지지한 뒤 최종 답만 우연히 맞힘
- 오답과 정답이 문항별로 교환되었지만 평균 정확도는 유지

### 5.6 자연 충돌과 복합 충돌의 외적 타당성

- synthetic substitution은 정답 통제가 쉽지만 실제 web conflict와 다르다.
- 자연 데이터는 현실적이지만 gold answer·문서 정오·시점 검증이 어렵다.
- ambiguity·opinion·complementary는 단일 정답 accuracy로 평가하기 어렵다.
- factual·temporal·opinion을 하나의 conflict label로 합치면 기대 행동 차이가 사라진다.

---

## 6. 현재 프로젝트에서의 활용 위치

이 절은 새로운 연구 주제를 확정하지 않고, 각 논문이 현재 자원에서 어떤 역할을 할 수 있는지만 정리한다.

| 논문 | 현재 프로젝트에서의 역할 |
|---|---|
| Self-RAG | reflection prompt 및 adaptive retrieval 비교선 |
| Tug-of-War / CD² | majority·confirmation bias 가설과 decoding baseline |
| COIECD | conflict-aware adaptive decoding baseline 및 비용 비교 |
| FaithfulRAG | fact-level conflict representation 비교 |
| RAMDocs / MADAM-RAG | 통제 데이터와 agent debate baseline |
| Conflict-Aware RAG | 학습 기반 상한·비교 대상. 직접 재학습은 자원상 후순위 |
| ConflictRAG | detect–classify–resolve pipeline 비교 및 단계 평가 기준 |

현재 프로젝트의 공통 질문은 이 방법들이 올린 최종 성능이 다음 중 어느 경로에서 왔는지를 확인하는 데 있다.

```text
충돌 탐지
   ↓
올바른 문서·주장 선택
   ↓
선택한 결론과 일치하는 최종 답
```

다만 이 진단 질문 자체도 최근 monitoring–control 연구와 인접하므로, 후속 주제를 정할 때는 반드시 최신 선행연구와 다시 대조해야 한다.

---

## 7. 핵심 요약

1. **Self-RAG와 Conflict-Aware RAG**은 conflict 관련 행동을 학습으로 내재화한다.
2. **CD²와 COIECD**는 학습 없이 token probability를 수정하지만 logits 접근과 추가 decoding 비용이 필요하다.
3. **FaithfulRAG**은 document가 아닌 fact 단위로 충돌을 다루지만 extraction 오류와 faithfulness–correctness 차이가 남는다.
4. **MADAM-RAG**은 ambiguity·misinformation·noise를 agent debate로 함께 처리하지만 비용과 evidence imbalance 문제가 크다.
5. **ConflictRAG**은 충돌을 generation 전에 탐지·분류·해결하지만 초기 module 오류가 누적될 수 있다.
6. **Tug-of-War**는 majority·confirmation·parametric bias를 밝혔지만 최종 score만으로 추론 실패 위치를 설명하기 어렵다.
7. 전체적으로 학습 비용, logits 접근, agent 비용, 초기 오류 전파, 올바른 문서 선택과 단순 context faithfulness의 혼동이 공통 한계다.
8. **MAGIC·QACC·ConfRAG·GroupQA**는 다중 충돌 위치, 복수 답, stance group을 다루지만 heterogeneous resolution operator의 조합과 순서를 직접 주석하지 않는다.
9. **ArbGraph·TruthfulRAG·KCR·CF-RAG·EvidentialRAG**는 claim graph, 구조화 reasoning, counterfactual arbitration, uncertainty fusion을 각각 선점했으므로 이 구성요소 자체를 신규 기여로 주장하기 어렵다.
10. 남은 후보 공백은 한 사례 내부에서 서로 다른 연산이 필요한 충돌을 찾고, 그 **연산의 합성·의존관계·순서 효과**를 학습 없이 해결하는 것이다. 단, 실제 발생률과 사람 주석 benchmark가 선행되어야 한다.

이 문서를 기준으로 후속 연구 주제를 만들 때는 기존 해결 연산을 새 방법으로 다시 제안하기보다, **어떤 conflict 범위와 어떤 실패 단계가 기존 접근에서 실제로 미해결인지**를 먼저 특정해야 한다.
