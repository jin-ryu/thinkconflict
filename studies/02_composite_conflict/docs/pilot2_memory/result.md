# 파일럿 2 결과: Compositional Memory Conflict 탐색 실험

> 실행일: 2026-08-26–27  
> 범위: MemConflict schema audit, `K=2,H=1/2` 구성, single-unit probe, evidence-order 통제, 학습 없는 baseline·oracle 비교  
> 상태: Stage A–G 완료; 최신 factorial 결과는 [Stage G 결과](stage_g_result.md), 독립 human validation은 미완료

## 0. 결론

MemConflict에서 자연스러운 `K=2,H=2` 24건과 `K=2,H=1` 통제 24건을 구성했다. Pilot 2B에서 96개 atomic probe는 96/96 성공했지만, 같은 H2 unit을 합친 Direct 응답은 원순서 19/24, 역순 22/24였다. 반면 strong natural match는 4쌍뿐이었고 그 subset에서는 두 순서 모두 H1=H2=4/4였다. 따라서 기존 20.8%p 차이를 `H`의 인과 효과로 해석하지 않고, atomic resolution은 가능해도 composition과 distractor 선택이 evidence order에 민감하다는 결과를 중심으로 삼는다. Stage F에서는 이 현상이 Qwen3-8B와 gpt-oss-20b에서도 재현되어 세 모델 gate를 통과했다.

하지만 이것만으로 논문 수준의 construction go를 선언할 수는 없다.

1. 통과한 24건은 모두 `SUPERSEDE+CONDITION`이다.
2. 표본은 prevalence 추정을 위한 무작위 표본이 아니라 feasibility 확인용 enriched sample이다.
3. `K=2,H=1` 통제군과 난이도·길이·goal을 엄밀하게 pairwise matching하지 않았다.
4. 세 모델에서 재현했지만 heterogeneous policy 조합은 여전히 `SUPERSEDE+CONDITION` 하나뿐이다.

따라서 현재 주장은 다음으로 제한한다.

> MemConflict에는 `SUPERSEDE+CONDITION`을 함께 적용해야 하는 source-grounded 과제가 존재한다. 세 open-weight 모델에서 각 atomic unit을 단독으로 해결하고도 합성 시 실패하는 사례와 evidence-order flip이 관측됐다. `H=2`가 일반적으로 더 어렵다는 인과 주장은 아직 검증되지 않았다.

교차 모델의 상세 결과와 gate 판정은 [Stage F 결과](stage_f_result.md)에 분리해 기록했다.

## 1. 데이터 audit

원본은 MemConflict 공식 repository의 `Data/Step4_4.jsonl`, revision `ec51d5d36e87f7665d1337f3a88cbde95fc2a964`이다.

| 항목 | 수 |
|---|---:|
| personas | 30 |
| sessions | 1,579 |
| atomic questions | 3,750 |
| raw same-session pairs | 5,686 |
| homogeneous-policy pairs | 4,662 |
| heterogeneous-policy pairs | 1,024 |

같은 session의 서로 다른 질문이라는 사실만으로 `K=2`나 하나의 자연스러운 목표가 보장되지는 않는다. 예를 들어 이직 정보와 임의의 음식 선호가 함께 등장해도 두 정보를 모두 요구하는 사용자 과제가 없으면 복합 충돌 사례가 아니다.

상세 자동 집계는 [schema report](../../data/pilot2_memory/schema_report.md)에 있다.

## 2. 판정자와 절차

### 2.1 판정자

- judge: `OpenAI Codex interactive agent`
- model family: `GPT-5-based Codex`
- exact deployment checkpoint: interface에서 노출되지 않음
- protocol: `pilot2-codex-direct-v1`
- 독립성: Codex 단일 pass, 독립 human validation 없음
- 용도: exploratory feasibility only

로컬 `mistralai/Mistral-Small-3.2-24B-Instruct-2506`가 만든 결과는 공식 판정에 사용하지 않았다. 해당 파일은 후보 탐색 과정의 preliminary artifact로만 이름을 분리해 보존했다.

### 2.2 후보 선택

전체 1,024 heterogeneous pair에서 work, health, relocation, social, family처럼 하나의 생활 목표로 연결될 가능성이 있는 후보의 recall을 높이는 lexical proposal score를 사용했다. persona당 최대 3개, session당 최대 1개로 80개 후보를 제안한 뒤, 그중 통과 가능 사례와 명확한 반례를 포함한 40건을 직접 판정했다.

이는 구성 가능성을 빨리 확인하는 목적에는 맞지만 자연 발생률이나 무작위 통과율을 추정할 수 없는 선택 방식이다.

### 2.3 통과 기준

다음을 모두 만족해야 통과시켰다.

1. 두 atomic slot이 별도의 conflict resolution decision인가?
2. 실제 사용자가 한 번에 요청할 법한 하나의 목표인가?
3. 두 slot이 모두 최종 답이나 행동 결정에 필요한가?
4. 동일 persona와 timeline을 유지하는가?
5. 원 answer와 conflict relation을 바꾸거나 새 gold를 발명하지 않는가?

질문 두 개를 단순히 `and`로 연결할 수 있다는 것은 통과 근거로 인정하지 않았다.

## 3. 판정 결과

| 구분 | 건수 |
|---|---:|
| 직접 검토 | 40 |
| 통과 | 24 |
| 탈락 | 16 |
| 통과 persona | 17 |
| 통과 session | 24 |
| 통과 naturalness 5/5 | 16 |
| 통과 naturalness 4/5 | 8 |

검토한 40건과 통과한 24건 모두 `SUPERSEDE+CONDITION` 조합이다. `VERIFY_PREFER`가 포함된 same-session pair는 대부분 가족 사실과 임의의 취향처럼 목표가 무관하여 이번 enriched set에 포함할 만큼 강한 후보를 확보하지 못했다.

### 3.1 강한 통과 사례

- 최신 work status가 `Busy`이고 Candy Crush를 짧은 휴식이나 통근 중 선호하는 경우: 현재 일정에는 `SUPERSEDE`, 활동 선택에는 `CONDITION`이 필요하다.
- physical health는 유지됐지만 mental health가 distressed로 바뀌었고 badminton을 stress relief로 선호하는 경우: 최신 건강 상태와 조건부 운동 선호가 한 추천에 함께 필요하다.
- 새 자녀가 생겼고 아기가 낮잠 잘 때 ambient music을 선호하는 경우: 가족 상태 update와 preference condition이 직접 맞물린다.
- 현재 business trip 중이고 여행 시 comfort와 photo opportunity를 위해 luxury resort를 선호하는 경우: 현재 이동 상태와 숙소 선호 조건이 한 결정에 필요하다.

### 3.2 대표 탈락 사례

- 이직과 busy shopping trip 선호: 두 정보가 같은 session에 있어도 하나의 의사결정을 공동으로 제약하지 않는다.
- business trip과 career fair·job interview용 suit 선호: 현재 trip은 해당 clothing condition을 활성화하지 않는다.
- relocation과 cold-evening vegetable soup 선호: 연결하려면 날씨나 식사 상황을 새로 발명해야 한다.
- dating 상태와 colleagues·students와 하는 게임 선호: 관계 update와 게임 조건이 무관하다.

## 4. Stage A–B 당시 판정과 후속 조치

### 확인된 것

- `SUPERSEDE+CONDITION`에서는 자연스러운 `K=2,H=2` query construction이 가능하다.
- 같은 session pair를 기계적으로 결합하면 무관한 사례가 다수 생기므로 goal necessity 검증이 필수다.
- 상태 변화가 preference condition을 직접 활성화하거나 비활성화하는 사례가 가장 설득력 있다.

### 이 단계에서 아직 확인되지 않았던 것

- 실제 memory context에서 모델이 `H=2`에서 더 실패하는가?
- `K=2,H=1` 통제군보다 all-unit success가 낮은가?
- oracle unit 또는 policy가 성능을 회복하는가?
- `VERIFY_PREFER`가 포함된 두 번째 heterogeneous 조합을 충분히 만들 수 있는가?

앞의 세 질문은 Stage C의 탐색 실행으로 일부 확인했으며, 결과는 8–9절에 기록한다. 다만 pairwise matching이 아니므로 `H`의 인과 효과로 해석하지 않는다.

## 5. Stage C에 적용한 실행 순서

1. 통과 24건에 대응할 `K=2,H=1` nearest-neighbor control을 만든다.
2. 두 원자 질문에 연결된 원문 memory evidence와 timestamp를 복원하고 required/forbidden behavior를 기록한다.
3. 길이와 distractor 수를 점검해 controlled comparison set을 동결한다. 엄밀한 pairwise matching은 완료된 것으로 간주하지 않는다.
4. Direct, Generic CoT, Taxonomy CoT, Single-global policy, Oracle units, Oracle unit policies를 같은 모델에서 실행한다.
5. `All-unit success`, global-policy collapse, omission, cross-unit contamination과 oracle recovery를 계산한다.
6. 이후 Memora 또는 HaluMem에서 `SUPERSEDE+VERIFY_PREFER`나 다른 policy 조합을 확보할 수 있는지 audit한다.

두 번째 조합을 확보하지 못해도 MemConflict 실험은 `SUPERSEDE+SUPERSEDE` 대 `SUPERSEDE+CONDITION`의 좁은 controlled study로 수행할 수 있다. 이 경우 논문의 주장은 “모든 복합 memory conflict”가 아니라 “temporal update와 contextual preference의 compositional interference”로 축소해야 한다.

## 6. 산출물

- 원자 질문: `data/pilot2_memory/question_index.jsonl`
- raw pair 모집단: `data/pilot2_memory/same_session_pair_pool.jsonl`
- 후보 제안: `data/pilot2_memory/codex_review_candidates_h2.jsonl`
- Codex 수기 annotation: `data/pilot2_memory/codex_h2_annotations.jsonl`
- 원본과 병합된 판정표: `data/pilot2_memory/codex_direct_reviews_h2.jsonl`
- 제외된 로컬 모델 예비 판정: `data/pilot2_memory/pair_mistral_preliminary_reviews.jsonl`
- 최종 H1/H2 instance: `data/pilot2_memory/instances_h1_oracle_retrieval.jsonl`, `data/pilot2_memory/instances_h2_oracle_retrieval.jsonl`
- 실행 설정: `results/pilot2_memory/run_manifest.yaml`
- 288개 원출력: `results/pilot2_memory/raw/baseline_outputs.jsonl`
- 핵심 의미 판정: `results/pilot2_memory/semantic_core_judgments.jsonl`
- 핵심 지표: `results/pilot2_memory/semantic_core_metrics.json`

---

## 7. Stage B 최종 구성 audit

초기 24건을 그대로 모델 평가에 사용하지 않았다. Direct 응답을 의미 검토하면서 다음 세 construction failure를 발견하고 순차 수정했다.

1. **Condition uniqueness:** 하나의 query가 둘 이상의 preference condition을 동시에 활성화한 사례를 수정했다.
2. **Unit necessity:** query에서 dynamic gold state를 직접 말하거나 한 unit을 삭제해도 같은 답을 낼 수 있던 사례를 상태 의존 subdecision으로 바꿨다.
3. **Gold compatibility:** 두 unit의 gold를 동시에 만족할 수 없는 relationship+food 사례 1건을 제외하고, business-trip state와 at-home preference의 applicability를 함께 판단하는 사례로 교체했다.

보고 결과는 `v3_post_compatibility_audit`만 사용한다. v0–v2 출력은 삭제하지 않고 `results/pilot2_memory/raw/`에 감사용으로 보존했다.

최종 set은 다음과 같다.

| 조건 | 구성 | 수 |
|---|---|---:|
| `H=1` | `SUPERSEDE+SUPERSEDE` | 12 |
| `H=1` | `CONDITION+CONDITION` | 12 |
| `H=2` | `SUPERSEDE+CONDITION` | 24 |

모든 instance는 원 MemConflict session의 `Updated_Attributes` 또는 동일 `Conflict_ID` evidence로 복원했다. 평균 compact context record 수는 `H=1` 6.83, `H=2` 6.17이다. 현재 실험은 retrieval failure를 분리하기 위한 **oracle relevant-evidence setting**이며, 같은 conflict ID의 other-person distractor는 유지했다.

## 8. Stage C 모델 실행

### 8.1 설정

- generation model: `mistralai/Mistral-Small-3.2-24B-Instruct-2506`
- serving: local vLLM, OpenAI-compatible endpoint
- temperature: 0
- seed: 20260826
- max output tokens: 900
- instances: 48
- conditions: 6
- calls: 288
- API/parse errors: 0

실행 조건은 Direct, Generic CoT, Taxonomy CoT, Single-global policy, Oracle units, Oracle unit policies이다. 상세 설정은 `results/pilot2_memory/run_manifest.yaml`에 고정했다.

### 8.2 핵심 의미 평가

| 조건 | `H=1` | `H=2` | `H=2-H=1` |
|---|---:|---:|---:|
| Direct | 24/24 (100.0%) | 19/24 (79.2%) | -20.8%p |
| Generic CoT | 22/24 (91.7%) | 21/24 (87.5%) | -4.2%p |
| Oracle unit policies | 23/24 (95.8%) | 24/24 (100.0%) | +4.2%p |

이 수치는 완전한 matched causal estimate가 아니라 고정 feasibility set의 기술통계다. Direct 48건은 Codex가 의미 검토했고, Generic CoT와 Oracle unit policies는 lexical high-confidence pass를 유지하면서 lexical failure를 Codex가 재검토했다. exact Codex deployment checkpoint는 interface에서 노출되지 않는다.

### 8.3 Direct의 `H=2` 오류 5건

| 오류 | 수 | 설명 |
|---|---:|---|
| wrong preference/condition selection | 3 | 다른 item 또는 distractor condition을 선택 |
| condition over-preservation | 1 | 하나의 조건을 선택하지 않고 두 대안을 함께 반환 |
| stale state | 1 | 최신 Busy update 대신 이전 Free 상태를 사용 |

원순서에서 Direct `H=2`는 5건 실패했고 Oracle unit policies는 24/24로 회복됐다. 그러나 Pilot 2B의 역순에서는 Oracle unit policies가 21/24였으므로 이 회복은 order-robust하지 않다. unit별 policy 명시에는 headroom이 있지만, 최종 방법은 unit-local evidence selection과 distractor rejection까지 포함해야 한다.

Generic CoT는 `H=2`를 19건에서 21건으로 개선했지만 `H=1`에서 unrelated preference를 더 끌어오는 오류 2건을 만들었다. 즉 더 길게 비교하라는 일반 지시가 항상 단조롭게 성능을 높이지는 않았다.

### 8.4 Single-global condition 해석

`H=2` 24건 중 22건에서 모델은 global label로 `CONDITION`을 선택했다. 그러나 실제 답에서는 temporal update를 정상 적용하기도 했으므로, 이 조건은 global-policy collapse만을 깨끗하게 조작하지 못했다. instruction-following confound가 있어 보조 분석으로만 둔다.

## 9. 현재 연구 판단

### 확인된 전제

1. MemConflict에서 source-grounded `K=2,H=2` 24건을 구성할 수 있다.
2. H2를 구성하는 atomic unit 48개는 Direct에서 모두 성공했다.
3. 같은 unit을 합치면 원순서 5건, 역순 2건이 실패했고 한 사례는 두 순서 모두 실패했다.
4. 오류는 주로 같은 evidence group 안의 잘못된 preference·distractor 선택과 condition over-preservation이었다.
5. 두 순서를 합친 H2 Direct는 41/48, Oracle unit policies는 45/48이었지만 순서별 회복은 일관되지 않았다.

따라서 방법론의 우선 대상은 단순 policy label 제공이 아니라 **unit-local evidence selection → policy application → composition verification**이다. 다만 CMCR-Linear 개발은 두 번째 모델에서 composition failure가 재현된 뒤 진행하는 것이 안전하다.

### 아직 주장하면 안 되는 것

1. 24+24가 goal·길이·난이도까지 엄밀하게 pairwise matched됐다는 주장
2. 복합 memory conflict가 자연 대화에서 흔하다는 prevalence 주장
3. `SUPERSEDE+CONDITION` 외 여러 heterogeneous policy 조합으로 일반화된다는 주장
4. 한 open-weight 모델의 24건 결과를 통계적 유의성이나 ACL 수준의 최종 증거로 해석하는 것
5. Codex 단일 판정이 독립 human evaluation을 대체한다는 주장

## 10. 다음 우선순위

1. 같은 atomic probe와 H2 composite를 계열이 다른 모델 2개에서 실행한다.
2. 최소 두 모델에서 재현되면 `K=2,H=1/2`와 `K=3,H=1/2/3` factorial composite를 cell당 30–50건 구축한다.
3. 세 번째 source-grounded policy가 부족하면 H3를 강제하지 않고 `H≤2`로 범위를 축소한다.
4. 확장 set에서 physical grouping, distractor filtering, policy와 verifier 원인 분해를 수행한다.
5. 회복 요인이 확인된 뒤에만 Pilot 3에서 CMCR-Linear를 개발한다.
6. 논문용 데이터로 승격할 때 blind human validation과 IAA를 추가한다.

현재 24건의 교차모델 재현은 대규모 factorial 구축 전에 수행하는 gate다. strong natural match가 4쌍뿐이므로 기존 H1/H2 nearest matching을 억지로 늘리지 않고, Stage G에서 K와 H를 함께 설계한다.


---

## 11. Pilot 2B 보강 실험

### 11.1 보강 목적

초기 24+24 비교는 H1과 H2의 goal·도메인·표면 난이도가 달라 `H` 효과를 분리하지 못했다. Pilot 2B는 기존 데이터를 폐기하지 않고 다음 두 통제를 추가했다.

1. 각 composite instance를 구성하는 96개 unit을 `K=1`로 단독 실행했다.
2. 동일 48개 composite instance의 memory record 순서를 완전히 뒤집어 5개 조건을 재실행했다.

또한 query 길이, answer 길이, domain, context record·token, distractor 수, explicit cue와 single-unit 난이도로 1:1 natural matching을 다시 수행했다.

### 11.2 실행 규모

| 항목 | 규모 |
|---|---:|
| single-unit Direct | 96 calls |
| reverse-order composite | 48 instances × 5 conditions = 240 calls |
| 총 추가 calls | 336 |
| 실행 오류 | 0 |
| natural match | strong 4, moderate 5, weak 제외 15 |

모델과 decoding은 기존 실행과 같은 `mistralai/Mistral-Small-3.2-24B-Instruct-2506`, temperature 0, seed 20260826이다.

### 11.3 핵심 의미 결과

| 비교 | 원순서 | 역순 | 두 순서 합산 |
|---|---:|---:|---:|
| H1 Direct | 24/24 | 21/24 | 45/48 |
| H2 Direct | 19/24 | 22/24 | 41/48 |
| H1 Oracle unit policies | 23/24 | 22/24 | 45/48 |
| H2 Oracle unit policies | 24/24 | 21/24 | 45/48 |

두 순서는 같은 instance를 반복한 것이므로 48개 독립 표본처럼 통계 검정하지 않는다.

### 11.4 동일-instance atomic-to-composite gap

H2의 atomic unit 48개는 모두 단독 Direct에서 성공했다. 그러나 같은 두 unit을 합친 composite query에서는 원순서 5건, 역순 2건이 실패했다. 원순서 실패 5건 중 4건은 순서를 바꾸면 회복됐고 1건은 두 순서 모두 실패했다. 역순에서는 기존에 성공했던 다른 1건이 새로 실패했다.

이 결과는 다음을 구분한다.

- 각 memory conflict를 단독으로 해결하는 능력: 관측 표본에서 48/48 성공
- 여러 해결 결과를 같은 응답으로 합성하는 능력: order-dependent failure 발생

따라서 단순히 각 unit이 어려워서 composite가 실패했다는 설명은 약해진다. 다만 오류가 `H=2`에만 고유하다고 볼 수는 없다. H1도 역순에서 3건 실패했기 때문이다.

### 11.5 natural matching 결과

엄격한 조건을 통과한 strong natural match는 4쌍뿐이었고, 두 evidence order 모두 H1=H2=4/4였다. Moderate까지 포함한 primary 9쌍에서는 다음 결과가 나왔다.

| order | H1 | H2 | 차이 |
|---|---:|---:|---:|
| original | 9/9 | 6/9 | -33.3%p |
| reverse | 9/9 | 7/9 | -22.2%p |

하지만 차이는 moderate match에서만 발생했고 strong subset에서는 사라졌다. 따라서 이를 `H=2`의 인과 효과로 사용하지 않는다.

### 11.6 oracle과 오류 해석

두 순서를 합치면 H2는 Direct 41/48에서 Oracle unit policies 45/48로 개선됐다. 그러나 원순서 24/24였던 oracle이 역순에서는 21/24로 하락했다. policy label을 제공해도 같은 evidence group 안의 여러 preference, other-person record와 조건 대안을 잘못 선택할 수 있다는 뜻이다.

반복 오류는 다음과 같다.

- query 조건과 다른 preference item 선택
- 같은 conflict group의 other-person 또는 대안 preference 사용
- 하나를 선택해야 할 때 여러 조건을 함께 보존
- record order 변화에 따른 선택 전환

### 11.7 연구 방향 결정

Pilot 2B는 기존의 강한 `H effect` 주장을 약화했지만, 방법론 목표를 더 구체화했다. 다음 연구 질문은 “H2가 H1보다 항상 어려운가?”보다 다음이 적합하다.

> 각 conflict unit은 단독으로 해결 가능한데도, 여러 unit과 distractor가 함께 주어지면 왜 evidence selection과 composition이 순서에 따라 실패하는가?

따라서 다음 방법은 global routing이나 policy label 예측만으로 구성하지 않는다.

```text
conflict unit proposal
→ unit-local evidence ownership·target filtering
→ unit-local policy application
→ cross-unit contamination·condition consistency verification
→ final composition
```

현재 판정은 **revise-and-validate**다. 연구 방향은 유지하되 `H` 인과 주장보다 compositional interference와 evidence-order robustness를 전면에 둔다. 두 번째 모델에서 atomic-to-composite gap이 재현된 뒤 CMCR-Linear 구현으로 진행한다.

### 11.8 산출물

- `data/pilot2_memory/stage2_matched/single_unit_probes.jsonl`
- `data/pilot2_memory/stage2_matched/validation.jsonl`
- `data/pilot2_memory/stage2_matched/single_unit_semantic_judgments.jsonl`
- `results/pilot2_memory/stage2_matched/raw/single_unit_outputs.jsonl`
- `results/pilot2_memory/stage2_matched/raw/reverse_order_outputs.jsonl`
- `results/pilot2_memory/stage2_matched/semantic_judgments.jsonl`
- `results/pilot2_memory/stage2_matched/metrics.json`
- `results/pilot2_memory/stage2_matched/run_manifest.yaml`
