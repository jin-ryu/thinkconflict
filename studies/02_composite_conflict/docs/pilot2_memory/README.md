# 파일럿 2 · Compositional Memory Conflict

## 상태

Stage A–H와 Pilot 2B 통제 검증을 완료했다. `K×H` factorial diagnostic과 outcome-blind 원인 분해 screen을 마쳤으며, Pilot 3 방법론 gate는 조건부 revise 상태다.

- MemConflict: 30 personas, 1,579 sessions, 3,750 atomic questions
- raw same-session pair: 5,686건, 이 중 heterogeneous-policy pair 1,024건
- Codex 직접 판정과 query audit를 거쳐 `SUPERSEDE+CONDITION` `H=2` 24건 동결
- `H=1` 통제 24건과 6개 baseline/oracle 조건, 총 288회 실행 완료
- Pilot 2B: atomic unit 96/96 성공, H2 composite Direct 원순서 19/24·역순 22/24
- natural matching: strong 4쌍, moderate 5쌍; strong subset에서는 H1/H2 차이 없음
- 두 evidence order 합산: H2 Direct 41/48, Oracle unit policies 45/48
- Stage F: Qwen3-8B와 gpt-oss-20b 교차 재현 완료, 세 모델 gate 통과
- Stage G: `K=2,H=1/2`, `K=3,H=1/2/3` 5개 cell × 30 = 150 base 완료
- 390 atomic probe, 450 evidence-order trial, 세 생성 모델 실행 완료
- H3 gate: MemConflict의 세 번째 policy `VERIFY_PREFER`를 포함해 30건 확보
- H4: MemConflict taxonomy 밖의 연산을 인위적으로 추가하지 않음
- Stage H Qwen: direct 28.0% → oracle full_local 52.7%; verifier 추가 이득은 1건
- Stage H Llama 복제: direct 45.3% → full_local 46.7%; order flip 30% → 14%
- 아직 미완료: 독립 human validation, matched H-only causal set, 외부 유형 transfer, gold-free 방법

현재 판단은 [Stage H 결과](stage_h_result.md)를 먼저 보고, factorial 근거는 [Stage G 결과](stage_g_result.md), 초기 탐색은 [결과와 연구 판단](result.md), 교차 모델 gate는 [Stage F 결과](stage_f_result.md)를 본다. 실행 설정은 [run manifest](../../results/pilot2_memory/run_manifest.yaml), 초기 집계는 [semantic core metrics](../../results/pilot2_memory/semantic_core_metrics.json), 보강 실험 집계는 [Pilot 2B metrics](../../results/pilot2_memory/stage2_matched/metrics.json)에 있다.

## 오픈 모델 구성

| 단계 | 생성 모델 | 역할 |
|---|---|---|
| Stage F | Mistral-Small-3.2-24B, Qwen3-8B, gpt-oss-20b | composition-specific failure와 order effect의 계열 간 재현 |
| Stage G | Mistral-Small-3.2-24B, Qwen3-8B, Llama-3.1-70B-AWQ | K×H factorial 경향과 atomic-to-composite gap 검증 |
| Stage H | Qwen3-8B, Llama-3.1-70B-AWQ | oracle intervention의 정확도·순서 강건성 효과 비교 |

판정 모델은 생성 모델과 교차 배치한 Qwen3-8B와 Llama-3.1-70B-AWQ를 사용한다. 연구 결과와 이후 방법 개발 범위에는 외부 proprietary API 모델을 포함하지 않는다.

## 핵심 질문

1. 동일 persona history에서 자연스러운 source-grounded composite query를 구성할 수 있는가?
2. atomic unit은 성공하면서 같은 unit의 composite resolution은 실패하는가?
3. composition failure와 evidence-order flip이 여러 모델에서 재현되는가?
4. evidence grouping·filtering·policy·verifier 중 무엇이 회복을 만드는가?

## 이 파일럿의 역할

generic memory conflict taxonomy나 단일 action routing을 다시 제안하지 않는다. MemConflict와 TANGLE이 주로 한 target attribute/aspect를 평가한다는 공백을 바탕으로, 여러 query-relevant conflict unit의 해결 정책을 하나의 응답으로 조합하는 문제만 검증한다.

연구 문제와 제안 방법은 [memory 연구 본문](../background/memory_problem_and_method.md), 상세 데이터 구성, baseline, 평가 지표와 go/revise/stop 기준은 [실험 계획](plan.md)을 따른다. 파일럿 1의 근거는 [검색 conflict 결과](../pilot1_search/result.md)에 있다.

Stage H에서 Qwen의 큰 oracle recovery는 확인됐지만 Llama에서 정확도 이득은 재현되지 않고 order robustness만 개선됐다. 따라서 복합 충돌 문제 설정은 유지하되, oracle `full_local`을 방법으로 주장하지 않고 gold-free unit assignment·target selection·policy inference를 개발한 뒤 독립 human validation을 수행해야 한다.
