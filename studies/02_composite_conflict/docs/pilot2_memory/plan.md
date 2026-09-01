# 파일럿 2: Compositional Memory Conflict 타당성 검증 계획

> 작성일: 2026-08-26
> 상태: Stage A–J 완료. Stage J([stage_j_result.md](stage_j_result.md))에서 conflict 고유 간섭(H-B)과 policy 이질성 효과(H-C)가 네 모델에서 기각되어 Pilot 3 CMCR 진입 조건 미충족
> 목적: source-grounded 복합 memory query에서 atomic resolution 성공이 composite 성공을 보장하는지, evidence order와 distractor가 어떤 간섭을 만드는지 교차모델로 검증한다.
> 선행 결과: [파일럿 1 결과](../pilot1_search/result.md)
> 연구 본문: [복합 메모리 충돌 문제 정의와 방법](../background/memory_problem_and_method.md)
> 데이터 근거: [dataset_evidence.md Part II](../background/dataset_evidence.md#part-ii-장기-메모리-conflict)

---

## 0. 이 파일럿이 결정할 것

파일럿 1의 202건에서는 strict `K>1,H>1` 검색 사례가 관측되지 않았다. 따라서 검색 문서에서 prevalence를 전제한 matched comparison은 중단하고, `K/H` 문제를 long-term personalized memory로 옮긴다.

대상은 generic memory conflict나 단일 conflict-type routing이 아니다.

> 하나의 사용자 요청이 여러 query-relevant memory conflict unit을 필요로 하고, unit별로 서로 다른 policy를 적용해 하나의 일관된 응답·계획으로 합성해야 하는 문제

파일럿 2는 다음 세 전제를 순차 판정한다.

1. 동일 persona history에서 억지스럽지 않은 `K>1,H>1` query를 충분히 구성할 수 있는가?
2. 각 atomic unit은 해결하면서도 같은 unit을 합친 composite query에서 실패하는가?
3. 이 실패와 evidence-order sensitivity가 여러 모델에서 재현되고, evidence grouping·filtering·policy·verification 개입으로 회복되는가?

Stage A–G에서 첫 두 전제와 교차모델 재현을 확인했지만 `H`의 독립 효과는 확인하지 못했다. Stage H 원인 분해에서는 Qwen의 oracle accuracy recovery와 Llama의 order-robustness 개선을 확인했으나, 교차모델 accuracy recovery는 재현되지 않았다. 해결 방법은 gold-free 구성요소를 추가로 검증한 뒤 Pilot 3에서 개발한다.

---

## 1. 기존 연구와 연구 공백

### 1.1 직접 관련 연구

- [MemConflict](https://arxiv.org/abs/2605.20926): dynamic, static, conditional conflict와 supporting-memory retrieval를 평가한다. 공개 데이터는 [TaoZhen1110/MemConflict](https://github.com/TaoZhen1110/MemConflict)에 있다. 원 query는 주로 하나의 target attribute와 하나의 type을 평가한다.
- [TANGLE](https://arxiv.org/abs/2608.13921): irreducible conflict와 adaptive action을 다루지만 각 instance는 하나의 persona-aspect와 unresolved slot 중심이다. 2026-08-26 현재 공식 artifact 링크를 확인하지 못했으므로 필수 데이터 경로에서 제외한다.
- [STALE](https://arxiv.org/abs/2605.06527): implicit update와 propagated invalidation을 평가한다. 공개 자료는 [icedreamc/STALE](https://github.com/icedreamc/STALE)에 있다. 각 scenario는 한 중심 conflict pair이므로 `D>0` stress test로 사용한다.
- [Memora](https://arxiv.org/abs/2604.20006): obsolete memory 재사용과 update/forgetting을 FAMA로 평가한다. [공식 데이터와 코드](https://github.com/geniesinc/Memora)가 공개되어 자연 장기 history 외부 검증 후보다.
- [HaluMem](https://arxiv.org/abs/2511.03506): 같은 user의 장기 session에서 extraction, updating, QA와 evidence link를 제공한다. [HaluMem-Medium](https://github.com/MemTensor/HaluMem)을 먼저 audit한다.
- [MemoryAgentBench](https://arxiv.org/abs/2507.05257): FactConsolidation의 later-wins edit pair는 동일 policy를 반복하는 `K>1,H=1` 통제에 적합하다.

### 1.2 공백과 차별점

| 구분 | 기존 대표 평가 | 본 파일럿 |
|---|---|---|
| query target | 한 attribute/aspect/slot | 둘 이상의 query-relevant slot |
| conflict 수 | 한 중심 unit | `K>1` |
| policy | instance-level 한 type/action | unit별 policy 집합 `H>1` |
| 출력 | 한 값 또는 한 action | 여러 resolved unit을 합친 응답·계획 |
| 핵심 오류 | retrieval, update, underdetermination | omission, global-policy collapse, cross-unit contamination |

Conflict type을 분류해 action 하나를 routing하는 것만으로는 TANGLE과 차별화되지 않는다. 신규성 후보는 **query-level multi-policy composition**이다.

---

## 2. 조작적 정의

### 2.1 Memory conflict unit

사용자 query `q`, 시점 `t`, memory history `M_{≤t}`에서 conflict unit `u_i`는 다음을 만족한다.

1. query의 하나의 atomic answer/action slot과 관련된다.
2. 둘 이상의 memory claim을 동시에 그대로 적용할 수 없다.
3. 다른 unit과 별도의 resolution decision을 내릴 수 있다.
4. gold response에서 해결 여부를 독립적으로 판정할 수 있다.

### 2.2 `K`, `H`, `D`

- `K`: 현재 query와 관련된 독립 memory conflict unit 수
- 다중 충돌: `K>1`
- `H`: gold response에 필요한 서로 다른 core resolution policy 수
- 복합 충돌: `H>1`
- `D`: 한 unit의 상태·정책 결정이 다른 unit의 유효성에 영향을 주는 dependency

History에 conflict가 여러 개 있어도 query가 하나만 요구하면 `K=1`이다.

### 2.3 파일럿 policy 범위

1차 matched set은 MemConflict gold와 직접 대응하는 세 policy로 제한한다.

| Relation | Policy | 기대 행동 |
|---|---|---|
| true temporal update | `SUPERSEDE` | 최신 유효 상태를 사용 |
| stable fact vs unreliable contradiction | `VERIFY_PREFER` | provenance·정합성을 비교하고 불충분하면 확인 |
| context-dependent preference | `CONDITION` | 조건과 값을 분리해 query 조건에 적용 |

`KEEP_BOTH`, `CLARIFY/DEFER`, `FORGET`은 TANGLE, Memora 또는 HaluMem에서 신뢰할 gold를 확보한 뒤 확장한다. 관련 없는 memory, duplicate와 단순 정보 부족은 core `H`에서 제외한다.

### 2.4 핵심 실패 가설

주 가설은 **atomic-to-composite interference**다. 각 unit은 단독으로 해결 가능하지만, 여러 unit과 distractor가 섞인 context에서는 evidence ownership, condition selection과 최종 합성이 서로 간섭할 수 있다.

- evidence order에 따라 선택하는 preference나 distractor가 바뀜
- 한 unit의 evidence를 다른 unit의 근거로 사용함
- query 조건과 다른 preference를 선택하거나 여러 조건을 과잉 보존함
- 해결한 unit을 최종 답에서 누락하거나 서로 모순되게 합성함

**Global-policy collapse**는 가능한 하위 오류 유형이지만 주 가설은 아니다. Stage C에서 global label과 실제 행동이 불일치했기 때문에 보조 분석으로만 사용한다.

---

## 3. 파일럿 연구 질문

- **MRQ1 — Artifact feasibility:** 각 공개 데이터에서 persona, attribute, type, evidence와 timestamp를 복원할 수 있는가?
- **MRQ2 — Construction feasibility:** 동일 persona와 하나의 사용자 목표를 유지한 `K=2,H=2` query를 충분히 만들 수 있는가?
- **MRQ3 — Benchmark gap:** 원 query는 대부분 single-slot `K=1,H=1`인가?
- **MRQ4 — Atomic-to-composite gap:** 두 atomic unit이 모두 성공해도 composite all-unit success가 낮아지는가?
- **MRQ5 — Cross-model robustness:** 이 gap과 evidence-order flip이 서로 다른 모델 계열에서 재현되는가?
- **MRQ6 — Failure mechanism:** physical grouping, source filtering, condition filtering, policy와 verifier 중 무엇이 회복을 만드는가?
- **MRQ7 — H as secondary analysis:** 충분히 통제된 subset에서 `H`가 추가 설명력을 가지는가?

---

## 4. 데이터 선정과 역할

### 4.1 확정 우선순위

| 순위 | 데이터셋 | 역할 | 파일럿 포함 조건 |
|---:|---|---|---|
| 1 | MemConflict | 주 controlled matched source | 동일 persona에서 자연 pair 확보 |
| 2 | Memora | 자연 update/forgetting 외부 검증 | 원 user timeline에서 mixed pair 확인 |
| 3 | HaluMem-Medium | same-user raw history·evidence source | update edge와 policy gold 복원 가능 |
| 4 | STALE | implicit/propagated `D>0` stress test | H effect와 별도 분석 |
| 5 | FactConsolidation | `K>1,H=1` homogeneous control | query가 복수 edit pair를 실제로 요구 |
| 조건부 | TANGLE | irreducible-action 외부 검증 | 공식 artifact와 license 확보 |
| 보조 | LongMemEval | 질문 자연성·`K=1,H=1` transfer | 서로 다른 persona item 결합 금지 |
| 제외 | Mem2ActBench | 후속 task-action transfer | 원 데이터는 conflict를 해소해 구성 |

빠른 파일럿의 필수 경로는 **MemConflict matched set**이다. Memora와 HaluMem-Medium은 둘 다 본실험에 넣지 않고 schema audit 후 하나만 선택한다. TANGLE 공개를 기다리지 않는다.

### 4.2 Stage A — Artifact/schema audit

#### MemConflict

- 공개 파일 `Data/Step4_4.jsonl`의 persona/history grouping key
- conflict type, target attribute, gold answer와 supporting memory id
- 동일 persona 안의 type별 attribute 수
- 원 query가 참조하는 slot 수
- 같은 goal로 묶을 수 있는 attribute pair 수

#### Memora

- user timeline과 weekly/monthly/quarterly split
- updated/deleted memory와 obsolete-memory annotation
- remembering/reasoning/recommending query의 evidence link
- 한 query 또는 goal에서 여러 state를 함께 요구할 수 있는지

#### HaluMem-Medium

- user/session/memory-point identifier
- old/new update relation과 timestamp 복원 가능성
- QA의 direct evidence link
- consistency filtering이 conflict를 제거했는지

#### 기타

- TANGLE artifact와 license 공개 여부
- STALE Type I/II와 probe별 원자 unit schema
- FactConsolidation에서 query-relevant edit pair 수

Audit 결과는 “복합 충돌이 현실에서 흔하다”는 prevalence가 아니라 **기존 benchmark의 query coverage와 재구성 가능성**으로 보고한다.

### 4.3 Stage B — 후보 구성

주 source는 MemConflict로 제한하고 다음 절차를 따른다.

1. persona/history 최소 20개를 audit한다.
2. 서로 다른 conflict-bearing attribute 중 하나의 생활 과제로 묶을 pair를 찾는다.
3. 원 memory statement, timestamp, source와 gold relation을 보존한다.
4. 연결 문장과 multi-goal query만 최소 수정한다.
5. 빠른 구성 가능성 검증은 현재 대화의 Codex가 고정 rubric으로 직접 판정한다. 별도 로컬 LLM 판정은 후보 탐색용 예비 결과로만 취급한다.

서로 다른 persona의 무관한 query를 단순 연결하지 않는다.

### 4.4 Stage C — Matched set

논문 수준의 목표 표본은 matched pair 24쌍이다. 이번 탐색 실행에서는 24+24 controlled comparison set을 구성했지만 이를 pairwise matched set으로 부르지 않는다.

- `K=2,H=1` homogeneous: 24 instances
- `K=2,H=2` heterogeneous: 24 instances
- heterogeneous policy 조합 최소 2종, 가능하면 3종
- 조합별 최소 8 instances

우선 조합:

- `SUPERSEDE + CONDITION`
- `SUPERSEDE + VERIFY_PREFER`
- `CONDITION + VERIFY_PREFER`

| 조건 | Unit A | Unit B | `K` | `H` |
|---|---|---|---:|---:|
| Homogeneous | `SUPERSEDE` | `SUPERSEDE` | 2 | 1 |
| Heterogeneous | `SUPERSEDE` | `CONDITION` | 2 | 2 |

Pair matching 변수:

- persona·사용자 목표의 자연성
- query slot 수와 답 형식
- conflict-bearing evidence 수
- memory/session 수와 distractor 수
- input/output 길이, 목표 ±10%
- temporal/source/context cue의 명시성
- conflict distance와 evidence order

완전한 counterfactual pair가 불가능하면 nearest-neighbor matching을 사용하고 차이를 표에 공개한다. `H` 외 차이가 큰 사례는 제외한다.

### 4.5 자연성·유효성 판정표

각 후보에 다음을 기록한다.

1. 실제 사용자가 한 번에 요청할 법한 하나의 목표인가?
2. 두 slot이 모두 최종 답이나 행동에 필수인가?
3. 동일 persona와 timeline에서 성립하는가?
4. 원 conflict relation과 gold state가 보존되는가?
5. 두 unit이 독립적으로 판정 가능하면서 최종 응답에서 함께 합성되는가?
6. `H=1/H=2` 외 표면 난이도가 유사한가?
7. required behavior와 forbidden behavior가 명확한가?

빠른 파일럿의 판정자는 `OpenAI Codex interactive agent`이며 interface가 노출하는 범위에서 `GPT-5-based Codex`로 기록한다. exact deployment checkpoint는 노출되지 않으므로 재현 가능한 특정 checkpoint 판정으로 주장하지 않는다. 이번 단일 판정은 exploratory feasibility screen이며 사람 간 일치도나 독립 검증을 대체하지 않는다. 논문용 데이터로 승격할 때 blind human validation, IAA와 adjudication을 추가한다.

---

## 5. 비교 조건

파일럿에서는 학습·파인튜닝·강화학습을 하지 않는다.

1. **Direct answer:** memory와 query만 제공
2. **Generic CoT:** 관련 memory를 비교하고 conflict를 해결하라는 일반 지시
3. **Taxonomy CoT:** 세 policy 정의를 제공하되 unit 구조는 제공하지 않음
4. **Single-global policy:** instance 전체에 하나의 policy만 선택·적용
5. **Oracle units:** gold conflict unit과 evidence group을 제공
6. **Oracle unit policies:** unit별 gold policy까지 제공하고 합성만 수행

파일럿에서는 CMCR, agent, graph와 plan search를 구현하지 않는다. `Oracle unit policies`에서 회복 가능성이 보이고 non-oracle 조건에서 composition failure가 확인된 뒤에만 [새 연구 본문](../background/memory_problem_and_method.md)의 CMCR-Linear를 개발한다.

---

## 6. 모델과 실행 설정

- 1차 모델: `mistralai/Mistral-Small-3.2-24B-Instruct-2506`
- 2차 재현: 계열이 다른 open-weight 또는 API model 1개
- temperature 0 또는 가능한 deterministic 설정
- 동일 max output tokens, prompt budget과 memory context
- memory order permutation 3개
- oracle 조건 외 gold unit/policy 비공개
- exact model identifier, revision, prompt, generation config와 raw output 저장

1차 실행 설정은 `results/pilot2_memory/run_manifest.yaml`에 동결했다. 2차 모델과 memory-order permutation은 후속 검증으로 남긴다.

---

## 7. 평가와 분석

### 7.1 주 지표

- **All-unit success:** 모든 query-relevant unit에서 gold behavior 충족
- **Per-unit policy compliance**
- **Global-policy collapse rate**
- **Unit omission rate**
- **Cross-unit contamination rate**
- **Composition inconsistency rate**

### 7.2 보조 지표

- memory faithfulness
- invalid overwrite / invalid preservation
- unnecessary clarification / unsafe commitment
- stale-dependency rate: `D>0` stress set
- token, latency와 model call 수

### 7.3 판정

- 규칙으로 확인 가능한 gold state, forbidden memory 사용과 slot coverage는 deterministic evaluator 사용
- policy adherence와 응답 자연성은 rubric 기반 LLM 판정
- 파일럿 구성 가능성은 Codex 직접 판정, 모델 출력 평가는 deterministic rule과 별도 judge를 분리
- 논문용 결과는 blind human evaluation 또는 human-validated judge 사용

### 7.4 주 분석

```text
Delta_H = AllUnitSuccess(K=2,H=2) - AllUnitSuccess(K=2,H=1)
```

- matched pair paired bootstrap 95% confidence interval
- paired binary outcome는 McNemar test
- 작은 파일럿에서는 유의확률보다 효과 방향과 반복 오류를 우선 판단
- policy combination별 결과와 memory-order 민감도를 별도 보고

`D` 효과는 STALE stress set에서 별도 분석하고 `H` 효과와 합치지 않는다.

---

## 8. Go / revise / stop 기준

### 8.1 논문 수준 construction go

다음을 모두 만족해야 논문 수준의 본실험과 인과 주장으로 진행한다. 이번 24+24 실행은 이 기준을 채우기 전 방법론 headroom을 확인한 탐색 실험이다.

1. 자연스러운 `K=2,H=2` 후보 40개 이상
2. 검토 통과 matched pair 24쌍 이상
3. 최소 두 policy combination, 조합당 8개 이상
4. 동일 persona·goal과 원 gold relation 보존
5. 큰 confound 없이 `K`, slot 수와 길이를 맞출 수 있음

### 8.2 Method go

다음 패턴이 확인되면 본 방법 개발로 진행한다.

1. Direct 또는 Generic CoT에서 `H=2`의 all-unit success가 일관되게 낮음
2. `H=2`에서 global-policy collapse 또는 cross-unit contamination이 반복됨
3. Oracle unit policies가 non-oracle baseline보다 명확히 회복됨
4. 오류가 단순 retrieval 실패나 query 길이만으로 설명되지 않음

`-8%p`, `+10%p` 같은 수치는 사전 검정력 없는 파일럿의 과학적 임계값으로 사용하지 않는다. 효과 방향, confidence interval과 오류 재현성을 함께 기록한다.

### 8.3 Revise

- 후보는 충분하지만 `H` 효과가 작으면 `D`, implicitness와 conflict distance를 보조축으로 검토
- oracle도 실패하면 response composition 또는 annotation rubric 수정
- matching이 어렵지만 자연성은 높으면 인과 비교 대신 controlled stress benchmark로 범위 축소
- MemConflict가 부족하면 Memora/HaluMem audit 결과 중 하나를 보조 construction source로 승격

### 8.4 Stop 또는 전환

- 자연스러운 후보가 12개 미만
- 대부분 무관한 두 질문을 인위적으로 연결해야 함
- `H=1/H=2`에서 일관된 성능·오류 차이가 없음
- oracle policy도 회복을 만들지 못함
- 후속 연구가 동일한 multi-slot policy composition과 해결 방법을 이미 공개함

이 경우 다음 중 관측 근거가 강한 방향으로 좁힌다.

- dependency-aware stale-memory resolution
- implicit policy adaptation
- controlled worst-case compositional benchmark

---

## 8.5 Pilot 2B — 현재 실험의 통제 검증

Pilot 2B는 새로운 연구 주제를 탐색하는 별도 파일럿이 아니다. 현재 24+24 feasibility set에서 발견한 Direct 성능 차이와 oracle recovery가 `H` 이외의 난이도 차이로 설명되는지 확인하는 보강 단계다. 기존 instance와 raw output은 감사용으로 보존하고, 검증된 paired set의 결과만 본실험 설계에 사용한다.

### 8.5.1 검증 질문

1. `K=2`, query slot 수와 표면 난이도를 맞춘 뒤에도 `H=2`에서 all-unit success가 낮아지는가?
2. 같은 evidence를 unit별로 분리하거나 policy를 제공하면 성능이 회복되는가?
3. 실패가 단순 길이·retrieval 차이가 아니라 policy composition에서 발생하는가?

### 8.5.2 데이터 보강 원칙

- 기존 `H=2` 24건을 출발점으로 사용하되 자동 생성 결과를 그대로 gold로 인정하지 않는다.
- source-grounded natural matching을 먼저 시도한다. 동일 persona·goal에 가까운 `H=1` 후보를 MemConflict에서 찾고 원 timestamp, conflict relation과 answer를 보존한다.
- exact natural pair가 없는 사례를 억지로 연결하지 않는다. 이 경우 controlled counterfactual variant를 별도 층으로 만들고 `natural matched`와 `counterfactual controlled` 결과를 분리 보고한다.
- counterfactual variant는 한 unit의 policy만 바꾸는 최소 변형으로 만들며, 값·조건·시점 단서는 원 MemConflict evidence에서 가져온다.
- query에서 gold state를 직접 노출하지 않고, 한 unit을 제거하면 정답을 완성할 수 없는지 unit deletion test를 수행한다.

### 8.5.3 필수 matching 변수

| 변수 | 기준 |
|---|---|
| `K`와 answer slot | 모두 2로 동일 |
| query goal·답 형식 | 같은 task family와 출력 형식 |
| relevant evidence 수 | pair 간 차이 1개 이하 |
| 전체 context record 수 | pair 간 차이 1개 이하 |
| input token 길이 | 상대 차이 10% 이하 목표 |
| distractor 수·종류 | 동일하거나 차이를 명시 |
| temporal/context cue 명시성 | 동일 rubric 등급 |
| evidence order | 같은 permutation 사용 |
| unit별 단독 난이도 | single-unit probe 성능으로 보정 |

### 8.5.4 실행 순서

1. 기존 48건에 matching covariate와 single-unit probe를 추가한다.
2. `H=2` 각 사례에 natural `H=1` 후보를 최대 3개 검색하고 blind rubric으로 하나를 선택한다.
3. natural match가 불가능한 사례는 counterfactual controlled set으로 분리한다.
4. query uniqueness, unit necessity, gold compatibility와 source-grounding audit를 다시 수행한다.
5. pair와 evidence-order permutation을 동결하고 새 version을 run manifest에 기록한다.
6. Direct, Generic CoT, Taxonomy CoT, Oracle units와 Oracle unit policies를 동일 설정으로 재실행한다.
7. paired all-unit success, unit별 오류, oracle recovery와 order sensitivity를 계산한다.

`Single-global policy`는 기존 실행에서 label과 실제 행동이 불일치하는 instruction-following confound가 확인됐으므로 주 비교에서 제외하고 보조 분석으로만 유지한다.

### 8.5.5 Pilot 2B 결정 기준

다음을 모두 만족하면 CMCR-Linear 최소 구현으로 진행한다.

1. natural matched 또는 counterfactual controlled set 중 하나 이상에서 Direct/Generic CoT의 `H=2` 열세가 반복된다.
2. 오류가 두 개 이상의 모델 또는 evidence-order permutation에서 재현된다.
3. Oracle unit policies가 non-oracle 조건보다 명확하게 회복된다.
4. single-unit probe는 성공하지만 두 unit을 합쳤을 때 실패하는 composition-specific 사례가 반복된다.

matching 후 차이가 사라지면 현재 20.8%p 차이는 `H` 효과로 주장하지 않는다. 이 경우 방법 개발보다 dataset construction confound를 결과로 보고하고, dependency `D`나 implicit condition activation처럼 더 직접적인 난이도 축으로 연구 질문을 수정한다.

### 8.5.6 산출물 위치

새 파일럿 폴더를 만들지 않고 기존 파일럿 2 아래에서 version을 분리한다.

```text
data/pilot2_memory/stage2_matched/
├── matching_candidates.jsonl
├── matched_instances_h1.jsonl
├── matched_instances_h2.jsonl
├── single_unit_probes.jsonl
└── validation.jsonl

results/pilot2_memory/stage2_matched/
├── run_manifest.yaml
├── raw/
├── semantic_judgments.jsonl
└── metrics.json
```

---

## 9. 산출물

```text
data/pilot2_memory/
├── source_audit.jsonl
├── schema_report.md
├── query_candidates.jsonl
├── matched_pairs_draft.jsonl
├── instances_h1_oracle_retrieval.jsonl
├── instances_h2_oracle_retrieval.jsonl
└── codex_direct_reviews_{h1,h2}.jsonl

results/pilot2_memory/
├── run_manifest.yaml
├── raw/baseline_outputs.jsonl
├── lexical_screen.jsonl
├── semantic_core_judgments.jsonl
└── semantic_core_metrics.json

docs/pilot2_memory/
└── result.md
```

---

## 10. 실행 체크리스트

### Stage A — 데이터 확인

- [x] MemConflict `Step4_4.jsonl`을 내려받고 schema를 기록한다.
- [x] persona/history/type/attribute별 분포를 계산한다.
- [ ] Memora update/deletion·obsolete annotation을 확인한다.
- [ ] HaluMem-Medium update edge와 evidence link를 확인한다.
- [ ] 두 후보 중 자연 외부 검증 source 하나를 선택한다.
- [ ] TANGLE artifact 공개 여부를 기록하되 기다리지 않는다.

### Stage B — 데이터 구성

- [x] MemConflict persona/history 최소 20개를 audit한다.
- [x] same-persona `H=2` 후보 모집단과 enriched review sample 40개를 만든다.
- [x] Codex 직접 판정으로 `H=2` 40건의 자연성·필수성·gold 보존 표를 채웠다(24건 통과).
- [x] `K=2,H=1`/`K=2,H=2` controlled comparison set을 각각 24건 동결한다.
- [x] required/forbidden behavior와 unit evidence를 기록한다.
- [x] natural matching을 재설계했으나 strong pair가 4쌍뿐이라 causal matched set 주장은 포기했다.

### Stage C — 모델 실행

- [x] run manifest와 평가 prompt를 동결한다.
- [x] Direct, Generic CoT, Taxonomy CoT와 global-policy 조건을 실행한다.
- [x] Oracle units와 Oracle unit policies를 실행한다.
- [x] reverse memory-order permutation을 실행했다.

### Stage D — 결정

- [x] 탐색 set의 all-unit success와 기술적 `Delta_H`를 계산한다.
- [x] 핵심 실패 유형을 의미 검토한다.
- [x] oracle recovery와 retrieval-independent failure headroom을 확인한다.
- [x] 현재의 조건부 method-go 판단을 `result.md`에 기록한다.
- [ ] 두 번째 모델·human validation 후 최종 go/revise/stop을 결정한다.
- [ ] 검증 후 CMCR-Linear 최소 구현을 시작한다.

### Stage E — Pilot 2B matched validation

- [x] 기존 48건의 matching covariate와 96개 single-unit probe를 만들었다.
- [x] natural matching을 수행해 strong 4, moderate 5, weak 제외 15로 구분했다.
- [x] source-grounded 최소 변형을 보장할 수 없어 counterfactual layer는 만들지 않기로 결정했다.
- [x] 기존 frozen query의 uniqueness·unit necessity·gold compatibility를 유지하고 atomic probe를 감사했다.
- [x] 동일 모델의 reverse evidence-order baseline·oracle 240회를 재실행했다.
- [ ] 계열이 다른 두 번째 모델에서 atomic·composite 실험을 재현한다.
- [x] natural-match 결과와 atomic-to-composite failure를 분석했다.
- [x] cross-model 기준은 아직 미충족이므로 CMCR-Linear 구현을 보류했다.


---

## 11. 수정 실행 계획: 교차모델 재현과 데이터 확장

### 11.1 Pilot 번호 결정

이 단계는 새 Pilot 3으로 분리하지 않고 Pilot 2를 확장한다. 문제 정의, MemConflict-derived instance, atomic-to-composite protocol과 평가 지표를 그대로 사용하기 때문이다. Pilot 3은 아래 Stage F–H의 gate를 통과한 뒤 **CMCR 해결 방법론 자체를 개발·평가할 때만** 시작한다.

```text
Pilot 2A  문제·구성 가능성 확인                    완료
Pilot 2B  single-unit·evidence-order 통제          완료
Pilot 2C  교차모델 재현(Stage F)                   완료
Pilot 2D  K/H factorial 150개 확장(Stage G)       완료
Pilot 2E  원인 분해와 방법 요구사항 확정(Stage H)  완료·조건부 revise
Pilot 2F  데이터 보강(Stage I)                     완료: I-1 통제군, I-2 anchor 짝 (I-3~I-5 미구축)
Pilot 2G  간섭 검증·독립 null·policy leakage(Stage J)  완료: H-B·H-C 기각, stage_j_result.md
Pilot 3   CMCR-Linear 방법 개발·본실험             진입 조건 미충족. 방향 재설정 필요
```

### 11.2 Stage F — 현재 24건의 교차모델 재현

#### 목적

현재 Mistral 한 모델에서 관측한 atomic-to-composite gap과 evidence-order flip이 모델 특이 현상인지 먼저 판정한다. 대규모 데이터 구축 전에 수행하는 비용 제한 gate다.

#### 모델 구성

- 현재 모델: `mistralai/Mistral-Small-3.2-24B-Instruct-2506`
- 추가 모델: 서로 다른 계열 2개
- 최소 한 모델은 강한 general-purpose instruction/reasoning model로 선택
- exact identifier, revision, context length, serving 방식과 license를 run manifest에 기록
- 가능한 deterministic 설정과 동일 prompt·token budget 사용

실행 모델은 `Qwen/Qwen3-8B`와 `openai/gpt-oss-20b`로 동결했다. exact revision과 추론 통제는 [Stage F run manifest](../../results/pilot2_memory/stage_f_cross_model/run_manifest.yaml)에 기록했다.

Stage F의 세 모델은 feasibility와 model-family replication을 위한 구성이다. 메모리 연구의 대표 모델 패널이라는 의미는 아니다. Stage G의 주력 패널은 다음처럼 문헌 비교 가능성을 보강한다.

| 모델 | Stage G 역할 | 선정 근거 |
|---|---|---|
| `Qwen/Qwen3-8B` | 효율적인 주력 open model | MemBench가 Qwen2.5-7B를 공통 memory baseline으로 사용한 계열 연결성 |
| `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4` | memory-literature 계열 anchor와 강한 공개 모델 재현 | LongMemEval의 Llama 3.1 계열 연결성; 실제 로컬 artifact는 70B AWQ INT4이며 동일 규모 비교로 해석하지 않음 |
| `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | 더 큰 open model 및 계열 일반화 | LoCoMo의 Mistral 계열 선례와 기존 Stage C 결과 연결 |

`openai/gpt-oss-20b` 결과는 Stage F의 architecture-transfer 보조 결과로 유지하되 Stage G 주 결과의 문헌 anchor로 사용하지 않는다. 최종 본실험에서는 제출 시점의 강한 API model 한 종으로 핵심 subset을 재검증해 작은 open model의 capability ceiling을 배제한다.

#### F1 — Direct replication screen

추가 모델당 다음 96회를 실행한다.

| 조건 | 수 |
|---|---:|
| H2 atomic Direct | 48 |
| H2 composite original Direct | 24 |
| H2 composite reverse Direct | 24 |
| 모델당 합계 | 96 |

추가 모델 2개의 F1 총량은 192 calls다.

#### F2 — Oracle headroom

F1에서 composition failure가 관측된 모델에만 실행한다.

| 조건 | 모델당 수 |
|---|---:|
| H2 original Oracle unit policies | 24 |
| H2 reverse Oracle unit policies | 24 |
| 모델당 합계 | 48 |

두 모델 모두 F2로 진행하면 96 calls이며 Stage F 전체 최대치는 288 calls다.

#### 교차모델 replication gate

다음을 모두 만족하면 Stage G로 진행한다.

1. 세 모델 중 최소 두 모델에서, 두 atomic unit은 성공하지만 composite가 실패하는 instance가 반복된다.
2. 모델별로 최소 3개 instance 또는 10% 이상의 composition-specific failure가 관측된다. 이 수치는 통계적 유의성 기준이 아니라 데이터 확장 여부를 위한 운영 gate다.
3. 잘못된 preference·distractor 선택, condition over-preservation 또는 cross-unit contamination 중 하나 이상이 두 모델에서 공통으로 나타난다.
4. evidence-order flip이 모델 하나에만 국한되지 않는다.

한 추가 모델에서만 재현되면 Stage G를 축소하고 세 번째 모델을 먼저 확인한다. 추가 모델 모두에서 거의 재현되지 않으면 일반 현상 주장을 중단하고 Mistral-specific failure analysis 또는 데이터 설계 재검토로 전환한다.

### 11.3 Stage G — K/H factorial 데이터 확장

Stage F gate를 통과한 경우에만 실행한다. H2 사례만 100–150건으로 늘리지 않고, K와 H의 효과를 분리할 수 있는 factorial design을 구축한다.

#### 핵심 cell

| K | H | policy 구조 예시 | 역할 |
|---:|---:|---|---|
| 1 | 1 | A | atomic baseline |
| 2 | 1 | A+A | K 증가, homogeneous policy |
| 2 | 2 | A+B | K=2에서 H 효과 |
| 3 | 1 | A+A+A | 순수 K 증가 |
| 3 | 2 | A+A+B | K=3에서 부분 heterogeneity |
| 3 | 3 | A+B+C | K=3에서 완전 heterogeneity |

- A: `SUPERSEDE`
- B: `CONDITION`
- C: `VERIFY_PREFER` 또는 source-grounded gold가 확보된 세 번째 policy

`K=1,H=1`은 각 composite를 구성하는 atomic probe를 paired control로 사용한다. 주요 composite cell은 나머지 5개다.

#### 검증할 효과

```text
K effect at H=1:
(K=1,H=1) → (K=2,H=1) → (K=3,H=1)

H effect at K=2:
(K=2,H=1) → (K=2,H=2)

H effect at K=3:
(K=3,H=1) → (K=3,H=2) → (K=3,H=3)
```

H를 증가시키면서 K도 함께 증가한 결과를 H effect로 해석하지 않는다.

#### 목표 규모

- 최소: 주요 composite cell당 30건, 총 150건
- 권장: cell당 50건, 총 250건
- 모든 composite에 K개의 atomic probe를 생성
- 각 base composite에 evidence-order variant 3개 생성
- permutation과 baseline 출력은 독립 표본으로 세지 않음

#### policy identity 통제

H가 특정 policy의 난이도와 혼동되지 않도록 가능한 조합을 cell 내부 strata로 기록한다.

- `K=2,H=1`: A+A, B+B, C+C
- `K=2,H=2`: A+B, A+C, B+C
- `K=3,H=1`: A+A+A, B+B+B, C+C+C
- `K=3,H=2`: A+A+B, A+B+B와 가능한 A/C·B/C 변형
- `K=3,H=3`: A+B+C와 unit/evidence order permutation

모든 subgroup을 같은 수로 맞추기 어렵다면 policy identity를 공개하고 stratified 결과와 mixed-effects 분석에서 보정한다. A+B만으로 H2 전체를 대표하지 않는다.

#### 세 번째 policy feasibility gate와 taxonomy 범위

1. MemConflict에서 `VERIFY_PREFER`가 포함된 same-persona composition 가능성을 먼저 audit한다.
2. 부족하면 Memora 또는 HaluMem에서 provenance·uncertainty gold를 복원할 수 있는지 확인한다.
3. source-grounded C를 cell당 최소 30건 확보하지 못하면 `H=3`을 억지로 만들지 않는다. 이 경우 본 논문 범위를 `H≤2`와 temporal-update/contextual-preference composition으로 축소하고, 핵심 composite 규모는 4개 cell × 30–50건인 120–200건으로 조정한다.
4. MemConflict가 제공하는 validity dimension은 temporal, factual, contextual 세 가지이므로 이 benchmark 안에서 최대 이질성은 `H=3`이다. 네 번째 연산을 임의로 추가한 `H=4`는 만들지 않는다.
5. 세 유형은 memory conflict 전체의 완전한 taxonomy로 주장하지 않는다. 핵심 주장은 **세 foundational validity dimension 안에서의 heterogeneous operator composition**으로 한정한다.
6. 범위 밖 일반화는 H의 숫자를 인위적으로 늘리는 대신 다음 두 검증으로 다룬다.
   - 한 policy-pair 조합을 방법 설계에서 제외한 뒤 unseen combination에 transfer하는 조합 일반화
   - artifact가 확보되면 STALE 또는 TANGLE의 implicit/unresolvable conflict에 대한 외부 유형 전이

#### 데이터 계층

Stage G의 실제 구현은 다음 한 계층이다.

1. **Controlled cross-session composition layer**: 동일 persona의 source-grounded atomic fact·timestamp·answer·evidence를 보존하고 compound query와 evidence order만 구성

이는 natural prevalence layer가 아니다. 향후 실제 하나의 goal에서 K개 unit이 필요한 same-session 사례를 확보하면 별도 natural layer로 추가하며 두 결과를 합치지 않는다.

새로운 사용자 사실, timestamp, conflict relation과 atomic gold를 발명하지 않는다. Combined query와 composition gold만 작성한다.

#### 후보 수집과 cherry-picking 방지

- MemConflict의 same-session pair와 triple pool을 각각 구축한다.
- random audit sample과 high-recall targeted sample을 분리한다.
- random sample은 composability 비율과 탈락 이유 추정에만 사용한다.
- targeted sample은 benchmark 규모 확보에 사용하되 prevalence 추정에 사용하지 않는다.
- persona당·session당 상한을 두어 특정 사용자나 domain 과대표집을 방지한다.

#### annotation과 품질 관리

- LLM 초벌: K개 unit 필요성, query 자연성, source grounding과 gold compatibility
- Codex/연구자 검토: 모든 후보의 unit deletion test와 condition uniqueness
- 논문용 승격 전: 무작위 subset의 blind human validation과 IAA
- unit 하나를 제거해도 같은 답을 낼 수 있거나 query가 gold state를 직접 노출하면 제외
- 같은 persona의 관련 instance는 분석 시 cluster로 묶음

### 11.4 Stage G 실행 규모와 순서

최소 설계인 composite cell당 30건에서는 150개 base composite가 생성된다.

| 구성 | 수 |
|---|---:|
| K=2 composite: 2 cells × 30 | 60 |
| K=3 composite: 3 cells × 30 | 90 |
| atomic probes, 중복 제거 전 | 390 |
| composite 3 evidence orders | 450 |
| 모델당 최대 Direct calls | 840 |
| 모델 3개 | 2,520 |

권장 설계인 cell당 50건에서는 250개 base composite이며, 중복 제거 전 모델당 atomic 650회와 composite 750회로 최대 1,400 calls다. 동일 atomic unit이 여러 composite에 재사용되면 probe 결과를 공유하되 데이터 의존성을 기록한다.

모든 baseline을 처음부터 실행하지 않고 다음 funnel을 따른다.

1. 3개 모델에서 atomic과 mixed-evidence Direct
2. K/H cell별 gap과 order flip 확인
3. 고정 평가셋에서 원인 분해 조건 실행
4. 방법 확정 후에만 전체 baseline·ablation 실행

### 11.5 Stage H — 원인 분해

확장한 동일 base instance에 다음 개입을 적용한다.

| 조건 | 분리하려는 원인 |
|---|---|
| mixed evidence | 현재 end-to-end 성능 |
| physically unit-grouped evidence | cross-unit contamination |
| other-person distractor 제거 | source ownership 오류 |
| non-matching preference 제거 | condition selection 오류 |
| grouped evidence + unit policy | local resolution headroom |
| 위 조건 + composition verifier | 합성·coverage 오류 |

현재 Oracle units는 evidence ID를 알려줄 뿐 context를 물리적으로 분리하지 않으므로, `physically unit-grouped evidence`를 별도 구현해야 한다.

#### 주요 지표

- atomic-to-composite success gap
- all-unit success
- `H=1`에서의 K marginal effect와 monotonic trend
- `K=2`와 `K=3`을 고정한 H marginal effect
- policy identity subgroup별 stratified effect
- K×H interaction
- composition-specific failure rate
- answer flip rate across evidence orders
- worst-order accuracy와 order consistency
- wrong-owner/distractor selection rate
- condition over-preservation과 cross-unit contamination
- oracle/grouping/verifier recovery
- token, latency와 call 수

통계 단위는 base composite instance다. permutation을 독립 샘플로 취급하지 않고 instance·persona cluster bootstrap confidence interval을 사용한다.

### 11.6 Pilot 3 진입 조건

2026-08-28 개정. 원래의 다섯 조건 중 1·2는 Stage G–H에서 충족했고, 3(H3 30건)은 충족, 4(교차모델 회복)는 미충족, 5는 미검증이다. 관련 연구 조사([related_work_memory_2026.md](../background/related_work_memory_2026.md))에서 확인한 독립 실패 null model(2608.12426)과 policy identity confound 때문에 진입 조건을 다음으로 교체한다. 상세는 [Stage I–J 계획](stage_ij_plan.md)에 있다.

1. J-0: frontier API 모델에서도 worst-order all-unit success < 80%이고 composition-specific failure ≥ 10%
2. J-1: composite 안의 unit별 정확도가 같은 unit의 atomic 정확도보다 유의하게 낮음 (세 모델 중 둘 이상)
3. J-2: no-conflict 통제군 `K*_C0`에서는 그 gap이 유의하게 작음
4. J-3(anchor 짝에서 different-policy 조건이 유의하게 낮음) 또는 J-4(heterogeneous cell에서 policy leakage 비율이 높음) 중 하나 이상

Pilot 3의 목적은 발견 재검증이 아니라, Stage H·J에서 확인된 원인에 맞춘 최소 학습 없는 CMCR-Linear를 구현하고 Direct, CoT, CAR-style 분해, oracle과 비교하는 것이다.

### 11.7 새 실행 체크리스트

#### Stage F — 교차모델 재현

- [x] 실행 가능한 서로 다른 모델 계열 2개를 확인하고 manifest에 동결했다.
- [x] Qwen3-8B와 gpt-oss-20b에서 atomic 48개와 original/reverse composite를 Direct로 실행했다.
- [x] composition-specific failure와 order flip을 의미 평가했다.
- [x] 두 모델에 Oracle unit policies를 실행했다.
- [x] cross-model replication gate를 통과했다. 상세 결과는 [Stage F 결과](stage_f_result.md)에 있다.

#### Stage G — 데이터 확장

- [ ] random audit와 targeted candidate frame을 분리한다.
- [x] `K=2,H=1/2`, `K=3,H=1/2/3` 주요 5개 composite cell을 cell당 30건 확보했다.
- [x] 각 K-way composite의 atomic controls와 3개 evidence-order variant를 생성했다.
- [x] `VERIFY_PREFER`를 포함한 source-grounded H3를 30건 확보해 feasibility gate를 통과했다.
- [x] MemConflict의 세 validity dimension을 핵심 범위로 고정하고, 근거 없는 H4 구성을 제외한다.
- [ ] held-out policy combination과 외부 conflict type transfer protocol을 동결한다.
- [x] 30 persona와 policy identity/multiset 분포, extraction 탈락 171건을 기록했다.
- [ ] unit deletion, condition uniqueness와 gold compatibility audit를 수행한다.
- [x] 세 생성 모델 Direct와 evidence-aware cross-model semantic evaluation을 완료했다.
- [x] 상세 결과와 판정 protocol audit을 [Stage G 결과](stage_g_result.md)에 기록했다.

#### Stage H — 원인 분해와 방법 결정

- [x] outcome-blind cell-balanced 50 base와 150 order trial을 동결했다.
- [x] physically grouped evidence condition을 구현했다.
- [x] distractor·non-matching preference 제거 ablation을 구현했다.
- [x] unit policy와 composition verifier의 추가 회복을 측정했다.
- [x] base-instance worst-order 지표와 order consistency를 계산했다.
- [x] Qwen 스크린과 Llama 생성·Qwen 판정 교차모델 복제를 완료했다.
- [x] Pilot 3 판단을 조건부 revise로 결정했다. 상세 결과는 [Stage H 결과](stage_h_result.md)에 있다.

Qwen에서는 oracle `full_local`이 28.0%에서 52.7%로 회복했지만 Llama에서는 45.3%에서 46.7%로 정확도 이득이 재현되지 않았다. 다만 Llama의 order flip은 30%에서 14%로 감소했다. 따라서 gate 4의 교차모델 accuracy recovery는 아직 충족하지 못했으며, `full_local` prompt를 최종 방법으로 승격하지 않는다. 다음 단계는 gold-free unit assignment·target selection·policy inference의 소규모 screen과 blind human validation이다.
