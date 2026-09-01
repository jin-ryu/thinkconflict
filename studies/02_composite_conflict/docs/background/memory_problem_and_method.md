어 그# 복합 메모리 충돌을 위한 학습 없는 단위별 정책 합성

> ACL 논문 전개용 연구 초안, 2026-08-26
> 현재 단계: 문제 정의·관련 연구·제안 방법·실험 계획
> 포함하지 않는 부분: 실험 결과, 결론, 한계
> 기존 검색 문서 conflict 연구안은 [problem_and_method.md](./problem_and_method.md)에 그대로 보존한다.
> 데이터 근거는 [dataset_evidence.md의 Part II](./dataset_evidence.md#part-ii-장기-메모리-conflict)를 따른다.
> 파일럿 실행 정본은 [pilot2_memory/plan.md](../pilot2_memory/plan.md)다.

---

## 0. 초록 초안

장기 메모리를 사용하는 LLM agent는 과거 상태, 갱신된 선호, 조건부 선호와 신뢰하기 어려운 진술을 함께 보유할 수 있다. 기존 memory-conflict benchmark는 temporal, factual, contextual 또는 irreducible conflict를 세밀하게 정의했지만, 평가 query는 주로 하나의 target attribute나 하나의 unresolved slot을 중심으로 구성된다. 실제 assistant 요청은 식당·여행·일정·구매 계획처럼 여러 사용자 상태를 동시에 요구할 수 있으며, 각 상태에는 서로 다른 resolution policy가 필요할 수 있다. 본 연구는 한 요청과 관련된 독립 memory conflict unit 수를 `K`, 필요한 서로 다른 resolution policy 수를 `H`, unit 간 유효성 의존성을 `D`로 정의한다. `K>1`을 다중 메모리 충돌, `H>1`을 복합 메모리 충돌로 구분하고, 하나의 정책을 모든 slot에 적용하는 **global-policy collapse**를 핵심 실패로 분석한다. 이를 위해 동일 persona의 공개 장기 memory history에서 `K=2,H=1`과 `K=2,H=2` matched set을 구성하고, 학습 없이 query slot을 분해하고 unit별 evidence와 policy를 판정한 뒤 하나의 응답으로 합성하는 **Compositional Memory Conflict Resolver(CMCR)**를 제안한다. 독립 unit에는 선형 계획을 사용하고 dependency가 감지된 경우에만 제한된 plan search를 수행한다. 본 연구는 데이터 구축 자체보다 query-level policy composition의 독립 난이도, unit-wise 해결 방법, 그리고 구조·행동·비용을 함께 측정하는 평가를 주요 기여로 삼는다.

실험 전까지 초록에는 성능 수치나 우월성 표현을 넣지 않는다.

---

# 1. 서론

## 1.1 배경

Personalized agent의 장기 memory에는 다음 정보가 함께 누적된다.

- 이사, 직장, 건강 상태처럼 실제로 갱신되어 이전 값을 대체해야 하는 정보
- 여행 목적, 동반자, 업무/개인 상황에 따라 달라지는 조건부 선호
- 사용자가 정정하지 않았거나 서로 다른 source가 다르게 말하는 불확실한 사실
- 삭제·철회되어 더 이상 사용하면 안 되는 정보
- 여러 번 바뀌어 단순한 latest-wins로 확정하기 어려운 행동과 선호

기존 평가는 대개 “현재 직장은 어디인가?”처럼 한 속성의 올바른 값을 복원하거나 한 conflict에 적절한 행동을 선택한다. 그러나 실제 요청은 “다음 주 가족 여행의 식당과 이동 계획을 짜줘”처럼 식이 제한, 현재 거주지, 가족 동반 조건, 예산 선호 등 여러 memory slot을 동시에 사용한다.

이때 모든 과거 정보를 최신 정보로 덮어쓰거나, 반대로 모든 불일치를 조건부로 보존하거나, 해결 가능한 slot까지 전부 사용자에게 되묻는 단일 정책은 일부 slot을 해결하면서 다른 slot을 망칠 수 있다.

## 1.2 문제 정의의 핵심

본 연구는 history 안의 conflict 총량이 아니라 **현재 query와 관련된 conflict composition**을 다룬다.

- **다중 메모리 충돌:** query-relevant conflict unit 수 `K>1`
- **복합 메모리 충돌:** 필요한 서로 다른 resolution policy 수 `H>1`
- **의존적 충돌:** 한 unit의 해결이 다른 unit의 유효성이나 행동을 바꾸는 `D>0`

`K>1,H=1`은 같은 정책을 여러 번 정확히 적용하는 coverage 문제다. `K>1,H>1`은 각 slot을 분리하고 서로 다른 정책을 적용한 뒤 한 응답으로 합성해야 하는 composition 문제다.

## 1.3 기존 연구의 공백

[MemConflict](https://arxiv.org/abs/2605.20926)는 dynamic, static, conditional conflict를 temporal, factual, contextual validity로 구분한다. [TANGLE](https://arxiv.org/abs/2608.13921)은 하나의 정답으로 환원할 수 없는 personal-memory conflict와 적응적 action을 제안한다. [STALE](https://arxiv.org/abs/2605.06527)은 명시적으로 부정되지 않은 stale memory와 관련 상태로 전파되는 invalidation을 다룬다. [Memora](https://arxiv.org/abs/2604.20006)는 obsolete memory의 재사용을 평가한다.

이 연구들은 memory conflict가 단순 retrieval 문제가 아니며 relation에 따라 행동이 달라야 함을 보여준다. 그러나 대표 instance는 주로 한 attribute, aspect 또는 conflict pair를 중심으로 평가한다. 따라서 다음 질문이 남는다.

> 하나의 요청이 여러 memory conflict unit을 동시에 필요로 할 때, 모델은 unit별로 다른 정책을 적용하고 그 결과를 하나의 일관된 답이나 계획으로 합성할 수 있는가?

## 1.4 목표 기여

본 연구는 다음 네 기여를 목표로 한다.

1. **문제 기여:** query-level `K/H/D`로 다중·복합·의존적 memory conflict를 구분하고 global-policy collapse를 정의한다.
2. **평가 데이터 기여:** 동일 persona와 하나의 사용자 목표를 유지한 `K=2,H=1`/`K=2,H=2` matched evaluation set과 unit-level evidence·policy gold를 구축한다.
3. **방법 기여:** 학습 없이 query slot과 conflict unit을 분해하고 unit별 policy를 합성하는 CMCR을 제안한다.
4. **분석 기여:** retrieval, policy selection, composition failure를 분리하고 `K/H/D`별 정확도·비용·오류 전파를 측정한다.

데이터셋 구축만을 주요 기여로 두지 않는다. 핵심은 **같은 `K`에서 policy heterogeneity가 만드는 새로운 실패를 보이고 이를 unit-wise composition으로 완화하는 것**이다.

---

# 2. 과제 정의

## 2.1 입력

시점 `t`에서 사용자 query `q`와 timestamp·source가 보존된 memory history `M_{≤t}`가 주어진다.

```text
Input = (q, M_{≤t})
```

Memory system 자체의 write/update 성능과 query-time 해결 성능을 혼동하지 않기 위해 두 track을 분리한다.

- **Oracle-memory track:** 원 memory와 gold evidence link를 제공해 resolution·composition을 측정
- **Pipeline track:** memory system이 저장·검색한 결과를 사용해 end-to-end 성능을 측정

주 방법 검증은 oracle-memory track에서 먼저 수행한다. 그래야 retrieval 실패 때문에 composition 가설이 가려지지 않는다.

## 2.2 Memory conflict unit

Conflict unit `u_i`는 다음을 만족한다.

1. query의 하나의 atomic answer/action slot과 관련된다.
2. 둘 이상의 memory claim을 동시에 그대로 적용할 수 없다.
3. 다른 unit과 별도의 resolution decision을 내릴 수 있다.
4. gold response에서 해당 unit의 해결 여부를 독립적으로 판정할 수 있다.

```text
u_i = (slot_i, claim_set_i, evidence_spans_i, relation_i, policy_i)
```

## 2.3 `K`, `H`, `D`

```text
K = number of query-relevant conflict units
H = number of distinct core resolution policies required by those units
D = dependency structure among unit validity or policy decisions
```

| 조건 | 명칭 | 예시 | 핵심 난점 |
|---|---|---|---|
| `K=1,H=1` | 단일 충돌 | 현재 주소 한 개 갱신 | 기본 resolution |
| `K>1,H=1` | 다중 충돌 | 두 outdated 상태를 모두 최신값으로 교체 | localization·coverage |
| `K>1,H>1` | 복합 충돌 | 주소는 교체하고 여행 선호는 조건별 보존 | policy 분리·합성 |
| `K>1,H>1,D>0` | 의존적 복합 충돌 | 건강 상태 갱신이 식당 선호의 적용 가능성을 변경 | dependency reasoning |

## 2.4 1차 relation과 policy

파일럿은 공개 gold와 직접 대응하는 세 policy로 시작한다.

| Memory relation | Policy | Gold behavior |
|---|---|---|
| true temporal update | `SUPERSEDE` | 최신 유효 상태를 사용하고 과거 상태를 현재값으로 사용하지 않음 |
| stable fact vs unreliable contradiction | `VERIFY_PREFER` | provenance·정합성을 비교하고 근거가 부족하면 확인 |
| context-dependent preference | `CONDITION` | 조건과 값의 연결을 보존하고 query 조건에 맞게 적용 |

다음 policy는 TANGLE 또는 자연 데이터에서 신뢰할 gold를 확보한 뒤 확장한다.

- `KEEP_BOTH`: 실제로 양립 가능한 복수 선호·관점을 보존
- `CLARIFY/DEFER`: 현재 evidence로 하나의 행동을 정당화할 수 없을 때 질문·보류
- `FORGET`: 명시적으로 삭제·철회된 정보를 사용하지 않음

관련 없는 memory filtering, duplicate 제거와 단순 retrieval 부족은 core `H`에 포함하지 않는다.

## 2.5 출력

CMCR은 최종 답뿐 아니라 평가 가능한 중간 구조를 출력한다.

```json
{
  "query_slots": ["..."],
  "conflict_units": ["..."],
  "K": 2,
  "policies": ["SUPERSEDE", "CONDITION"],
  "H": 2,
  "dependencies": [],
  "resolved_slots": ["..."],
  "answer": "..."
}
```

## 2.6 핵심 오류 taxonomy

- **Unit omission:** query에 필요한 conflict unit을 빠뜨림
- **Policy selection error:** unit을 찾았지만 잘못된 policy를 적용
- **Global-policy collapse:** 한 unit의 policy를 모든 slot에 과잉 적용
- **Cross-unit contamination:** 한 unit의 조건·불확실성·시점을 다른 unit에 전파
- **Composition inconsistency:** unit별 결과는 맞지만 최종 응답에서 서로 모순되거나 일부가 사라짐
- **Stale dependency:** 상태는 갱신했지만 downstream 행동이 과거 상태에 의존

---

# 3. 관련 연구

## 3.1 Reducible memory conflict

MemConflict는 dynamic, static, conditional conflict를 한 schema에서 진단하고 supporting-memory retrieval와 answer correctness를 분리한다. 이는 본 연구의 세 core policy와 oracle-memory 평가의 직접 기반이다. 다만 원 query는 주로 한 target attribute와 한 conflict type에 연결된다. 논문이 언급한 nested/overlapping conflict와 broader query space는 본 연구가 다루는 공백과 맞닿아 있다.

## 3.2 Irreducible personal-memory conflict

TANGLE은 context-partitioned, behavior-oscillation, source-contradiction을 정의하고 `{commit, conditionalize, clarify, verify, defer, reversible_trial}` action을 선택하는 CAAP를 제안한다. 따라서 type-aware single-action routing은 이미 선점된 방향이다. 본 연구는 하나의 unresolved slot에 적절한 action을 고르는 것이 아니라 **여러 slot의 서로 다른 action을 동시에 합성**하는 데 초점을 둔다.

## 3.3 Implicit staleness와 dependency

STALE은 co-referential update와 propagated invalidation을 State Resolution, Premise Resistance, Implicit Policy Adaptation으로 평가한다. 이는 최신 memory를 찾았어도 downstream response가 stale할 수 있음을 보인다. 본 연구에서는 Type II를 `D>0` stress test로 사용하되, STALE의 단일 conflict pair를 복합 충돌 prevalence 근거로 사용하지 않는다.

## 3.4 Long-horizon update와 forgetting

[Memora](https://github.com/geniesinc/Memora)는 수주~수개월 memory에서 obsolete information을 사용하는 오류를 FAMA로 평가한다. [HaluMem](https://github.com/MemTensor/HaluMem)은 extraction, updating, QA를 operation level로 평가하고 같은 user의 장기 history와 evidence link를 제공한다. [LongMemEval](https://github.com/xiaowu0162/LongMemEval)은 knowledge update, temporal reasoning, abstention 등을 포함한다.

이들은 현실적인 history와 질문 형식을 제공하지만 heterogeneous policy composition gold는 없다. 따라서 자연성·외부 전이 source로 사용하고 새 policy label을 자동으로 가정하지 않는다.

## 3.5 동질 다중 갱신과 task action

[MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench)의 FactConsolidation은 많은 counterfactual edit pair에 동일한 later-wins rule을 적용한다. 이는 `K>1,H=1` 통제군에 적합하다. [Mem2ActBench](https://aclanthology.org/2026.acl-long.370/)는 memory를 tool action에 반영하지만 구축 중 conflict를 해소하므로 파일럿의 conflict source가 아니라 후속 downstream transfer 후보다.

## 3.6 정리된 연구 공백

기존 연구가 이미 제공하는 것은 다음과 같다.

- conflict 유형 taxonomy
- 단일 conflict에 대한 relation-aware action
- memory update·forgetting·implicit invalidation 평가
- retrieval와 answer utilization의 분리

아직 직접 평가되지 않은 후보는 다음과 같다.

1. 한 query에 여러 conflict unit이 실제로 필요한가?
2. 같은 `K`에서 `H`가 증가하면 global-policy collapse가 나타나는가?
3. unit별로 맞는 policy를 선택해도 최종 합성에서 실패하는가?
4. 일반 CoT보다 명시적 unit-wise policy composition이 이 실패를 줄이는가?

---

# 4. 제안 방법: CMCR

## 4.1 설계 원칙

CMCR은 모델을 파인튜닝하거나 강화학습하지 않는다. 기존 LLM의 test-time reasoning을 구조화하고, 필요한 경우에만 추가 계산을 사용한다.

```text
Query + memory history
        ↓
Query-slot decomposition
        ↓
Query-conditioned memory retrieval/packing
        ↓
Conflict-unit formation
        ↓
Unit-wise relation and policy adjudication
        ↓
Dependency check
        ↓
Policy-constrained response composition
        ↓
Residual-unit verification
```

## 4.2 Query-slot decomposition

Query를 답변·행동에서 독립적으로 검증 가능한 atomic slot으로 분해한다. 단순히 명사를 나누는 것이 아니라, 각 slot이 어떤 사용자 상태나 선호를 요구하는지 명시한다.

```text
여행 계획을 짜줘
→ destination/current location
→ dietary constraint
→ companion-conditioned activity preference
→ budget preference
```

Conflict가 없는 slot도 보존하되 `K`에는 포함하지 않는다.

## 4.3 Query-conditioned evidence packing

각 slot과 관련된 memory span, timestamp, speaker/source, session identifier를 묶는다. 원 memory를 요약하면서 시간·조건·부정 표현을 잃지 않도록 evidence span을 함께 유지한다.

Oracle-memory track에서는 gold evidence를, pipeline track에서는 retrieval 결과를 사용한다. 두 결과를 분리 보고한다.

## 4.4 Conflict-unit formation

같은 slot에 적용되는 incompatible claim을 하나의 unit으로 묶는다. LLM이 모든 memory pair를 비교하지 않도록 slot, entity, attribute와 condition overlap으로 후보를 제한한다.

각 unit에 다음을 출력한다.

```text
relation
candidate policies
policy precondition
supporting evidence
unresolved information
confidence
```

## 4.5 Unit-wise policy adjudication

각 unit은 다른 unit과 독립적으로 우선 판정한다.

- `SUPERSEDE`: 실제 update이며 query가 현재 상태를 요구하는지 확인
- `VERIFY_PREFER`: 단순 recency가 아니라 source·persona consistency로 신뢰성 비교
- `CONDITION`: condition-value 연결과 현재 query condition의 일치를 확인
- `CLARIFY/DEFER`: 정답을 강제할 근거가 없는 경우에만 사용

Instance 전체에 하나의 conflict label을 먼저 고르는 global routing을 사용하지 않는다.

## 4.6 Dependency-aware composition

`D=0`이면 unit별 결과를 선형적으로 합성한다. 다음 조건에서만 dependency graph와 제한된 plan search를 활성화한다.

- 한 memory claim이 둘 이상의 slot에 참여
- 한 상태 갱신이 다른 policy의 적용 가능성을 변경
- unit별 결과를 동시에 적용하면 제약 위반
- 초안 verifier가 stale dependency 또는 cross-unit contamination을 탐지

Search는 모든 reasoning trace를 무작정 늘리지 않고 2~4개 후보 plan에 예산을 제한한다. 선택 기준은 unit coverage, policy compliance, memory faithfulness, unresolved-risk calibration이다.

## 4.7 Response composition과 verifier

최종 생성기는 unit별 resolved state와 policy constraint를 입력받는다. 이후 verifier가 다음을 검사한다.

- 모든 필수 slot이 답에 포함됐는가?
- 과거 상태가 현재값으로 되살아나지 않았는가?
- 조건부 선호가 전역 선호로 일반화되지 않았는가?
- 해결 가능한 unit까지 불필요하게 질문으로 넘기지 않았는가?
- 한 unit의 불확실성이 다른 확정 unit에 전파되지 않았는가?

실패하면 전체 답을 다시 생성하지 않고 해당 unit과 관련 문장만 수정한다.

## 4.8 방법 비교의 핵심

메인 비교는 “graph인가 아닌가”가 아니다.

1. Direct answer
2. Generic CoT
3. Taxonomy CoT
4. Single-global policy routing
5. **CMCR-Linear:** unit-wise policy composition
6. **CMCR-Adaptive:** `D>0`에서만 dependency search
7. Oracle units
8. Oracle unit policies

CMCR-Linear가 CoT보다 개선되는지가 핵심 방법 가설이다. Adaptive search는 `D>0` subset에서만 추가 기여를 검증한다.

---

# 5. 데이터 구축과 평가 계획

## 5.1 데이터 역할

| 데이터셋 | 역할 | 사용 조건 |
|---|---|---|
| MemConflict | 주 matched-set source | 동일 persona에서 자연스러운 pair가 충분할 때 |
| Memora | 자연 장기 update·forgetting 외부 검증 | query-relevant mixed pair audit 통과 시 |
| HaluMem-Medium | 같은-user raw history·evidence source | update edge와 policy를 복원할 수 있을 때 |
| STALE | implicit/propagated `D>0` stress test | prevalence 근거로 사용하지 않음 |
| FactConsolidation | `K>1,H=1` homogeneous control | query가 실제로 복수 edit pair를 요구하도록 구성 |
| TANGLE | irreducible-action 외부 검증 | 공식 artifact와 license 확보 시 |
| LongMemEval | 질문 형식과 `K=1,H=1` transfer | 서로 다른 persona item을 결합하지 않음 |
| Mem2ActBench | 후속 tool-action transfer | 파일럿 2 주 데이터에서는 제외 |

## 5.2 3단계 evaluation set

### A. Controlled matched composition

MemConflict에서 동일 persona, 하나의 사용자 목표, 같은 slot 수와 비슷한 evidence 길이를 유지해 다음을 맞춘다.

- `K=2,H=1`: 동일 policy가 필요한 두 unit
- `K=2,H=2`: 서로 다른 policy가 필요한 두 unit

주 treatment는 `H`이며 `K`, 입력 길이, evidence 수, session distance와 출력 형식을 통제한다.

### B. Dependency stress set

STALE Type II 또는 MemConflict의 연관 attribute를 사용해 `D=0`과 `D>0`을 구분한다. 이는 `H` 효과와 별도 분석한다.

### C. Natural-history transfer

Memora와 HaluMem-Medium을 schema audit한 뒤 더 적합한 하나만 선택한다. 새로운 query를 작성하더라도 원 statement, timestamp, user identity와 evidence link를 유지한다.

## 5.3 Annotation schema

각 instance는 다음을 포함한다.

```json
{
  "persona_id": "...",
  "query": "...",
  "query_slots": [],
  "conflict_units": [
    {
      "slot": "...",
      "memory_ids": [],
      "relation": "...",
      "policy": "...",
      "gold_state": "..."
    }
  ],
  "K": 2,
  "H": 2,
  "dependencies": [],
  "required_behaviors": [],
  "forbidden_behaviors": []
}
```

빠른 파일럿은 LLM 초벌과 연구자 검토로 진행한다. 논문용 benchmark로 승격할 때는 독립 human validation, IAA와 adjudication을 추가한다.

## 5.4 연구 질문

- **RQ1:** 공개 same-persona history에서 자연스러운 `K>1,H>1` query를 충분히 구성할 수 있는가?
- **RQ2:** `K=2`를 고정해도 `H=2`가 `H=1`보다 all-unit success를 낮추는가?
- **RQ3:** `H=2`에서 global-policy collapse와 cross-unit contamination이 증가하는가?
- **RQ4:** CMCR-Linear가 Generic/Taxonomy CoT보다 all-unit success와 policy compliance를 개선하는가?
- **RQ5:** `D>0`에서만 adaptive dependency search가 추가 이점을 보이는가?
- **RQ6:** oracle memory와 retrieved memory 사이의 차이가 retrieval과 resolution failure를 얼마나 설명하는가?

## 5.5 평가 지표

### 구조·정책

- query-slot recall
- conflict-unit localization precision/recall/F1
- `K/H` exact match와 absolute error
- relation·policy macro F1
- dependency edge F1

### 최종 행동

- **All-unit success**
- per-unit policy compliance
- global-policy collapse rate
- unit omission rate
- cross-unit contamination rate
- composition inconsistency rate
- stale-dependency rate
- unnecessary clarification과 unsafe commitment rate
- memory faithfulness

### 비용

- input/output/reasoning tokens
- LLM call 수
- latency
- `K/H/D`별 accuracy–cost frontier
- conflict가 없는 경우 fast-path 비용

## 5.6 모델과 실행 원칙

- 1차: 로컬에서 재현 가능한 20B~30B급 instruction/reasoning model
- 2차: 계열이 다른 open-weight 또는 API model
- deterministic 설정을 우선하고 memory order permutation을 별도 실행
- 모든 방법에 동일 context, output budget과 총 test-time token budget을 제공
- exact model identifier, revision, prompt와 generation config를 동결·공개
- 학습, 파인튜닝과 강화학습은 사용하지 않음

## 5.7 통계 분석

- matched instance 단위 paired bootstrap 95% confidence interval
- paired outcome에 McNemar 또는 permutation test
- `method × H`, `method × D` interaction 분석
- overall score뿐 아니라 policy combination별 결과 보고
- 작은 파일럿은 p-value보다 효과 방향과 반복 오류를 go/no-go 판단에 사용

---

# 6. 단계별 실행 계획

## Phase 0 — Artifact와 schema audit

1. MemConflict의 persona/history/type/attribute grouping을 확인한다.
2. HaluMem-Medium의 update edge와 direct evidence schema를 확인한다.
3. Memora의 obsolete-memory annotation과 user timeline을 확인한다.
4. TANGLE 공개 artifact와 license를 재확인한다.

## Phase 1 — 타당성 파일럿

1. MemConflict persona/history 최소 20개를 audit한다.
2. 자연스러운 `K=2,H=2` 후보 40개 이상을 생성한다.
3. 연구자 검토 후 matched pair 최소 24쌍을 동결한다.
4. Direct, Generic CoT, Taxonomy CoT, global-policy와 oracle 조건을 실행한다.
5. `H` 효과와 global-policy collapse를 확인한다.

상세 실행과 중단 기준은 [파일럿 2 계획](../pilot2_memory/plan.md)을 따른다.

## Phase 2 — 최소 방법 검증

파일럿이 go 조건을 통과한 뒤에만 구현한다.

1. CMCR-Linear를 구현한다.
2. gold structure와 predicted structure의 oracle gap을 측정한다.
3. `H=2`에서 CoT 대비 composition 개선을 확인한다.
4. STALE 기반 `D>0` subset에서 CMCR-Adaptive를 추가한다.

## Phase 3 — 외부 검증과 본실험

1. Memora/HaluMem 중 audit를 통과한 데이터에 transfer한다.
2. FactConsolidation으로 `K>1,H=1` scaling control을 수행한다.
3. TANGLE artifact가 공개되면 irreducible action composition을 추가한다.
4. 두 모델 계열, memory-order permutation과 cost-matched 비교를 수행한다.
5. human-validated evaluation과 오류 분석을 완료한다.

## Phase 4 — 주장 결정

- 자연 pair와 `H` 효과가 모두 확인되면 **Compositional Memory Conflict Resolution**을 main claim으로 유지한다.
- controlled set에서만 성립하면 현실 prevalence 주장을 제거하고 stress-test benchmark로 축소한다.
- `H`보다 `D`가 핵심이면 dependency-aware stale-memory resolution로 좁힌다.
- Generic CoT와 CMCR-Linear가 동등하면 method contribution을 재검토하고 benchmark·analysis 중심으로 전환한다.
- oracle policy에서도 회복되지 않으면 policy selection보다 response composition 또는 task construction을 수정한다.
