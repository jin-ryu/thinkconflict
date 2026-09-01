# Stage H 결과: 복합 메모리 충돌 원인 분해

> 실행일: 2026-08-27
> 상태: outcome-blind screen 완료; 범용 해결법 gate는 보류
> 선행 결과: [Stage G 결과](stage_g_result.md)

## 0. 결론

Stage H는 50개 base composite를 결과를 보지 않고 cell별 10개씩 고정하고, 각 base의 세 evidence order를 모두 사용해 150개 trial을 평가했다. Qwen3-8B에서는 evidence를 unit별로 묶고, 소유자·목표가 맞지 않는 기록을 제거하고, unit별 policy를 함께 주는 `full_local` oracle이 all-unit success를 **28.0%에서 52.7%로 +24.7%p** 높였다. direct 오답 49건을 복구하고 정답 12건을 훼손했으며, order-trial 수준 McNemar exact p는 약 0.000002였다.

그러나 같은 개입을 Llama-3.1-70B-AWQ에 복제했을 때 all-unit success는 **45.3%에서 46.7%로 +1.4%p**에 그쳤다. 15건을 복구하고 13건을 훼손해 p=.851이었다. 대신 order flip은 30%에서 14%로 줄고 worst-order base accuracy는 30%에서 40%로 올랐다.

따라서 현재 결과가 지지하는 주장은 다음과 같다.

1. Qwen의 실패에는 unit-local evidence ownership, target selection, policy application을 함께 명시하면 회복 가능한 headroom이 크다.
2. Llama에서는 동일 구조가 평균 정확도보다 evidence-order 안정성을 개선한다.
3. `full_local`은 gold evidence와 gold policy를 이용한 원인 진단 oracle이다. 아직 end-to-end CMCR 방법이 아니다.
4. verifier를 항상 호출하는 방법은 정당화되지 않는다. Qwen에서 full_local 대비 순증가는 1건뿐인데 호출·토큰 비용은 거의 두 배였다.
5. Pilot 3의 방법 기여는 oracle 구조를 gold-free하게 근사하고 모델별로 다른 잔여 오류를 다루는 데 있어야 한다.

## 1. 설계

### 1.1 표본

- Stage G의 다섯 cell: `K2_H1`, `K2_H2`, `K3_H1`, `K3_H2`, `K3_H3`
- SHA-256 기반 고정 seed로 cell당 10 base를 결과와 무관하게 선택
- 총 50 base, base당 original/reverse/interleaved 세 order, 총 150 trial
- 통계 단위는 base이며 세 order는 반복 측정이다

### 1.2 개입 조건

| 조건 | 조작 | 진단 대상 |
|---|---|---|
| direct | mixed evidence 그대로 입력 | 현재 end-to-end 성능 |
| grouped_only | gold unit signature로 문서를 물리적으로 묶음 | cross-unit contamination |
| owner_filter | other-person 기록 제거 | source ownership 오류 |
| target_filter | owner + CONDITION의 non-target preference 제거 | condition target selection 오류 |
| grouped_policy | grouping + gold unit policy 제공 | local policy application headroom |
| full_local | grouping + owner/target filter + policy | 세 병목의 결합 headroom |
| full_local_verifier | full_local draft를 두 번째 호출로 검증·수정 | composition/coverage 잔여 오류 |

`target_filter`는 제거할 기록을 찾을 때 gold atomic answer를 내부적으로 사용하지만 생성 모델에는 gold answer를 보여주지 않는다. grouping과 policy도 gold annotation을 사용한다. 그러므로 이 조건들은 구성요소의 필요성을 보는 oracle ablation이다.

### 1.3 생성과 판정

- 주 스크린 생성: `Qwen/Qwen3-8B`
- 주 스크린 판정: `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4` evidence-aware v3
- 복제 생성: `hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4`
- 복제 판정: `Qwen/Qwen3-8B` evidence-aware v3
- 생성 모델과 판정 모델을 교차해 자기평가를 피했다
- 생성 1,050건과 semantic judgment 1,050건에서 실행·파싱 오류는 0건이었다

## 2. Qwen 원인 분해 결과

| 조건 | all-unit success | direct 대비 순변화 | worst-order base | order flip | 평균 token/trial |
|---|---:|---:|---:|---:|---:|
| direct | 42/150 (28.0%) | — | 6/50 (12%) | 17/50 (34%) | 1,590.8 |
| grouped_only | 51/150 (34.0%) | +9 | 11/50 (22%) | 11/50 (22%) | 1,857.5 |
| owner_filter | 47/150 (31.3%) | +5 | 10/50 (20%) | 13/50 (26%) | 1,391.7 |
| target_filter | 59/150 (39.3%) | +17 | 12/50 (24%) | 16/50 (32%) | 1,289.8 |
| grouped_policy | 60/150 (40.0%) | +18 | 10/50 (20%) | 17/50 (34%) | 1,862.4 |
| full_local | 79/150 (52.7%) | +37 | 16/50 (32%) | 17/50 (34%) | 1,543.3 |
| full_local_verifier | 80/150 (53.3%) | +38 | 18/50 (36%) | 15/50 (30%) | 3,173.0 |

개별 개입 중 target selection과 policy 제공의 신호가 컸고, 결합 조건이 가장 높은 정확도를 냈다. 다만 이 표만으로 구성요소 사이의 인과적 상호작용이나 가산성을 주장할 수는 없다. `full_local`은 동시에 여러 입력을 바꾸기 때문이다.

### 2.1 cell별 direct → full_local

| cell | direct | full_local | 변화 |
|---|---:|---:|---:|
| K2_H1 | 40.0% | 76.7% | +36.7%p |
| K2_H2 | 33.3% | 66.7% | +33.4%p |
| K3_H1 | 30.0% | 66.7% | +36.7%p |
| K3_H2 | 23.3% | 26.7% | +3.4%p |
| K3_H3 | 13.3% | 26.7% | +13.4%p |

회복은 K=2와 K3_H1에서 크고 K=3,H≥2에서는 제한적이다. 즉 unit-local 입력 정리만으로 세 unit의 heterogeneous policy composition을 충분히 해결하지 못한다. Pilot 3에는 K=3,H≥2의 omission, cross-unit contamination, output composition 오류를 별도로 겨냥한 단계가 필요하다.

### 2.2 verifier 비용

verifier는 full_local 오답 3건을 복구했지만 정답 2건을 훼손해 순증가가 1건이었고, McNemar p=1.0이었다. 평균 token은 1,543.3에서 누적 3,173.0으로 증가했다. 따라서 항상-on verifier는 제외하고, 향후에는 coverage 검사에서 실패한 unit에만 선택적으로 재호출하는 설계를 검토한다.

## 3. Llama 교차모델 복제

| 지표 | direct | full_local |
|---|---:|---:|
| all-unit success | 68/150 (45.3%) | 70/150 (46.7%) |
| worst-order base accuracy | 15/50 (30%) | 20/50 (40%) |
| best-order base accuracy | 30/50 (60%) | 27/50 (54%) |
| order flip | 15/50 (30%) | 7/50 (14%) |
| 평균 token/trial | 1,229.2 | 1,167.2 |

정확도 짝비교는 15 recovery 대 13 regression으로 유의하지 않았다. full_local은 순서별 정확도를 46%, 46%, 48%로 평탄화해 순서 민감성은 낮췄지만, 일부 order에서만 맞던 base를 모두 맞게 만드는 대신 모두 틀리게 만든 경우도 있어 best-order accuracy가 하락했다. 따라서 안정성 개선을 곧바로 correctness 개선으로 해석하면 안 된다.

## 4. 연구 판단

### 4.1 통과한 것

- outcome-blind cell-balanced screen에서 Qwen의 큰 oracle recovery 확인
- 같은 개입이 Llama에서도 order flip을 줄이는 안정성 효과 확인
- 항상-on verifier의 비용 비효율 확인
- K=3,H≥2가 unit-local oracle 이후에도 남는 고난도 구간임을 확인

### 4.2 아직 통과하지 못한 것

- 두 생성 모델에서 일관된 all-unit accuracy recovery
- gold-free unit discovery, evidence ownership, target selection과 policy inference
- base/persona cluster bootstrap과 독립 human validation
- 외부 memory dataset 또는 held-out policy combination transfer

따라서 현재 Pilot 3 gate는 **조건부 revise**다. 문제 설정은 유지하되 `full_local` prompt를 곧바로 방법으로 승격하지 않는다.

## 5. Pilot 3에 요구되는 최소 방법

다음 구현은 학습 없는 adaptive linear pipeline이 가장 타당하다.

1. query를 atomic unit 후보로 분해한다.
2. 각 memory record를 unit에 soft assignment하고, 소유자와 조건 target의 불확실성을 함께 기록한다.
3. unit별 policy를 gold label 없이 추론한다.
4. 각 unit을 독립적으로 해결한 뒤 모든 unit을 하나의 답으로 합성한다.
5. 저신뢰 unit, 누락 unit, order-disagreement가 있을 때만 해당 unit을 재탐색·재판정한다.

핵심 비교는 Direct, 단일 structured prompt, gold-free CMCR-Linear, oracle full_local이다. Qwen에서는 oracle gap을 얼마나 닫는지, Llama에서는 정확도를 훼손하지 않으면서 order robustness를 유지하는지를 함께 봐야 한다. K=3,H≥2를 별도 primary stress subset으로 둔다.

## 6. 산출물

- 선택 데이터: `data/pilot2_memory/stage_h_screen/`
- 실행 설정: `results/pilot2_memory/stage_h_screen/run_manifest.yaml`
- Qwen 결과: `results/pilot2_memory/stage_h_screen/qwen3_8b/`
- Llama 복제: `results/pilot2_memory/stage_h_screen/llama3_1_70b_awq_int4/`
- 데이터 선택기: `src/composite_conflict/prepare_pilot2_stage_h.py`
- 개입 실행기: `src/composite_conflict/run_pilot2_stage_h.py`
- verifier 실행기: `src/composite_conflict/run_pilot2_stage_h_verifier.py`
- 집계기: `src/composite_conflict/finalize_pilot2_stage_h.py`

이 결과는 50 base의 screening evidence이며 논문 최종 효과 크기가 아니다. 논문용 결론 전에는 blind human validation과 더 큰 고정 평가셋이 필요하다.
