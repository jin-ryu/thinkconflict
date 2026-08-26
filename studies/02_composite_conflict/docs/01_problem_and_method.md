# 복합 충돌을 위한 학습 없는 조합적 RAG 해결 파이프라인

> ACL 논문 초안 구조, 2026-08-26 개정
> 현재 단계: 문제 정의·관련 연구·방법론·실험 계획
> 아직 작성하지 않는 부분: 실험 결과, 결론, 한계
> 관련 문서: [다중·복합 충돌 데이터셋 논문 분석과 연구 주장 논리](./03_dataset_evidence.md)

---

## 초록 초안

검색 증강 생성(RAG)은 여러 외부 문서를 동시에 사용하지만, 기존 conflict-aware RAG 연구는 대체로 한 instance에 하나의 충돌 유형이 존재한다고 가정하거나 동일한 해결 규칙을 반복 적용한다. 실제 retrieval set에서는 충돌 지점의 수뿐 아니라 충돌의 의미와 바람직한 대응도 달라질 수 있다. 본 연구는 한 instance의 독립적인 core conflict unit 수를 **conflict cardinality `K`**, 필요한 서로 다른 의미적 resolution operator 수를 **resolution heterogeneity `H`**로 정의한다. 이에 따라 `K>1`을 **다중 충돌**, `H>1`을 **복합 충돌**로 구분한다. 기존 MAGIC은 주로 `K` 증가를, DRAGged/CONFLICTS는 여러 유형 중 하나를, RAMDocs는 고정된 ambiguity·misinformation·noise 조합을 다루지만, 일반적인 `K×H` 공간에서 여러 conflict unit을 식별하고 서로 다른 해결 행동을 합성하는 문제는 충분히 평가되지 않았다. 이를 위해 본 연구는 학습 없이 atomic claim을 분해하고, conflict unit별 relation과 resolution operator를 산출한 뒤, 하나의 전역 resolution plan으로 합성하는 **Property-Conditioned Compositional Conflict Resolution(PCCR)** 파이프라인을 제안한다. ConfRAG·NatConfQA·QACC 등 자연 검색 문서를 공통 schema로 재주석해 `K/H` 분포를 먼저 검증하고, 검색 파일럿의 부정 결과를 반영해 후속 단계는 long-term personalized memory에서 query-level `K/H` composition의 현실성과 독립 난이도를 검증한다. 그 근거가 확보된 뒤에만 training-free 해결 파이프라인을 개발한다.

초록에는 실험 완료 전까지 성능 수치와 우월성 표현을 넣지 않는다.

---

# 1. 서론

## 1.1 배경

RAG 시스템은 검색된 문서가 질문에 관련 있고 서로 양립한다고 암묵적으로 가정한다. 그러나 실제 검색 결과에는 서로 다른 시점의 정보, 대상·지역·조건이 다른 주장, 상충하는 연구 결과와 의견, 상보적인 부분 답, 사실적으로 양립할 수 없는 답이 함께 포함될 수 있다.

이러한 retrieval set에 하나의 일괄 규칙을 적용하면 다음 문제가 생긴다.

- 모든 불일치를 제거하면 유효한 ambiguity·의견·상보 정보를 잃는다.
- 모든 관점을 보존하면 misinformation까지 답에 남는다.
- 항상 최신 문서를 따르면 역사적 질문이나 잘못된 최신 문서에서 실패한다.
- 항상 다수 문서를 따르면 복제·재인용된 오정보가 독립적인 다수 증거처럼 작동한다.
- instance 전체에 하나의 conflict type을 부여하면 문서 내부의 서로 다른 claim 관계가 가려진다.

## 1.2 문제의 핵심

기존 연구에서 “multiple conflicts”는 서로 다른 의미로 사용된다.

- MAGIC: 동일 instance에 존재하는 contradiction location의 수
- ConfRAG·QACC: 서로 다른 answer 또는 reason cluster의 수
- DRAGged: benchmark 전체에서 제공하는 conflict category의 다양성
- RAMDocs: ambiguity, misinformation, noise의 공동 존재

따라서 본 연구는 다음 두 축을 명시적으로 분리한다.

- **다중 충돌(multi-conflict):** 충돌 개수 `K`가 2개 이상인 경우
- **복합 충돌(composite conflict):** 한 instance에 서로 다른 충돌 유형·해결 행동이 공존해 `H`가 2개 이상인 경우

다중 충돌은 모든 conflict unit을 빠짐없이 찾고 반복 처리하는 능력을 요구한다. 복합 충돌은 각 unit에 서로 다른 행동을 적용하고 결과를 모순 없이 합성하는 능력을 추가로 요구한다.

## 1.3 연구 공백

[MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)은 `K=1...4`에서 conflict localization이 악화됨을 보여주지만, 여러 unit이 서로 다른 해결 행동을 요구하지는 않는다. [DRAGged/CONFLICTS](https://arxiv.org/abs/2506.08500)는 complementary, opinion, outdated, misinformation에 서로 다른 expected behavior를 정의하지만 기본적으로 instance-level 단일 유형을 사용한다. [RAMDocs](https://arxiv.org/abs/2504.13079)는 ambiguity·misinformation·noise를 함께 처리하지만 고정된 요인 조합이며, 각 claim relation과 해결 계획을 명시적으로 평가하지 않는다.

이로부터 다음 공백을 설정한다.

> 하나의 retrieval set에서 `K`개의 conflict unit을 식별하고, 각 unit이 요구하는 `H`개의 서로 다른 resolution operator를 선택·합성하여 최종 답을 생성하는 일반적인 학습 없는 방법과 평가 체계가 부족하다.

## 1.4 목표 기여

본 연구는 다음 기여를 목표로 한다. 아직 실험 전이므로 완료형 성능 주장이 아니다.

1. **문제 정의:** 다중 충돌 `K`와 복합 충돌 `H`를 분리한 `K×H` 평가 공간
2. **데이터 기여:** 기존 데이터셋을 공통 conflict-unit/action schema로 정규화하고, 자연·통제형 복합 충돌 평가 세트 구성
3. **방법 기여:** 학습 없이 conflict unit별 operator를 결정하고 전역 계획으로 합성하는 PCCR
4. **분석 기여:** `K`, `H`, 선택적 dependency `D`가 정확도·누락·비용에 미치는 영향

---

# 2. 문제 정의

## 2.1 입력과 conflict unit

질의 `q`와 검색 문서 집합 `D={d_1,...,d_n}`가 주어진다. 각 문서에서 질문에 답하는 최소 단위의 atomic claim을 추출해 `C={c_1,...,c_m}`을 구성한다.

conflict unit `u_i`는 다음을 포함한다.

```text
u_i = (claim set, evidence span set, relation, properties, required operator)
```

문서 전체가 아니라 claim·evidence span을 unit으로 삼는 이유는 한 문서가 여러 claim을 포함하고, 그중 일부만 다른 문서와 충돌할 수 있기 때문이다.

## 2.2 다중 충돌 `K`

**Conflict cardinality `K`**는 한 instance 안에서 독립적으로 localization되는 core conflict unit 수다.

```text
K = |U_core|
```

다음은 `K`에 포함하지 않는다.

- 동일 결론을 지지하는 `SUPPORT`
- 동일 원출처를 반복한 `DUPLICATE/DERIVATIVE`
- 질문과 무관한 문서
- 충돌 없이 단순히 불충분한 증거

`K>1`이면 다중 충돌이다. 모든 unit에 같은 operator가 필요해도 다중 충돌에 해당한다.

## 2.3 복합 충돌 `H`

**Resolution heterogeneity `H`**는 core conflict unit을 해결하는 데 필요한 서로 다른 의미적 operator의 수다.

```text
H = |{operator(u_i) : u_i ∈ U_core}|
```

`H>1`이면 복합 충돌이다. 일반적으로 `H≤K`다.

| `K,H` 조건 | 용어 | 예시 | 핵심 난점 |
|---|---|---|---|
| `K=1,H=1` | 단일 충돌 | 하나의 오정보를 배제 | 기본 판정 |
| `K>1,H=1` | 다중 충돌 | 네 개의 오정보 unit을 모두 배제 | localization·coverage |
| `K>1,H>1` | 복합 충돌 | outdated는 대체하고 opinion은 보존 | action 식별·합성 |

## 2.4 선택적 의존성 `D`

`D`는 conflict unit이 evidence를 공유하거나 operator 사이에 선행·순서 제약이 있는 정도다. `D`는 복합 충돌의 정의가 아니라 고난도 하위 축이다.

예를 들어 복제된 오정보를 독립 표로 센 뒤 majority를 적용하면 잘못된 답이 선택될 수 있다. 이때 `COLLAPSE_DUPLICATES`는 별도의 conflict type이 아니라 core conflict 해결 전에 필요한 conditioning이며, `PREFER`와의 순서 의존성이 `D`를 만든다.

## 2.5 Evidence condition과 core conflict의 경계

관련성·충분성·중복은 파이프라인이 처리해야 하지만 `K`와 `H`를 증가시키지 않는다.

| 조건 | 분류 | 처리 |
|---|---|---|
| irrelevant | evidence adequacy | `FILTER` |
| insufficient | evidence adequacy | `REQUEST_EVIDENCE`; 검색 불가 시 보류 |
| duplicate/derivative | evidence dependence | `COLLAPSE_DUPLICATES` |
| temporal update | core relation | `SUPERSEDE` 또는 시간 조건화 |
| scope difference | core relation | `CONDITION` |
| valid ambiguity/opinion | core relation | `KEEP_BOTH` |
| complementary information | core relation | `MERGE` |
| irreducible factual disagreement | core relation | `VERIFY/PREFER` 또는 `ABSTAIN` |

`misinformation`은 텍스트 모양이나 낮은 source reputation만으로 정하지 않는다. factual disagreement를 독립 근거로 검증한 뒤 한 주장이 거짓으로 판정될 때 사용하는 해결 결과에 가깝다.

## 2.6 출력

시스템은 최종 답뿐 아니라 다음 구조를 출력한다.

```json
{
  "K": 3,
  "H": 2,
  "conflict_units": ["..."],
  "operators": ["SUPERSEDE", "KEEP_BOTH"],
  "plan": ["..."],
  "answer": "...",
  "citations": ["..."]
}
```

구조화 출력은 component-level 평가와 oracle 분석을 가능하게 한다.

---

# 3. 관련 연구

## 3.1 다중 충돌: 개수와 localization

[MAGIC](https://aclanthology.org/2025.findings-emnlp.466/)은 KG 기반으로 single/multi-hop과 1~4개 conflict location을 통제한다. conflict 수가 늘면 존재 탐지는 쉬워질 수 있지만 정확한 localization은 어려워진다. 이는 `K` 축의 직접 근거다. 그러나 각 conflict가 서로 다른 resolution action을 요구하지는 않아 복합 충돌 `H`를 평가하지 않는다.

[ConfRAG](https://aclanthology.org/2026.acl-long.11/)은 1,814개의 실제 web question과 평균 9.58개 문단을 제공하며 answer clustering, answer coverage, reason coverage를 평가한다. 다양한 답과 이유의 누락을 분석하기 좋지만, cluster별 semantic conflict type과 operator gold는 없다.

## 3.2 충돌 유형과 expected behavior

[DRAGged/CONFLICTS](https://arxiv.org/abs/2506.08500)는 458개 질의와 평균 9.2개 실제 검색 결과를 제공한다. complementary information은 병합하고, opinion은 균형 있게 제시하며, outdated information은 최신 답을 우선하고, misinformation은 배제하는 expected behavior를 정의한다. 또한 factual grounding, answer recall, expected-behavior adherence를 분리 평가한다.

하지만 한 instance에 하나의 `conflict_type`을 부여하므로 복합 충돌을 직접 측정할 수 없다. 본 연구에서는 taxonomy와 평가 방식을 재사용하되, document set을 claim unit으로 재주석해 multi-label 여부를 조사한다.

## 3.3 여러 요인의 공동 존재

[RAMDocs/MADAM-RAG](https://arxiv.org/abs/2504.13079)는 한 질의에 ambiguity, misinformation, noise를 동시에 넣는다. 유효한 복수 답은 보존하면서 misinfo와 noise는 제거해야 하므로 `KEEP_BOTH + REJECT/FILTER` 행동을 함께 요구한다. 현재 가장 직접적인 복합 행동 데이터다.

그러나 noise는 core conflict가 아니고, 조합이 고정되어 있으며, 일반적인 `K×H` annotation이나 operator plan gold는 없다. 따라서 RAMDocs는 방법의 end-to-end 혼합 조건 평가에는 적합하지만 복합 충돌 전체를 대표하지 않는다.

## 3.4 통제 가능한 복합 충돌 후보: ConflictBank

[ConflictBank](https://arxiv.org/abs/2408.12076)은 553,117 QA pair와 7.45M claim-evidence pair를 제공하며 misinformation, temporal, semantic conflict를 구축한다. 특히 각 질문에는 default evidence와 세 종류의 conflict evidence가 연결되어 있어, 동일 question에서 유형 조합을 통제할 수 있다.

이 특성 때문에 현재 확인한 자원 중 **복합 충돌을 대규모로 구성하기 가장 적합한 controlled source**다.

| ConflictBank evidence | 본 연구의 후보 해석 | 후보 operator |
|---|---|---|
| misinformation | 같은 scope의 false alternative | `VERIFY/PREFER` |
| temporal | 시간 qualifier가 다른 주장 | `CONDITION/SUPERSEDE` |
| semantic | 동명·다의 대상 차이 | `CONDITION/DISAMBIGUATE` |

다만 그대로 gold로 사용하지 않고 다음을 재검증해야 한다.

- 원 논문은 유형별 영향을 주로 분리 평가했으며 operator composition을 평가하지 않았다.
- Wikidata와 Llama-3-70B로 생성한 synthetic evidence다.
- temporal evidence가 미래 시점을 이용해 구성되어 자연 freshness와 다를 수 있다.
- 세 conflict evidence가 default와는 충돌하지만 서로 간 관계가 항상 자연스럽지는 않다.
- type label이 곧바로 올바른 resolution operator를 보장하지 않는다.

따라서 ConflictBank는 통제형 `H` 평가의 기반으로 사용하고, 사람이 relation·operator·조합 타당성을 검증한 subset을 만든다.

## 3.5 실제 검색 증거의 속성

[DRUID](https://aclanthology.org/2025.acl-long.968/)는 1,329개의 실제 claim과 5,490개 claim-evidence sample에 relevance와 세분화된 stance를 주석하고, implicitness, uncertainty, source-related property 등을 분석한다. 이는 property schema를 현실적으로 설계하는 근거다. 하지만 QA resolution gold와 복합 conflict annotation은 없으므로 property extractor 검증용 보조 데이터로 사용한다.

[QACC](https://aclanthology.org/2025.findings-naacl.99/)는 자연 Google context에서 복수 답 충돌을 제공하고 majority, source trust, common sense, recency 등의 판단 요인을 포함한다. factual natural-conflict transfer에는 유용하지만 유형·operator multi-label은 추가 주석해야 한다.

## 3.6 구조화 해결 방법

[FaithfulRAG](https://aclanthology.org/2025.acl-long.1062/)는 parametric knowledge와 retrieved context를 fact level에서 정렬하고 self-thinking으로 통합한다. [ConflictRAG](https://arxiv.org/abs/2605.17301)는 detect–classify–resolve pipeline과 선택적 LLM refinement를 제안한다. [MADAM-RAG](https://arxiv.org/abs/2504.13079)는 document/answer agent debate와 aggregator를 사용한다.

따라서 다음만으로는 신규성이 부족하다.

- conflict를 먼저 분류한 뒤 유형별 prompt를 적용
- claim graph를 구성
- 여러 agent에게 문서를 나누어 제공
- 불확실한 사례만 LLM에 전달

본 연구의 방법 기여는 **한 instance의 여러 conflict unit과 서로 다른 operator를 명시하고, 모든 unit을 처리하는 전역 plan을 구성·검증하는 것**에 둔다.

---

# 4. 제안 방법: PCCR

## 4.1 개요

PCCR은 다음 단계로 구성되는 training-free pipeline이다.

```text
Query + retrieved evidence
        ↓
Evidence conditioning
        ↓
Atomic claim extraction
        ↓
Conflict-unit decomposition and K estimation
        ↓
Relation/operator assignment and H estimation
        ↓
Global operator composition
        ↓
Selective graph/plan search for dependent cases
        ↓
Grounded generation and residual-conflict verification
```

## 4.2 Evidence conditioning

먼저 질문과 무관한 evidence를 제외하고, 불충분성과 duplicate/derivative relation을 표시한다. 이 단계는 core conflict를 해결하지 않으며, 잘못된 majority나 불필요한 pair comparison을 방지한다.

metadata로 직접 알 수 있는 URL·publication time과 LLM이 추정한 sufficiency·certainty·scope를 구분해 기록한다.

## 4.3 Atomic claim과 conflict-unit 분해

문서에서 질문에 직접 기여하는 claim과 근거 span을 추출한다. 모든 문서쌍을 비교하는 대신 entity, answer target, temporal/scope overlap으로 후보를 blocking한다.

각 conflict unit은 다음 relation 중 하나 이상을 갖는다.

```text
COMPLEMENT
CONTRADICT_FACT
TEMPORAL_UPDATE
SCOPE_CONDITIONED
PERSPECTIVE_DISAGREEMENT
UNRESOLVED
```

unit 수로 `K`를 계산한다. multi-label relation을 허용하되, gold annotation에서는 주된 resolution action과 보조 relation을 구분한다.

## 4.4 Operator 결정과 `H`

각 unit에 후보 operator와 precondition을 부여한다.

```text
COMPLEMENT                 → MERGE
TEMPORAL_UPDATE            → SUPERSEDE 또는 CONDITION
SCOPE_CONDITIONED          → CONDITION
PERSPECTIVE_DISAGREEMENT   → KEEP_BOTH
CONTRADICT_FACT            → VERIFY/PREFER 또는 ABSTAIN
UNRESOLVED                 → ABSTAIN/QUALIFY
```

서로 다른 operator 종류 수로 `H`를 계산한다. 단순 type-to-action lookup이 아니라 time, scope, source dependence, evidential sufficiency를 precondition으로 검사한다.

## 4.5 전역 composition

독립적인 conflict unit은 linear operator list로 처리한다. 모든 gold/predicted unit이 적어도 하나의 operator에 연결되는지 coverage constraint를 적용한다.

```text
Plan = [operator(u_1), ..., operator(u_K)]
```

합성 시 다음 제약을 확인한다.

- 모든 high-confidence conflict unit이 처리됐는가?
- `KEEP_BOTH` 대상이 단일 답으로 축약되지 않았는가?
- `SUPERSEDE`에 time evidence가 있는가?
- `PREFER`가 duplicate document count에 의존하지 않는가?
- `MERGE`가 서로 양립하지 않는 claim을 합치지 않는가?
- 판정 불가 conflict가 과도한 확신으로 표현되지 않았는가?

## 4.6 선택적 graph와 plan search

graph는 모든 사례에 강제하지 않는다. 다음 중 하나가 나타날 때만 conflict graph를 구성한다.

- 하나의 claim/evidence group이 여러 conflict unit에 참여
- operator precondition이 다른 unit의 처리 결과에 의존
- 두 operator의 순서를 바꾸면 답이 달라질 가능성
- greedy plan의 verifier score가 임계값 이하

graph node는 claim/evidence group, edge는 relation, operator와 precedence를 attribute로 갖는다. `D=0`이면 linear plan을 사용하고, `D>0`이면 2~4개의 plan branch를 생성해 coverage, grounding, valid-alternative preservation, residual conflict 기준으로 선택한다.

## 4.7 선택적 verifier와 답 생성

관계 또는 plan이 불확실한 subgraph에만 별도 critic/verifier call을 사용한다. 전체 multi-round debate는 기본 경로로 사용하지 않는다.

선택된 plan과 evidence span을 답 생성기에 전달하고 문장별 citation을 요구한다. 생성 후 residual verifier가 미처리 conflict, unsupported claim, operator 위반을 검사하며 실패한 unit만 국소적으로 수정한다.

---

# 5. 실험 계획

## 5.1 연구 질문

- **RQ1 — 다중 충돌:** `K`가 증가할 때 conflict localization과 unit coverage가 어떻게 변하는가?
- **RQ2 — 복합 충돌:** 같은 `K`에서 `H` 증가가 단일 type routing보다 더 큰 성능 저하를 만드는가?
- **RQ3 — 해결 방법:** conflict-unit별 operator composition이 one-shot CoT와 독립 unit resolution보다 최종 답을 개선하는가?
- **RQ4 — 표현과 계획:** `D=0`에서는 linear plan이 충분하고 `D>0`에서는 graph/plan search가 추가 이점을 주는가?
- **RQ5 — 비용:** selective execution이 always-on graph 또는 multi-agent debate보다 나은 품질–비용 trade-off를 보이는가?
- **RQ6 — 일반화:** 학습 없는 schema와 resolver가 natural/synthetic dataset과 서로 다른 backbone에 전이되는가?

## 5.2 데이터셋 적합성 조사 결과

완성된 단일 데이터셋이 `K×H`, natural retrieval, action gold를 모두 제공하지는 않는다. 따라서 역할이 다른 benchmark suite를 사용한다. **검색 기반 데이터 선정은 [파일럿 1](04_pilot1_prevalence_plan.md)의 완료 결과로 종료했다. 후속 실행 순서는 [Compositional Memory Conflict 파일럿](05_pilot2_compositional_memory_plan.md)을 정본으로 하며, 아래 표는 검색 중심 초안의 후보 기록으로만 보존한다.**

| 데이터셋 | 규모·성격 | `K` | `H` | 활용 결정 |
|---|---|---:|---:|---|
| ConflictBank | 553,117 QA, synthetic, 세 conflict evidence/type | 통제 가능 | **세 유형 조합 가능** | 주 통제형 복합 충돌 source |
| RAMDocs | 500, ambiguity+misinfo+noise | 일부 | `KEEP_BOTH+REJECT` | 혼합 행동 end-to-end 평가 |
| MAGIC | 1,080, 1~4 conflict, single/multi-hop | **gold** | 거의 1 | 다중 충돌 localization 평가 |
| DRAGged/CONFLICTS | 458, 실제 web, 전문가 단일 유형 | 미주석 | instance당 1 | 자연 multi-label 재주석·유형별 평가 |
| ConfRAG | 1,814, 실제 web, answer/reason cluster | cluster 수 | 미주석 | 자연 복합 충돌 탐색·coverage |
| QACC | 1,617, 실제 Google context | answer 수 | 미주석 | 자연 factual transfer |
| DRUID | 5,490 claim-evidence sample | 해당 없음 | 해당 없음 | property·stance·sufficiency 보조 평가 |

### 선정 결론

1. **통제형 주 평가:** ConflictBank에서 type combination을 구성한 `ConflictBank-Composite`
2. **자연 주 평가:** DRAGged와 ConfRAG retrieval set을 multi-label로 재주석한 `Natural-Composite`
3. **혼합 행동 검증:** RAMDocs 원본
4. **다중 충돌 `K` 보조 평가:** MAGIC 원본
5. **자연 factual transfer:** QACC held-out subset
6. **property module 보조 평가:** DRUID

ConflictBank만으로 논문을 구성하지 않는다. synthetic composition의 통제 가능성과 natural web subset의 현실성을 함께 보고한다.

## 5.3 평가 세트 구축

### 5.3.1 ConflictBank-Composite

각 question에 연결된 default, misinformation, temporal, semantic evidence에서 다음 조합을 구성한다.

| 조건 | 포함 evidence | 목표 |
|---|---|---|
| `H=1` | 세 유형 중 하나 | single-type baseline |
| `H=2` | 세 유형 중 두 개 | pairwise composition |
| `H=3` | 세 유형 모두 | 최대 heterogeneous composition |

각 조합은 사람 검토를 거쳐 다음을 확인한다.

- claim들이 동일 질문에서 함께 제시될 수 있는가?
- type별 conflict unit이 실제로 구분되는가?
- operator가 서로 다른가?
- temporal·semantic evidence가 단순 misinformation으로 환원되지 않는가?
- 하나의 정답 선택만으로 모든 유형이 해결되지 않는가?

검토를 통과하지 못한 조합은 복합 충돌 평가에서 제외하고 single-type diagnostic에 남긴다.

`K`와 `H`를 독립적으로 통제할 수 있도록 같은 operator를 요구하는 복수 conflict claim을 추가 구성할 수 있는지 pilot에서 확인한다. 불가능하면 ConflictBank는 `H` 통제에만 사용하고 `K` 효과는 MAGIC으로 분리 보고한다.

### 5.3.2 Natural-Composite

DRAGged와 ConfRAG에서 retrieval set 단위로 다음을 주석한다.

- atomic conflict unit과 evidence span
- unit별 relation과 operator
- `K`, `H`
- evidence/source dependency
- operator precedence가 있으면 `D`
- 최종 답에 포함해야 할 content unit과 제외해야 할 content unit

DRAGged 원 논문의 protocol을 따라 2명 독립 주석, reconciliation, 제3 adjudication을 사용한다. 첫 pilot에서는 각 데이터셋에서 층화 표본을 뽑아 strict `H>1` prevalence와 multi-label agreement를 측정한다. 본 annotation 규모는 pilot prevalence와 power analysis 후 확정한다.

### 5.3.3 Split

학습은 하지 않지만 prompt와 operator rule의 과적합을 막기 위해 다음으로 분리한다.

- development: prompt/schema/threshold 결정
- held-out test: 최종 비교 전까지 비공개
- natural transfer test: QACC 또는 Natural-Composite의 별도 source split

동일 question·entity·source domain이 dev와 test에 겹치지 않도록 group split을 사용한다.

## 5.4 대상 모델

현재 H100 80GB 단일 GPU와 기존 serving 자원을 기준으로 한다.

| 모델 | 역할 | 선정 근거 |
|---|---|---|
| **Qwen3.6-27B** | 주력 open model, thinking on/off | 기존 1차 실험과 동일 모델·서빙 재사용, training-free reasoning 비교 |
| **Gemma 3 27B** | 교차 계열 open model | DRAGged가 직접 사용한 27B baseline, 단일 H100에서 실행 가능 |
| **gpt-oss-20b** | 소형 MoE generalization 또는 보조 component | 기존 환경에서 실행·파싱 검증, architecture transfer |
| **GPT-4o-mini** | 폐쇄형 비교군 | RAMDocs와 MAGIC이 직접 사용해 선행 결과와 비교 가능 |

주 결과는 Qwen3.6-27B와 Gemma 3 27B에서 모두 보고한다. GPT-4o-mini는 실행 시점에 model snapshot/API version을 고정한다. evaluated model과 automatic judge는 분리한다.

## 5.5 비교 방법

### 필수 baseline

1. **Vanilla RAG:** 검색 문서를 그대로 concat해 답 생성
2. **One-shot CoT:** property→conflict→action→answer를 한 prompt에서 지시
3. **Taxonomy-aware prompt:** DRAGged의 유형 정의를 prompt에 제공
4. **Single-type pipeline:** instance 전체에 하나의 type을 예측해 routing
5. **Independent-unit pipeline:** unit별 해결 후 단순 concat/merge
6. **MADAM-RAG 또는 공개 구현:** RAMDocs에서 multi-agent 비교

### 제안법과 ablation

7. **PCCR-Linear:** unit decomposition + operator composition, graph/search 없음
8. **PCCR-Graph-Greedy:** graph 표현, 단일 greedy plan
9. **PCCR-PlanSearch:** graph + 2~4 branch constrained plan search
10. **PCCR-Adaptive:** `K,H,D`에 따라 linear/graph/search 선택
11. **Oracle-Structure:** gold unit·relation·operator 제공
12. **Oracle-Type:** gold instance type만 제공하는 DRAGged식 upper bound

단순 graph 사용의 효과와 operator composition 효과를 혼동하지 않도록 representation과 search를 분리한다.

## 5.6 평가 지표

### Conflict structure

- conflict identification accuracy
- conflict-unit localization precision, recall, F1: MAGIC의 ID/LOC를 확장
- `K` exact match와 absolute error
- relation macro/micro F1
- operator set macro/micro F1과 exact-set accuracy
- `H` exact match와 absolute error
- precedence edge accuracy와 valid-plan rate: `D>0` subset

MAGIC은 automatic judge agreement가 충분하지 않았으므로 localization 최종 평가는 gold span 또는 사람 판정으로 수행한다.

### Final answer

- **Answer Recall:** DRAGged 방식
- **Factual Grounding:** 문장별 citation support, DRAGged/FACTS 방식
- **Expected-Behavior Adherence:** type/operator별 few-shot judge + 사람 검증
- **Exact Match:** RAMDocs 기준, 모든 gold answer를 포함하고 misinfo answer를 포함하지 않을 때 정답
- **Answer Precision/Recall/F1:** RAMDocs 방식
- **Answer/Reason Coverage:** ConfRAG 방식
- **Conflict-unit Coverage:** gold unit 중 최종 답에서 적절히 처리된 비율
- **Valid-Alternative Preservation:** `KEEP_BOTH` 대상 보존율
- **Misinformation Leakage:** 배제 대상이 답에 남은 비율
- **Residual Conflict Rate:** 해결 계획 후 처리되지 않은 core conflict 비율
- **Abstention calibration:** 해결 불가 subset에서 selective risk

### Efficiency

- input/output/reasoning token 수
- LLM call 수
- wall-clock latency
- question당 추정 비용
- `K,H,D`별 accuracy–cost Pareto frontier
- no-conflict fast-path 성능과 비용

## 5.7 Automatic judge와 사람 평가

DRAGged는 expected behavior judge를 유형별 few-shot prompt로 구성하고 100개 사람 판정에서 검증했다. 이 형식을 operator별 judge prompt로 확장한다.

최종 계획은 다음과 같다.

- 규칙으로 판정 가능한 EM, span, citation link는 deterministic evaluation
- nuanced behavior는 evaluated model과 다른 계열의 judge 2종 사용
- judge 일치 사례만 자동 확정
- 불일치와 `D>0` 사례는 사람 adjudication
- 모델별·`K×H` cell별 층화 사람 평가
- judge–human agreement와 confusion matrix 보고

LLM judge 하나의 통합 점수만으로 결론내리지 않고 component metric을 개별 보고한다.

## 5.8 실행 설정과 공정 비교

- open model은 bf16 비양자화, 동일 H100 환경
- 동일 document order seed와 최대 context
- greedy baseline과 sampling/search 조건을 분리 보고
- plan search는 고정 branch 수와 총 token budget 사용
- 동일 compute-budget 비교와 unrestricted-best 비교를 모두 수행
- 최소 5개 seed 또는 문서 순서 permutation
- 모든 raw output, intermediate JSON, prompt, model revision 기록
- evaluator prompt와 final prompt는 held-out test 실행 전에 동결

## 5.9 통계 분석

- instance-level paired bootstrap 95% confidence interval
- 주 방법 대 각 baseline의 paired permutation 또는 McNemar test
- 다중 비교는 Holm correction
- `method × K`, `method × H`, `method × D` interaction 분석
- dataset과 question을 random effect로 두는 mixed-effects analysis 검토
- overall average와 함께 각 `K×H` cell을 반드시 분리 보고

## 5.10 단계별 실행 순서

### Phase A — 데이터 타당성 pilot

1. ConflictBank type combination 100~200개 사람 검토
2. DRAGged·ConfRAG natural retrieval set 층화 표본 multi-label 주석
3. strict `H>1` prevalence와 annotation agreement 계산
4. operator taxonomy와 exclusion rule 동결

### Phase B — 방법 feasibility

1. Qwen3.6-27B로 Vanilla, CoT, PCCR-Linear 비교
2. gold structure와 predicted structure의 oracle gap 측정
3. `H>1`에서 operator composition 이점 확인
4. graph와 plan search가 `D>0`에서만 필요한지 확인

### Phase C — 본 실험

1. ConflictBank-Composite, RAMDocs, Natural-Composite, MAGIC 실행
2. Gemma 3 27B와 gpt-oss-20b로 cross-model 검증
3. GPT-4o-mini로 선행연구 비교 track 실행
4. component/answer/cost metric 집계
5. 층화 사람 평가와 통계 검정

### Phase D — 결정 기준

- natural `H>1` 사례와 IAA가 충분하면 복합 충돌을 main claim으로 유지
- natural prevalence가 낮지만 controlled interaction이 명확하면 robustness benchmark로 주장 범위 축소
- PCCR-Linear가 graph/search와 동등하면 graph를 메인 방법에서 제거
- one-shot CoT가 PCCR과 동등하면 pipeline 기여를 재검토하고 dataset/analysis contribution 중심으로 전환
- operator composition이 `H>1`에서 개선되지 않으면 복합 해결 방법 주장을 중단
