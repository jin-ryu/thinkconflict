# Pilot 2 Stage F · 교차 모델 재현 결과

## 0. 결론

Stage F gate는 **통과**했다. 기존 Mistral과 새로 실행한 Qwen·gpt-oss 세 계열 모두에서, H2를 이루는 atomic unit은 거의 모두 맞히지만 같은 unit을 한 query에 합치면 실패하는 사례가 재현됐다. 새 두 계열에서는 공통으로 잘못된 조건의 preference를 고르는 오류가 나타났고, evidence 순서만 뒤집어도 성공과 실패가 바뀌었다.

그러나 이 결과는 `H` 증가의 인과 효과를 증명하지 않는다. 현재 24개 `K=2,H=2` feasibility set에서 **compositional interference와 order sensitivity가 여러 모델에 존재한다**는 gate 증거다. 다음 단계는 계획된 `K×H` factorial set을 확장하는 Stage G이며, 아직 CMCR 방법의 효과나 ACL 수준의 최종 주장을 의미하지 않는다.

## 1. 질문과 입력

Stage F는 새 합성 데이터를 만들지 않고 Pilot 2B에서 동결한 입력을 그대로 사용했다.

| 입력 | 수 | 목적 |
|---|---:|---|
| H2 부모 | 24 | `SUPERSEDE+CONDITION`, `K=2,H=2` |
| H2 atomic probe | 48 | 각 부모의 두 unit을 각각 `K=1`로 실행 |
| H2 original composite | 24 | 원 memory order Direct |
| H2 reverse composite | 24 | 같은 evidence를 완전히 역순으로 배치 |

모든 입력은 oracle relevant-evidence setting이며, 같은 conflict group 안의 distractor는 유지했다. H2 atomic 48건은 전체 96개 probe에서 H2 부모 ID로 다시 동결했다.

## 2. 모델과 추론 통제

| 모델 | 체크포인트 revision | 추론 통제 | 호출 수 |
|---|---|---|---:|
| `Qwen/Qwen3-8B` | `b968826d9c46dd6066d109eabc6255188de91218` | bf16, thinking off | 144 |
| `openai/gpt-oss-20b` | `6cee5e81ee83917806bbde320786a8fb61efebee` | native MXFP4, effort low | 144 |

각 모델은 F1 Direct 96회와 F2 Oracle unit policies 48회를 실행했다. 공통 설정은 temperature 0, seed 20260826, max output tokens 900이다. H100 80GB 한 장에서 vLLM 0.27.1로 모델을 순차 서빙했으며 API·JSON parse 오류는 모두 0건이었다.

초기 후보였던 `Qwen/Qwen3.6-27B`는 로컬 snapshot 일부가 미완성인 상태에서 부족 shard를 복원하다 disk quota 오류가 발생해 결과에 포함하지 않았다. 완전히 캐시된 Qwen3-8B를 사용했고, 실패한 27B 실행은 실험 호출 수나 결과에 섞지 않았다.

## 3. F1 Direct 결과

원본과 역순은 같은 24개 부모를 재사용하므로 48개 독립 표본으로 통계 검정하지 않는다.

| 모델 | atomic | original composite | reverse composite | composition-specific failure/order trial |
|---|---:|---:|---:|---:|
| Mistral-Small-3.2-24B | 48/48 | 19/24 | 22/24 | 7/48 (14.6%) |
| Qwen3-8B | 47/48 | 19/24 | 16/24 | 13/48 (27.1%) |
| gpt-oss-20b | 48/48 | 23/24 | 19/24 | 6/48 (12.5%) |

`composition-specific failure`는 해당 부모의 두 atomic unit이 모두 성공했지만 composite Direct가 실패한 order trial이다. Qwen의 atomic 실패 1건은 이 분모의 composition-specific 사례로 세지 않았다.

### 3.1 공통 오류

새 두 모델에서 공통으로 확인된 오류는 다음과 같다.

- query 조건과 다른 preference 선택: Hollywood blockbuster 대신 gory horror, gym tank 대신 cargo pants 등
- evidence에서 근거를 찾을 수 없는 supervision time 추론
- Qwen에서는 추가로 여러 조건을 하나로 선택하지 않고 함께 보존하거나 current state를 생략하는 오류

Qwen의 composition-specific 13건 중 wrong preference selection이 6건으로 가장 많았다. gpt-oss는 6건 중 4건이 wrong preference selection이었다. 따라서 관측된 문제는 단순 temporal update 실패만이 아니라, 여러 unit과 대안 evidence가 같이 있을 때 **query-condition에 맞는 local evidence를 끝까지 유지하지 못하는 현상**에 가깝다.

## 4. Evidence-order 민감도

| 모델 | original/reverse 성공 여부가 뒤집힌 부모 |
|---|---:|
| Qwen3-8B | 7/24 (29.2%) |
| gpt-oss-20b | 4/24 (16.7%) |
| Mistral | 원·역순 성공 수가 달라 order effect 관측 |

Qwen과 gpt-oss 모두 동일 query와 동일 evidence를 사용하고 record 순서만 바꿨는데 preference 선택이 달라졌다. 따라서 order flip은 한 모델 계열에만 나타난 현상이 아니다. 다만 flip 자체가 `H` 때문이라는 인과 주장은 하지 않는다. distractor 배치와 decoder의 위치 민감도가 함께 작용할 수 있기 때문이다.

## 5. F2 Oracle unit-policy 결과

F1에서 composition failure가 확인된 두 모델에 unit grouping과 각 unit의 required behavior를 제공했다.

| 모델 | Direct pooled | Oracle pooled | Direct 실패 중 복구 | Direct 성공 중 회귀 |
|---|---:|---:|---:|---:|
| Qwen3-8B | 35/48 | 37/48 | 5/13 | 3 |
| gpt-oss-20b | 42/48 | 43/48 | 3/6 | 2 |

Oracle policy는 평균적으로 소폭 개선했지만 단조로운 회복을 만들지 않았다. policy를 알려줘도 모델이 다른 preference item을 선택하거나 query 조건에 없는 시간대를 추론했고, Direct에서 맞던 일부 사례가 Oracle prompt에서 새로 실패했다.

이 결과는 다음 원인 구분을 지지한다.

1. 일부 실패는 unit·policy 식별 정보로 복구된다.
2. 남은 실패는 policy label 부족만으로 설명되지 않는다.
3. 최종 방법은 `unit-local evidence ownership → condition-matched selection → policy application → composition verification`을 분리해야 한다.

## 6. Gate 판정

| 기준 | 결과 |
|---|---|
| 최소 2개 모델에서 atomic 성공 후 composite 실패 | 통과: 3/3 |
| 모델당 최소 3건 또는 10% composition-specific failure | 통과: Mistral 14.6%, Qwen 27.1%, gpt-oss 12.5% |
| 두 추가 계열의 공통 오류 유형 | 통과: wrong preference selection, unsupported inference |
| order flip이 한 모델에만 국한되지 않음 | 통과 |

따라서 Stage G 데이터 확장으로 진행한다. 다만 현재 gate는 방법 개발을 바로 정당화하는 최종 증거가 아니라, 더 큰 controlled set에 투자할 최소 근거다.

## 7. 다음 단계

1. `K=2,H=1/2`와 `K=3,H=1/2/3`의 5개 composite cell을 cell당 최소 30건 구성한다.
2. source-grounded 세 번째 policy가 30건 미만이면 `H=3`을 강제하지 않고 `H≤2`로 범위를 축소한다.
3. 동일 모델 3계열에서 atomic success를 조건으로 composition failure, order flip과 error taxonomy를 재평가한다.
4. blind human validation으로 Codex 의미 판정을 검증한다.
5. 그 뒤 CMCR-Linear에서 grouping, local selection, policy, verifier를 단계별 ablation한다.

## 8. 산출물

- 입력: `data/pilot2_memory/stage_f_cross_model/h2_single_unit_probes.jsonl`
- 모델별 raw: `results/pilot2_memory/stage_f_cross_model/{qwen3_8b,gpt_oss_20b}/raw/`
- 모델별 판정: `results/pilot2_memory/stage_f_cross_model/{qwen3_8b,gpt_oss_20b}/semantic_judgments.jsonl`
- 모델별 지표: `results/pilot2_memory/stage_f_cross_model/{qwen3_8b,gpt_oss_20b}/metrics.json`
- 통합 gate: `results/pilot2_memory/stage_f_cross_model/cross_model_metrics.json`
- 실행 명세: `results/pilot2_memory/stage_f_cross_model/run_manifest.yaml`

의미 판정은 exploratory Codex audit이며 exact deployment checkpoint는 interface에서 노출되지 않는다. 논문용 결과에서는 blind human annotation과 IAA가 필요하다.
