# 기존 연구로 검증된 사실과 남은 공백

작성일: 2026-09-01  
목적: 03 연구에서 이미 검증된 현상을 불필요하게 재실험하거나 신규 기여로 주장하지 않기 위한 근거 문서

## 1. 판정 원칙

다음 조건을 만족하면 파일럿의 confirmatory hypothesis에서 제외한다.

1. 선행연구가 해당 현상을 직접 조작하거나 비교했다.
2. 평가 지표와 결과가 공개되어 있다.
3. 우리 연구에서 필요한 결론을 인용만으로 사용할 수 있다.

최신 모델에서 baseline 수치를 얻기 위한 최소 실행은 허용하지만, 이를 독립 연구 질문이나 신규 발견으로 취급하지 않는다.

## 2. 이미 검증된 사실

### V1. Multi-hop conflict는 single-hop conflict보다 어렵다

**근거:** [MAGIC: A Multi-Hop and Graph-Based Benchmark for Inter-Context Conflicts in Retrieval-Augmented Generation](https://aclanthology.org/2025.findings-emnlp.466/)

MAGIC은 conflict를 single-hop/multi-hop과 1-conflict/N-conflict 축으로 구분하고, 다섯 LLM의 Identification(ID)과 Localization(LOC)을 평가했다. 논문은 multi-hop에서 ID와 LOC가 모두 낮고, 특히 여러 위치를 연결해야 하는 localization이 어렵다고 보고한다.

**03에 주는 결론:**

- “multi-hop conflict가 더 어렵다”를 다시 주가설로 검증하지 않는다.
- Single-hop은 oracle gap의 multi-hop-specific amplification을 계산하기 위한 소규모 calibration에만 사용한다.
- 최신 모델에서 MAGIC 수치를 갱신하더라도 baseline replication으로 표기한다.

### V2. Conflict localization은 단순 detection보다 어렵다

**근거:** [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)

MAGIC에서 다섯 모델 평균 ID는 64.54%, LOC는 40.51%로 보고되었다. 모델이 충돌 존재를 인지하더라도 정확한 충돌 지점을 모두 찾지 못한다는 현상은 이미 검증되었다.

**03에 주는 결론:**

- “탐지 후 국소화 실패” 자체를 신규 현상으로 주장하지 않는다.
- 03은 localization 실패의 최초 원인이 source selection, claim compilation, graph composition, proof search 중 어디인지 분해한다.

### V3. 충돌 개수는 detection과 localization에 서로 다른 영향을 준다

**근거:** [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)

MAGIC은 충돌 수가 많아지면 모순이 두드러져 ID는 쉬워질 수 있지만, 모든 충돌 위치를 찾아야 하는 LOC는 어려워진다고 보고한다.

**03에 주는 결론:**

- 1/N-conflict 성능 곡선을 다시 연구 질문으로 두지 않는다.
- Conflict 개수는 oracle ladder 표본을 균형화하기 위한 통제 변수로만 사용한다.

### V4. Structured/multi-step prompting은 단순 binary prompting보다 강할 수 있다

**근거:** [MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)

MAGIC의 prompt 비교에서 multi-step prompt는 binary prompt보다 모든 비교 조건에서 높았고 최대 39.41% 향상을 보였다.

[Contradiction Detection in RAG Systems](https://arxiv.org/abs/2504.00180)은 CoT 효과가 모델과 과제에 따라 달라지며, conflict detection에서는 일부 Claude 모델을 개선하지만 Llama 계열에서는 악화될 수도 있음을 보였다.

**03에 주는 결론:**

- Prompt 방식 비교를 독립 가설로 두지 않는다.
- 하나의 고정 structured prompt를 모든 oracle 조건에 공통 사용한다.
- Prompt 선택은 방법론 기여가 아니라 측정 도구로 취급한다.

### V5. 세 문서를 결합해야 드러나는 conditional contradiction은 이미 제안ㆍ평가되었다

**근거:** [Contradiction Detection in RAG Systems: Evaluating LLMs as Context Validators for Improved Information Consistency](https://arxiv.org/abs/2504.00180)

이 연구는 세 번째 문서가 앞의 두 문서를 상호 배타적으로 만드는 conditional contradiction을 정의했다. HotpotQA 문서를 기반으로 self, pair, conditional contradiction과 no-conflict를 포함한 1,867개 합성 사례를 생성해 모델별 탐지 성능을 비교했다.

Conditional data의 사람 검증은 쉽지 않았다. 두 annotator가 본 40개 conditional 사례 중 17개만 처음에 conflict로 식별했다는 보고가 있어 annotation 명확성과 재현성에는 여전히 한계가 있다.

**03에 주는 결론:**

- “세 문서를 함께 봐야 하는 충돌이 존재한다”는 사실을 재검증하지 않는다.
- 소규모 higher-order set으로 존재나 난도를 보이는 실험을 하지 않는다.
- 이후 certificate 방법을 제안한다면 최소성, proof validity, 정보 등가성을 엄격히 주석하는 별도 데이터가 필요하다.

### V6. Pairwise consistency는 global consistency를 보장하지 않는다

**근거:** [Foundations of Global Consistency Checking with Noisy LLM Oracles](https://arxiv.org/abs/2601.13600)

이 연구는 자연어 fact 집합의 global consistency를 형식화하고 pairwise 검사만으로 충분하지 않음을 전제로 minimal inconsistent subset(MUS) 탐색과 hitting-set repair를 제안한다.

**03에 주는 결론:**

- Pairwise detector의 원리적 한계를 새로 증명하지 않는다.
- MUS/MIES 자체를 신규 기여로 주장하지 않는다.
- Foundations는 gold/predicted fact가 주어진 이후 proof/subset-search 기준선으로 사용한다.

### V7. Atomic claim 또는 KG 기반 conflict handling은 유용할 수 있다

**근거:**

- [TruthfulRAG: Resolving Factual-level Conflicts in Retrieval-Augmented Generation with Knowledge Graphs](https://ojs.aaai.org/index.php/AAAI/article/view/40489)
- [ArbGraph: Conflict-Aware Evidence Arbitration for Reliable Long-Form Retrieval-Augmented Generation](https://arxiv.org/abs/2604.18362)

TruthfulRAG은 검색 문서에서 triple을 추출하고 KG 검색과 filtering으로 충돌을 처리한다. ArbGraph는 문서를 atomic claim으로 분해하고 support/contradiction graph에서 credibility를 전파한다. 두 연구 모두 구조화된 evidence representation을 사용하는 충돌 처리의 효용을 보여준다.

**03에 주는 결론:**

- “그래프를 사용하면 좋아진다”는 주장은 신규성이 없다.
- Hard claim/edge 추출 오류와 oracle gold representation 사이의 차이를 측정해야 한다.
- 후속 방법은 단순 graph 적용이 아니라 관찰된 compilation 또는 proof 병목을 직접 해결해야 한다.

### V8. 실제 웹 다중 출처에서도 conflict reasoning 성능은 불충분하다

**근거:** [Benchmarking LLM's Capability in Reasoning over Conflicting Web References (ConfRAG)](https://aclanthology.org/2026.acl-long.11/)

ConfRAG은 1,814개 실제 질문과 평균 9.58개 웹 문단을 제공하며, 57.2%의 질문에서 명시적 contradiction을 보고한다. Answer clustering, answer coverage, reason coverage 평가에서 최신 모델에도 큰 성능 공백이 있음을 보였다.

**03에 주는 결론:**

- “실제 웹 문서의 충돌이 어렵다”는 일반 주장도 인용으로 충분하다.
- 자연문서 subset은 MAGIC에서 발견한 특정 oracle gap이 실제 문서에서도 나타나는지 확인할 때만 사용한다.

## 3. 아직 직접 검증되지 않은 공백

### O1. Information-equivalent oracle ladder

동일 multi-hop conflict 사례에서 다음 표현을 정보량이 같도록 구성해 단계별로 개입한 연구는 확인하지 못했다.

```text
raw documents
→ gold source evidence
→ gold canonical prose claims
→ gold triplet serialization
→ gold graph adjacency
→ gold proof skeleton
```

기존 연구는 raw text에서의 실패를 보이거나, 처음부터 fact를 입력받거나, predicted atomic claim/KG를 사용하는 방법을 평가한다. 이 때문에 실패가 어느 변환 단계에서 최초 발생했는지는 아직 분리되지 않았다.

### O2. Multi-hop conflict에서 compilation과 proof-search의 상대 기여

Gold evidence/claim/graph를 순차 제공했을 때 exact conflict certificate가 얼마나 회복되는지, 그리고 그 회복량이 multi-hop에서 증폭되는지는 직접 검증되지 않았다.

### O3. Claim canonicalization과 serialization 효과의 분리

Gold triple이 raw prose보다 좋더라도 다음 원인이 섞일 수 있다.

- 짧아진 token 길이
- 불필요 문장 제거
- entity alias 정규화
- atomic fact 분해
- tuple 형식 자체의 inductive bias
- graph adjacency 제공

Canonical prose와 정보-equivalent triples를 구분한 개입이 필요하다.

### O4. Source-grounded fully valid conflict certificate의 계층별 평가

기존 ID/LOC 또는 downstream answer 지표는 다음 전체 사슬이 어디서 깨졌는지 알려주지 않는다.

```text
source span
→ atomic claim
→ alignment
→ derived claim
→ terminal incompatibility
```

각 단계가 원문에 역추적되는 fully valid certificate와 first-failure attribution은 남은 연구 공백이다.

### O5. Query twin에 의한 answer-relevant conflict 변화

실제 질문 기반 conflict benchmark는 존재하지만, 동일 문서 집합에 질문만 바꿔 conflict relevance 또는 필요한 행동이 달라지는 paired query twin은 체계적으로 검증되지 않았다. 다만 이 공백은 Pilot A가 아니라 후속 연구 범위다.

## 4. 03 파일럿에 대한 최종 경계

Pilot A가 검증할 주장은 다음 하나로 제한한다.

> 이미 알려진 multi-hop conflict 실패에서, 정보-equivalent oracle intervention을 통해 최초 병목이 evidence selection, claim canonicalization, graph organization, proof search 중 어디인지 식별할 수 있는가?

Pilot A가 검증하지 않을 주장은 다음과 같다.

- multi-hop conflict가 어렵다.
- localization이 detection보다 어렵다.
- conditional conflict가 존재한다.
- pairwise 검사가 충분하지 않다.
- structured prompting 또는 graph가 일반적으로 도움이 된다.

이 경계를 지켜야 후속 방법론이 이미 알려진 현상을 재포장하지 않고, 새로 확인된 병목을 직접 해결한다는 논리적 연결을 가질 수 있다.
