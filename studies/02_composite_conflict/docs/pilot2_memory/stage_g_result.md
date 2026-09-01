# Pilot 2D Stage G 결과: K×H factorial compositional memory conflict

> 실행일: 2026-08-27  
> 상태: controlled factorial diagnostic 완료  
> 주의: 자연 발생률·H의 인과 효과·모든 memory conflict로의 일반화를 입증한 결과가 아니다.

## 0. 결론

MemConflict의 세 validity dimension 전체를 사용해 `K2H1`, `K2H2`, `K3H1`, `K3H2`, `K3H3`의 5개 cell을 각각 30개씩 구성했다. 150개 base composite, 390개 paired atomic probe, base당 세 evidence order를 적용한 450개 composite trial을 세 모델에서 실행했다.

두 판정자와 세 생성 모델에서 공통으로 확인된 가장 안전한 결론은 다음이다.

> 같은 `K`에서 heterogeneous resolution policy가 추가되면 worst-order all-unit success가 대체로 낮아진다. 각 atomic unit이 모두 맞은 base에서도 composite 실패가 반복되며, evidence order에 따라 결과가 바뀐다. 그러나 cell이 동일 사실의 완전한 counterfactual pair가 아니므로 이를 아직 “H가 본질적·인과적으로 난이도를 높인다”라고 주장할 수는 없다.

이 결과는 연구 방향을 discovery-only로 축소할 이유보다는, **학습 없는 unit-local resolution 및 composition verifier 방법을 개발할 근거**에 가깝다. 다만 방법 개발 전에 다음 두 보강이 필요하다.

1. evidence-aware LLM judge 불일치 사례의 층화 인간 검토
2. 같은 atomic unit을 유지하고 policy heterogeneity만 조작하는 matched/counterfactual subset 또는 policy identity를 보정한 분석

## 1. 데이터 구성

### 1.1 규모

| 항목 | 수 |
|---|---:|
| persona | 30 |
| 독립 base composite | 150 |
| cell당 base | 30 |
| paired atomic probe | 390 |
| evidence-order variant | base당 3 |
| composite order trial | 450 |

증거 순서는 `original`, `reverse`, `interleaved`다. 세 order는 같은 base를 반복한 것이므로 독립 표본으로 세지 않는다. 통계 단위는 150개 base composite다.

### 1.2 cell

| Cell | 의미 | Base 수 |
|---|---|---:|
| `K2_H1` | 두 unit, 한 policy | 30 |
| `K2_H2` | 두 unit, 두 policy | 30 |
| `K3_H1` | 세 unit, 한 policy | 30 |
| `K3_H2` | 세 unit, 두 policy | 30 |
| `K3_H3` | 세 unit, 세 policy | 30 |

각 policy identity와 multiset을 저장했다. `H=1`에는 세 homogeneous policy를, `H=2`에는 가능한 두 policy 조합을, `H=3`에는 `SUPERSEDE+CONDITION+VERIFY_PREFER`를 포함했다.

### 1.3 source-grounding과 자연성 범위

- atomic fact, timestamp, conflict relation, answer와 evidence record는 MemConflict 원본에서 보존했다.
- 같은 persona의 서로 다른 session에서 atomic unit을 가져왔다.
- 새로 작성한 것은 compound query의 연결 형식과 evidence order뿐이다.
- 따라서 이 set은 **source-grounded controlled composition**이지만, 원 대화에서 하나의 자연스러운 사용자 목표로 함께 발생한 prevalence sample은 아니다.
- 데이터 검증은 통과했으며 171개 extraction failure는 후보 pool에서 제외했다. 이는 최종 150개 instance 오류가 아니라 SUPERSEDE 원문 복원 규칙이 보수적으로 후보를 버린 기록이다.

## 2. 모델과 실행

| 생성 모델 | 역할 | 설정 |
|---|---|---|
| `Qwen/Qwen3-8B` | 효율적 open model | BF16, thinking off |
| `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | 계열·규모 확장 | local vLLM |
| `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4` | memory-literature 계열 anchor | AWQ INT4 |

모든 생성은 temperature 0, seed 20260827, Direct 조건으로 실행했다. Llama 70B의 양자화 결과는 8B와 규모를 맞춘 비교가 아니라 공개 Llama 계열의 강한 모델에서 재현성을 확인하는 역할이다. Llama에서 1개 atomic output이 반복적으로 불완전 JSON으로 종료되어, 이를 제외하지 않고 final-answer omission 실패로 분모에 포함했다.

## 3. 의미 판정 protocol audit

최종 판정은 candidate의 `final_answer`만 보고 unit별 의미 정답을 평가했다. generation의 `analysis_summary`나 `resolved_units`는 판정 근거로 사용하지 않았다.

초기 판정 protocol은 gold answer만 제공했다. 이 방식은 gold가 `Yes`이고 candidate가 정확한 상태 변화를 자세히 서술한 사례를 오답 처리했다. 따라서 초기 결과는 폐기하고 다음을 포함한 evidence-aware v3로 전량 재판정했다.

- atomic question과 target date
- required behavior
- gold atomic answer
- gold evidence records
- candidate final answer

교차 판정은 self-judge를 피했다.

- Mistral 생성: Qwen judge와 Llama judge 둘 다 사용
- Qwen 생성: Llama judge 사용
- Llama 생성: Qwen judge 사용

Mistral의 두 judge 합의는 다음과 같다.

| 범위 | 일치율 | Cohen's κ |
|---|---:|---:|
| 전체 840 trial | 80.0% | 0.590 |
| atomic 390 | 89.0% | 0.708 |
| composite 450 | 72.2% | 0.435 |

Composite 판정의 κ가 낮으므로 절대 정확도는 탐색 수치다. 논문용 결과에는 cell·policy·정답 길이별로 층화한 blind human validation과 adjudication이 필요하다.

## 4. 주요 결과

### 4.1 Worst-order all-unit success

한 base의 세 order가 모두 성공해야 성공으로 세는 보수적 지표다.

| 생성 모델 / 판정자 | K2H1 | K2H2 | K3H1 | K3H2 | K3H3 |
|---|---:|---:|---:|---:|---:|
| Mistral / Qwen | 60.0% | 26.7% | 56.7% | 26.7% | 6.7% |
| Mistral / Llama | 33.3% | 26.7% | 30.0% | 20.0% | 6.7% |
| Qwen / Llama | 40.0% | 13.3% | 16.7% | 3.3% | 6.7% |
| Llama / Qwen | 60.0% | 43.3% | 50.0% | 16.7% | 16.7% |

공통 패턴은 다음이다.

1. K=2에서는 세 생성 모델 모두 H2가 H1보다 낮았다.
2. K=3에서는 H2가 H1보다 모든 모델에서 낮았다.
3. H3는 H2보다 항상 단조롭게 낮지는 않았다. Qwen과 Llama 생성에서는 H2와 같거나 소폭 높았다.
4. 따라서 현재 결과는 “H가 1씩 늘 때마다 성능이 단조 감소한다”보다 **homogeneous에서 heterogeneous로 넘어갈 때 성능 저하가 반복된다**는 주장에 더 적합하다.

각 cell의 `n=30` Wilson interval은 넓고 서로 겹친다. 예를 들어 Mistral/Qwen의 K2H1 60.0% CI는 42.3–75.4%, K2H2 26.7% CI는 14.2–44.5%다. 파일럿은 방향과 실패 메커니즘을 확인하는 용도이지 최종 유의성 검정이 아니다.

### 4.2 Atomic-to-composite interference

| 생성 모델 / 판정자 | Atomic unit 정확도 | 모든 atomic이 맞은 base | 그 base 중 order 하나 이상 composite 실패 |
|---|---:|---:|---:|
| Mistral / Qwen | 71.3% | 65/150 | 18/65 (27.7%) |
| Mistral / Llama | 78.7% | 78/150 | 53/78 (67.9%) |
| Qwen / Llama | 84.4% | 102/150 | 80/102 (78.4%) |
| Llama / Qwen | 77.2% | 76/150 | 26/76 (34.2%) |

판정자에 따라 실패율의 절대값 차이는 크지만, 모든 조합에서 composition-specific failure가 존재했다. 이는 단순히 원자 conflict 자체를 몰라서 실패한 경우와 별개로, 여러 unit의 evidence ownership·resolution·최종 합성에서 추가 실패가 생긴다는 근거다.

### 4.3 Evidence-order sensitivity

Base별 세 order의 성공 여부가 섞인 비율은 다음과 같다.

- Mistral/Qwen: 21.3%
- Mistral/Llama: 34.0%
- Qwen/Llama: 28.7%
- Llama/Qwen: 26.0%

즉 5분의 1 이상에서 evidence order가 all-unit success를 바꿨다. 이는 최종 방법에 order-robust evidence grouping과 composition verification이 필요함을 지지한다.

주요 의미 오류는 `wrong_temporal_state`와 `wrong_fact_or_source`였다. `wrong_condition`, omission과 cross-unit contamination도 관측됐지만 판정자별 빈도 차이가 커 현재 taxonomy의 정량 결론으로 사용하지 않는다.

## 5. 세 유형이면 일반화에 충분한가

### 5.1 충분한 주장

세 유형은 임의로 고른 것이 아니라 MemConflict가 제시한 전체 세 validity dimension에 대응한다.

| MemConflict dimension | 본 연구 policy |
|---|---|
| dynamic / temporal validity | `SUPERSEDE` |
| static / factual validity | `VERIFY_PREFER` |
| conditional / contextual validity | `CONDITION` |

따라서 다음 주장은 가능하다.

> MemConflict taxonomy의 세 core validity operation 전체에서 query-level policy composition을 구성하고 H1–H3를 평가했다.

이는 기존 Pilot 2의 `SUPERSEDE+CONDITION` 한 조합보다 분명한 범위 확장이다. 세 pair 조합과 완전 heterogeneous H3를 모두 포함하므로 “한 특정 pair에서만 생긴 현상”이라는 비판도 약해진다.

### 5.2 충분하지 않은 주장

세 유형만으로 **모든 장기 메모리 충돌에 일반화했다**고 말하면 안 된다. 관련 연구는 다음처럼 다른 resolution action을 다룬다.

- TANGLE: irreducible conflict에서 clarify, verify, defer, reversible trial
- STALE: implicit update와 다른 memory로 전파되는 invalidation
- Memora: deletion·forgetting과 obsolete memory 억제

이들은 `H=4`라는 숫자 하나를 추가한다고 해결되지 않는다. 새 operation과 dependency 구조가 다르므로 별도 외부 transfer 축으로 다뤄야 한다.

결론적으로 **3유형은 core benchmark claim에는 충분하지만 universal taxonomy claim에는 부족하다.** 논문의 표현은 “three foundational validity operations” 또는 “the full MemConflict taxonomy”로 제한한다.

## 6. 무엇이 확인됐고 무엇이 남았는가

### 확인된 것

1. 30 persona 모두에서 세 policy의 source-grounded atomic unit을 확보할 수 있었다.
2. 세 pair 조합과 H3 full combination을 cell당 30건 규모로 구성할 수 있었다.
3. 세 생성 모델에서 K를 고정했을 때 H1→H2 하락 방향이 재현됐다.
4. atomic 성공 이후에도 composite failure와 evidence-order flip이 반복됐다.
5. 단순 Direct 응답을 넘어 unit-local evidence selection과 composition verification을 개발할 empirical headroom이 있다.

### 아직 확인되지 않은 것

1. 실제 사용자 요청에서 K>1,H>1이 얼마나 자주 발생하는가
2. 동일 facts·길이·난이도를 완전히 고정했을 때 H만의 인과 효과가 있는가
3. H2→H3가 단조롭게 더 어려운가
4. 세 유형 밖의 irreducible, deletion/forgetting, propagated dependency로 transfer되는가
5. LLM judge 불일치를 인간 판정이 어떻게 해소하는가

## 7. 연구 방향 결정

현재 결과는 “세 유형만으로 일반화 완료”도, “발견만 보고 방법을 포기”도 지지하지 않는다. 가장 설득력 있는 다음 논문 전개는 다음이다.

1. **Problem/benchmark contribution:** `K`와 `H`를 분리한 source-grounded controlled composition set
2. **Empirical finding:** atomic success가 composite success를 보장하지 않고 heterogeneous policy와 evidence order에서 실패가 반복됨
3. **Method contribution:** 학습 없는 unit-local resolver와 composition verifier
4. **Evaluation contribution:** all-unit success, composition-specific failure, worst-order robustness와 비용

방법론은 전체 그래프 agent보다 다음의 adaptive linear pipeline을 우선한다.

```text
conflict/unit proposal
→ unit-local evidence ownership
→ unit-local policy application
→ final composition
→ cross-unit/order-consistency verifier
→ 실패한 unit만 제한적으로 재탐색
```

항상 agent/graph search를 수행하지 않고 verifier가 실패를 감지한 사례만 추가 test-time compute를 사용한다. 다음 단계는 이 구조를 Pilot 3에서 Direct·CoT·oracle과 비교하는 것이다.

## 8. 산출물

- 데이터: `data/pilot2_memory/stage_g_factorial/`
- raw generation과 판정: `results/pilot2_memory/stage_g_factorial/`
- 데이터 생성기: `src/composite_conflict/prepare_pilot2_stage_g.py`
- 모델 실행기: `src/composite_conflict/run_pilot2_baselines.py`
- evidence-aware judge: `src/composite_conflict/judge_pilot2_stage_g.py`
- 집계기: `src/composite_conflict/finalize_pilot2_stage_g.py`

파일명이 `v3_evidence`인 judgment와 metrics만 최종 Stage G 해석에 사용한다. 이전 judge 파일은 protocol audit용으로만 보존한다.
