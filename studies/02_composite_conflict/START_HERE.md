# Composite Conflict Study — START HERE

## 지금 확인할 결론

자연 검색 문서 202건을 strict `K/H` 기준으로 판정했지만 `K>1,H>1` 복합 충돌은 관측되지 않았다.

- ConfRAG 무작위 120건: 0건
- NatConfQA strict WH-mix 22건: 0건
- QACC 무작위 60건: 0건

따라서 “자연 검색에서 복합 충돌이 충분히 자주 발생한다”는 주장은 유지하지 않는다. ConfRAG 0/120의 양측 95% Wilson 상한은 약 3.1%다.

`K/H` formulation을 장기 사용자 메모리로 옮긴 Pilot 2 Stage G에서는 MemConflict의 세 validity operation 전체로 150개 controlled composite를 구성했다. 세 생성 모델에서 각 atomic unit이 맞아도 composite가 실패하는 사례, evidence-order flip, 같은 K에서 homogeneous→heterogeneous 하락이 반복됐다. 일반적인 memory-conflict 분류가 아니라 **Compositional Memory Conflict**가 현재 연구 후보이다.

Stage H의 outcome-blind 50-base screen에서 Qwen3-8B는 oracle `full_local`로 28.0%에서 52.7%까지 회복했지만, Llama-3.1-70B에서는 45.3%에서 46.7%로 accuracy recovery가 재현되지 않았다. 다만 Llama의 order flip은 30%에서 14%로 줄었다. 따라서 문제 설정은 유지하되 Pilot 3 방법론은 조건부 revise 상태다.

## 다음 단계

2026-08-28 Stage I–J 결과([stage_j_result.md](docs/pilot2_memory/stage_j_result.md)): 생성 모델 4종(Qwen3-8B/32B, Mistral-24B, Llama-70B)에서 (1) 같은 anchor unit을 same/different-policy 짝에 넣어도 different가 같거나 더 낫고(H-C 기각), (2) 독립 blind 주석(Claude, κ 0.82)으로 통제군 judge의 과잉 엄격성을 찾아 완화 규칙으로 재판정한 뒤에도 conflict 없는 다중 slot 통제군이 같은 크기로 떨어진다(H-B 기각). 따라서 **"서로 다른 policy의 conflict를 합성하는 것이 고유하게 어렵다"는 주장과 CMCR-Linear 방법은 보류**한다.

남는 현상은 (a) 8B~32B의 다중 slot 일반 저하(주된 실패: 타인 record·나중 거짓 값·다른 조건을 slot에 잘못 묶음), (b) 크기·reasoning과 무관한 evidence order 취약성(70B도 worst 0.39 vs best 0.74; 32B thinking on도 0.35 vs 0.79), (c) 같은 유형 conflict가 여럿이면 recency를 전체에 적용하는 동질성 간섭(24B·70B)이다. 제안 방향은 order-robust multi-slot memory answering(방법) 또는 benchmark·분석 논문이며, 대화형 context(I-3)와 frontier 모델 검증이 선행돼야 한다.

## 지금 볼 파일

1. [`docs/pilot2_memory/stage_j_result.md`](docs/pilot2_memory/stage_j_result.md)
   - Stage J 결과: 4 모델 J-1~J-4, 가설 판정, 방향 제안
2. [`docs/pilot2_memory/stage_ij_plan.md`](docs/pilot2_memory/stage_ij_plan.md)
   - Stage I–J 설계와 실행 체크리스트
3. [`docs/background/related_work_memory_2026.md`](docs/background/related_work_memory_2026.md)
   - 2025-06~2026-08 memory conflict 벤치마크·방법·인접 연구 조사
4. [`docs/pilot2_memory/stage_h_result.md`](docs/pilot2_memory/stage_h_result.md)
   - 최신 원인 분해, 교차모델 복제와 Pilot 3 판단
5. [`docs/pilot2_memory/stage_g_result.md`](docs/pilot2_memory/stage_g_result.md)
   - K×H factorial 결과와 3유형 일반화 범위
6. [`docs/pilot2_memory/plan.md`](docs/pilot2_memory/plan.md)
   - 파일럿 2의 전체 설계와 실행 이력
7. [`docs/background/memory_problem_and_method.md`](docs/background/memory_problem_and_method.md)
   - 새로운 memory conflict 연구의 문제 정의, 관련 연구, CMCR 방법과 본실험 계획
8. [`docs/pilot1_search/result.md`](docs/pilot1_search/result.md)
   - 검색 conflict에서 memory conflict로 이동한 근거

구조화된 최종 판정은 [`data/pilot1_search/final_llm_judgments.jsonl`](data/pilot1_search/final_llm_judgments.jsonl)에 있다.

## 용어

- `K`: 현재 질문과 관련된 독립 conflict unit 수
- 다중 충돌: `K>1`
- `H`: 필요한 서로 다른 core resolution policy 수
- 복합 충돌: `H>1`
- Compositional Memory Conflict: 하나의 요청에서 여러 memory conflict unit을 서로 다른 policy로 해결하고 하나의 응답·계획으로 조합해야 하는 경우

## 판정 정보와 한계

- 판정자: OpenAI Codex interactive agent, GPT-5 기반
- 정확한 deployment checkpoint: 비공개
- protocol: `strict-kh-direct-v1`
- 인간 검토와 human-human IAA 없음
- 성격: 빠른 exploratory go/no-go 판정

따라서 파일럿 1 결과는 gold benchmark가 아니라 기존 검색 기반 연구 전제를 계속 유지할지 결정하는 탐색 근거다.

## 연구 결정

1. 기존 자연 검색 `H` matched 파일럿 2는 수행하지 않는다.
2. 검색 문서에서 관측된 atomic operator의 다양성은 memory policy 설계의 후보로 재사용한다.
3. MemConflict·TANGLE 등 기존 연구와의 차별점은 type-aware routing이 아니라 **여러 conflict action의 query-level composition**으로 한정한다.
4. memory 파일럿에서도 자연스러운 후보 수와 `H` 효과가 확보되지 않으면 주제를 중단하거나 coverage stress test로 축소한다.

Stage G–H는 controlled cross-session composition과 oracle diagnostic이므로 자연 prevalence, H의 순수 인과 효과, end-to-end 해결을 확정하지 않았다. 다음 단계는 gold-free unit assignment·target selection·policy inference screen과 층화 인간 검토다.

## 나머지 문서의 용도

- `docs/background/memory_problem_and_method.md`: 현재 memory conflict 연구 본문 초안
- `docs/background/problem_and_method.md`: 기존 검색 중심 논문 초안; 비교 기록으로 보존
- `docs/background/related_work.md`: 검색 문서 conflict 관련 연구
- `docs/background/dataset_evidence.md`: Part I 검색 conflict, Part II memory conflict 데이터셋 조사
- `docs/pilot1_search/plan.md`: 파일럿 1의 사전 계획과 실제 실행 안내
- `docs/pilot1_search/annotation_guideline.md`, `docs/pilot1_search/runbook.md`: 재현·정식 주석 운영 자료

현재 의사결정에는 위 문서 전체를 읽을 필요가 없다.
