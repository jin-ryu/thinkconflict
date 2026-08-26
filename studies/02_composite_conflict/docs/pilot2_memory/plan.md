# 파일럿 2: Compositional Memory Conflict 타당성 검증 계획

> 작성일: 2026-08-26
> 상태: 실행 전
> 목적: 장기 사용자 메모리가 검색 문서보다 `K>1,H>1`의 현실적 검증 환경인지 확인하고, 기존 memory-conflict 연구가 다루지 않은 query-level composition failure가 존재하는지 최소 비용으로 검증한다.
> 선행 결과: [파일럿 1 결과](../pilot1_search/result.md)

## 0. 연구 방향 결정

기존 파일럿 2였던 “자연 검색 사례에서 `K`를 고정하고 `H` 효과를 비교”하는 실험은 수행하지 않는다. 파일럿 1의 202건에서 strict `K>1,H>1` 사례가 한 건도 관측되지 않아 자연 matched comparison의 전제가 충족되지 않았기 때문이다.

대신 `K/H` 정의는 유지하면서 적용 환경을 **long-term personalized memory**로 옮길 수 있는지 검증한다. 이것은 generic memory conflict 연구가 아니라 다음의 좁은 문제를 대상으로 한다.

> 하나의 사용자 요청에 여러 query-relevant memory conflict unit이 관련되고, 각 unit에 서로 다른 resolution policy를 적용해 하나의 일관된 응답이나 계획으로 조합해야 하는 문제

이 파일럿은 새 방법의 성능을 확증하는 본실험이 아니다. 다음 두 전제를 먼저 확인하는 go/no-go 실험이다.

1. memory history와 자연스러운 사용자 요청에서 `K>1,H>1`을 억지스럽지 않게 구성할 수 있는가?
2. 같은 `K`에서도 `H`가 증가하면 기존 모델에 **global-policy collapse**가 나타나는가?

---

## 1. 기존 연구와 남은 공백

### 1.1 MemConflict

[MemConflict](https://arxiv.org/abs/2605.20926)는 dynamic, static, conditional conflict를 각각 시간적 유효성, 사실적 정확성, 맥락 적합성 문제로 정의한다. 한 사용자 history에는 여러 형태의 정보가 누적될 수 있지만, 평가 query는 하나의 target attribute와 하나의 conflict type에 연결되며 unique answer를 복원한다. 논문도 nested or overlapping conflicts와 더 넓은 query space를 후속 방향으로 명시한다. 공개 코드는 [TaoZhen1110/MemConflict](https://github.com/TaoZhen1110/MemConflict)다.

### 1.2 TANGLE

[TANGLE](https://arxiv.org/abs/2608.13921)는 context-partitioned, behavior-oscillation, source-contradiction의 irreducible personal-memory conflict를 다룬다. conflict 인지, 원인 추론, confidence calibration, clarification, faithfulness를 평가하고, CAAP가 conflict별 action을 선택한다. 그러나 각 instance는 하나의 persona-aspect와 하나의 unresolved slot을 중심으로 구성된다.

### 1.3 LongMemEval과 MemoryAgentBench

- [LongMemEval](https://arxiv.org/abs/2410.10813): information extraction, multi-session reasoning, temporal reasoning, knowledge update, abstention
- [MemoryAgentBench](https://arxiv.org/abs/2507.05257): retrieval, test-time learning, long-range understanding, selective forgetting과 FactConsolidation

이들은 장기 메모리의 필요성과 temporal update 난이도를 뒷받침하지만, 하나의 요청에 여러 conflict unit과 서로 다른 action이 함께 필요한지를 직접 통제하지 않는다.

### 1.4 본 파일럿의 차별점

| 구분 | 기존 memory-conflict 평가 | 본 연구 후보 |
|---|---|---|
| query target | 주로 한 attribute/aspect | 둘 이상의 query-relevant slot |
| conflict 수 | 한 중심 conflict unit | `K>1` |
| 정책 | instance에 한 conflict policy/action | unit별 정책 집합 `H>1` |
| 산출물 | 한 값 또는 한 적절한 action | 여러 unit의 해결을 조합한 응답·계획 |
| 핵심 오류 | retrieval/selection/underdetermination | unit 누락, 정책 과잉 일반화, 조합 불일치 |

단순히 conflict type을 분류해 하나의 action을 routing하는 것은 TANGLE과 차별화되지 않는다. 신규성 후보는 **여러 action의 query-level composition**과 그 과정에서 발생하는 policy interference다.

---

## 2. 문제 정의

### 2.1 Memory conflict unit

사용자 요청 `q`, 시점 `t`, memory history `M_{≤t}`가 있을 때 conflict unit `u_i`는 다음을 만족한다.

1. 질문의 하나의 atomic answer/action slot과 관련된다.
2. 둘 이상의 memory claim이 동시에 그대로 적용될 수 없다.
3. 다른 unit과 별도의 resolution decision을 내릴 수 있다.

### 2.2 `K`와 `H`

- `K`: 현재 요청과 관련된 독립 memory conflict unit 수
- 다중 충돌: `K>1`
- `H`: gold response에 필요한 서로 다른 core resolution policy 수
- 복합 충돌: `H>1`

파일럿의 memory policy는 다음 다섯 개로 시작한다.

| Memory relation | Resolution policy | 기대 행동 |
|---|---|---|
| true temporal update | `SUPERSEDE` | 최신 유효 상태를 사용하고 과거 상태를 현재값으로 쓰지 않음 |
| context-dependent preference | `CONDITION` | 조건에 따라 값을 분리 적용 |
| stable fact vs unreliable contradiction | `VERIFY_PREFER` | provenance를 비교하고 불충분하면 확인 요청 |
| legitimate coexisting preferences/perspectives | `KEEP_BOTH` | 서로 다른 대상·목적의 값을 보존 |
| underdetermined/high-risk conflict | `ABSTAIN_QUALIFY` | 과도하게 확정하지 않고 보류·질문·검증 |

중복 제거, 관련 없는 memory 필터링, 단순 부족 정보는 core `H`에서 제외한다.

### 2.3 핵심 실패 가설

**Global-policy collapse**는 모델이 unit을 분리하지 못하고 하나의 지배적 정책을 모든 slot에 적용하는 오류다.

- 모든 이전 정보를 최신 정보로 덮어씀
- 모든 충돌을 조건부 선호로 보존함
- 해결 가능한 unit까지 모두 확인 질문으로 넘김
- 한 unit의 source 불확실성을 다른 unit의 확정적 temporal update에도 전파함

---

## 3. 파일럿 연구 질문

- **MRQ1 — 구성 가능성:** 기존 memory benchmark의 동일 persona history에서 주제적으로 자연스러운 `K>1,H>1` query를 충분히 만들 수 있는가?
- **MRQ2 — 기존 benchmark 공백:** 원래 query는 대부분 한 target attribute/type만 평가하는가?
- **MRQ3 — composition failure:** `K=2`를 고정했을 때 `H=2`가 `H=1`보다 all-unit success를 낮추는가?
- **MRQ4 — 오류 기제:** `H=2`에서 global-policy collapse, unit omission, invalid carry-over가 증가하는가?
- **MRQ5 — oracle 여지:** gold unit과 unit별 policy를 제공하면 일반 CoT보다 성능이 회복되는가?

---

## 4. 데이터와 표본 구성

### 4.1 우선순위

1. **MemConflict**: 같은 persona timeline에 dynamic/static/conditional event가 존재하고 gold attribute·type·supporting memory가 있어 주 통제 source로 사용한다.
2. **TANGLE**: 공개 데이터가 확보되는 경우 irreducible action policy와 source/condition conflict의 외부 검증 source로 사용한다. 공개 artifact가 없으면 논문 사례만 설계 참고에 사용하고 데이터에는 포함하지 않는다.
3. **LongMemEval**: knowledge-update 및 multi-session item을 이용해 topic coherence와 query naturalness를 검토한다.
4. **MemoryAgentBench FactConsolidation**: temporal `SUPERSEDE` unit의 추가 source로만 사용한다.

서로 다른 persona의 무관한 질문을 단순 연결하지 않는다. 주 데이터는 같은 persona, 같은 생활 과제 또는 하나의 의사결정 맥락에서 결합 가능한 unit으로 제한한다.

### 4.2 원 benchmark audit

각 데이터셋에서 다음을 기록한다.

- 한 history에 들어 있는 conflict-bearing attribute 수와 type 수
- 원 query가 참조하는 target attribute 수
- query-level `K/H`
- 하나의 history 안에서 함께 물어도 자연스러운 attribute pair 후보 수
- 원 query가 single-slot인 이유와 benchmark construction rule

이 결과는 “memory conflict가 흔하다”는 prevalence가 아니라 **기존 benchmark의 query coverage audit**로 보고한다.

### 4.3 최소 표본

- MemConflict persona/history 최소 20개
- natural multi-goal query candidate 최소 40개 생성
- 검토 후 matched pair 최소 24쌍 목표
  - `K=2,H=1` homogeneous 24개
  - `K=2,H=2` heterogeneous 24개
- 최소 세 heterogeneous 조합, 조합당 8쌍 이상

우선 조합은 다음과 같다.

- `SUPERSEDE + CONDITION`
- `SUPERSEDE + VERIFY_PREFER`
- `CONDITION + VERIFY_PREFER`
- 데이터가 허용하면 `CONDITION + KEEP_BOTH` 또는 `VERIFY_PREFER + ABSTAIN_QUALIFY`

### 4.4 Matched construction

각 base pair에서 한 unit은 고정하고 다른 unit의 policy만 교체해 다음을 맞춘다.

| 조건 | Unit A | Unit B | `K` | `H` |
|---|---|---|---:|---:|
| Homogeneous | `SUPERSEDE` | `SUPERSEDE` | 2 | 1 |
| Heterogeneous | `SUPERSEDE` | `CONDITION` | 2 | 2 |

통제 변수:

- 같은 persona와 하나의 사용자 목표
- memory 수와 session 수
- conflict-bearing evidence 수
- 입력·출력 길이 ±10%
- temporal/source/context metadata의 명시성
- 질문의 slot 수와 답 형식
- distractor 수와 배치

원 memory statement와 provenance는 보존한다. 연결 문장과 multi-goal query만 최소 수정하며, 어떤 claim의 정답 관계도 변경하지 않는다.

### 4.5 자연성 검토

빠른 파일럿에서는 LLM 초벌 후 연구자 1인이 다음을 검토한다.

1. 실제 사용자가 한 번에 요청할 법한 하나의 목표인가?
2. 두 slot 모두 답변에 필수인가?
3. 같은 persona와 timeline 안에서 모순 없이 공존하는가?
4. `H=1/H=2` 차이 외 표면 난이도가 크게 달라지지 않는가?
5. 두 unit이 독립적이되 최종 응답에서 함께 조합되어야 하는가?

논문용 benchmark로 승격할 때는 blind human validation과 IAA를 추가한다.

---

## 5. 비교 방법

파일럿에서는 학습·파인튜닝·강화학습을 하지 않는다.

1. **Direct answer**: memory와 query만 제공
2. **Generic CoT**: 관련 memory를 비교하고 충돌을 해결하라는 일반 지시
3. **Taxonomy CoT**: memory conflict policy 정의를 제공하되 unit 구조는 제공하지 않음
4. **Single-global policy**: instance 전체에 하나의 policy만 선택·적용
5. **Oracle units**: gold conflict unit과 연결 memory를 제공
6. **Oracle unit policies**: unit별 gold policy까지 제공하고 조합만 수행

파일럿 단계에서는 새로운 agent/graph를 구현하지 않는다. `Oracle unit policies`가 회복 상한을 보이고 일반 baseline에서 composition failure가 확인된 뒤에만 다음 최소 파이프라인을 개발한다.

```text
retrieve relevant memories
→ decompose query-relevant slots
→ form conflict units
→ select policy per unit
→ check policy dependencies
→ compose one response
→ verify unresolved slots
```

---

## 6. 모델과 실행 설정

- 1차 모델: 현재 로컬 자원에서 안정적으로 실행 가능한 20B~30B급 instruction/reasoning model 1개
- 2차 재현: 계열이 다른 API 또는 open-weight model 1개
- temperature 0 또는 가능한 deterministic 설정
- 조건별 동일한 max output tokens와 prompt budget
- memory order seed 3개
- gold unit/policy는 oracle 조건 외에는 노출하지 않음
- prompt, model identifier, revision, generation config, 원 출력을 모두 저장

정확한 모델은 데이터 확보 후 현재 serving 환경과 라이선스를 확인해 실행 직전에 동결한다. 모델 이름을 계획 단계에서 임의로 확정하지 않는다.

---

## 7. 평가

### 7.1 주 지표

- **All-unit success**: 두 unit의 gold behavior를 모두 만족
- **Per-unit policy compliance**
- **Global-policy collapse rate**
- **Unit omission rate**
- **Cross-unit contamination rate**: 한 unit의 불확실성·조건·시점을 다른 unit에 잘못 전파

### 7.2 응답 품질

- memory faithfulness
- 필요한 conditionalization·clarification의 적절성
- invalid overwrite / invalid preservation
- 최종 계획의 internal consistency와 completeness
- token, latency, model call 수

빠른 파일럿은 rubric 기반 LLM 판정 후 연구자 spot-check로 진행할 수 있다. 논문용 수치는 blind human evaluation 또는 human-validated judge가 필요하다.

### 7.3 분석

주 비교는 matched pair 안의 다음 차이다.

```text
Delta_H = AllUnitSuccess(K=2,H=2) - AllUnitSuccess(K=2,H=1)
```

paired bootstrap 신뢰구간과 McNemar 검정을 사용한다. 작은 파일럿에서는 유의확률보다 효과 방향과 반복되는 오류 패턴을 우선 판단한다.

---

## 8. Go / revise / stop 기준

### Go: compositional memory conflict로 본실험 진행

다음을 모두 만족해야 한다.

1. 검토를 통과한 자연스러운 `K=2,H=2` 후보 24개 이상
2. 최소 세 policy combination 확보
3. Direct/Generic CoT 중 하나 이상에서 `Delta_H ≤ -8%p`
4. `H=2`에서 global-policy collapse 또는 cross-unit contamination이 반복 관측
5. Oracle unit policies가 최선 non-oracle baseline보다 10%p 이상 회복

### Revise

- 후보는 충분하지만 `H` 효과가 작음: dependency `D`, implicit query, conflict distance를 보조 난이도 축으로 검토
- Oracle도 실패: query/answer composition 또는 rubric을 수정
- 자연성은 높지만 pair matching이 어려움: 인과 효과가 아니라 benchmark stress-test로 범위 축소

### Stop 또는 다른 문제로 전환

- 자연스러운 후보가 12개 미만
- 대부분의 후보가 무관한 두 질문의 인공 결합으로만 성립
- `H=1/H=2` 성능과 오류 유형에 일관된 차이가 없음
- TANGLE/후속 연구가 동일한 multi-slot composition과 해결 방법을 이미 제공함

---

## 9. 산출물

- `data/pilot2_memory/source_audit.jsonl`
- `data/pilot2_memory/query_candidates.jsonl`
- `data/pilot2_memory/matched_pairs.jsonl`
- `data/pilot2_memory/validation.jsonl`
- `results/pilot2_memory/raw/<method>.jsonl`
- `results/pilot2_memory/metrics.json`
- `results/pilot2_memory/error_analysis.jsonl`
- `docs/pilot2_memory/result.md`

## 10. 실행 순서

- [ ] MemConflict 공개 데이터의 schema와 persona/history 묶음을 확인한다.
- [ ] TANGLE artifact 공개 여부를 다시 확인한다.
- [ ] 원 benchmark query의 target attribute/type 분포를 audit한다.
- [ ] 같은 persona 안에서 multi-goal query candidate 40개 이상을 만든다.
- [ ] 자연성·필수성·unit 독립성을 검토한다.
- [ ] `K=2,H=1`과 `K=2,H=2` matched pair를 동결한다.
- [ ] Direct, CoT, taxonomy, single-global, 두 oracle 조건을 실행한다.
- [ ] all-unit success와 global-policy collapse를 분석한다.
- [ ] go/revise/stop 결정을 기록한 뒤에만 해결 파이프라인을 구현한다.
