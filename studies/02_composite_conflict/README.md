# 02 · Compositional Conflict Resolution

독립 conflict unit 수 `K`와 서로 다른 해결 정책 수 `H`를 구분하고, 여러 정책을 하나의 응답으로 조합하는 학습 없는 해결 방법을 연구한다.

## 현재 방향

- **다중 충돌**: 독립적인 core conflict unit이 여러 개인 경우(`K>1`)
- **복합 충돌**: 서로 다른 core resolution policy가 함께 필요한 경우(`H>1`)
- 파일럿 1에서 자연 검색 문서 202건을 판정했으나 strict `K>1,H>1`은 0건이었다.
- 검색 문서의 자연 prevalence를 주요 동기로 삼는 방향은 중단한다.
- 파일럿 2 Stage G에서 150개 controlled `K×H` composite와 세 모델 검증을 완료했다.
- 현재는 H의 보편적 인과 주장보다 atomic-to-composite interference와 evidence-order robustness를 핵심 발견으로 둔다.
- Stage H에서 Qwen의 oracle accuracy recovery와 Llama의 order-robustness 개선을 확인했지만 교차모델 accuracy recovery는 미충족이다.
- Stage I–J([결과](docs/pilot2_memory/stage_j_result.md))에서 no-conflict 통제군과 anchor-unit 짝 설계로 검증한 결과, 4 모델 모두 conflict 고유 간섭과 policy 이질성 효과가 없었다. `H` 축과 CMCR-Linear는 보류하고, evidence order 취약성·동질성 간섭·evidence binding 실패를 중심으로 방향을 재설정한다.
- 2026-08 기준 관련 연구 조사는 [related_work_memory_2026.md](docs/background/related_work_memory_2026.md)에 있다. read-time per-unit heterogeneous policy composition은 아직 공백이지만 CAR(2606.01435), CAAP(2608.13921), IBA-Bench(2608.02171)가 인접한다.

generic memory conflict 또는 conflict-type routing만으로는 MemConflict·TANGLE과 차별화되지 않는다. 연구 후보의 핵심은 여러 memory slot에 서로 다른 action을 적용할 때 생기는 **global-policy collapse와 cross-unit contamination**이다.

## 읽는 순서

1. [현재 결론과 안내](START_HERE.md)
2. [Stage J 결과](docs/pilot2_memory/stage_j_result.md)
3. [파일럿 2 Stage I–J 계획](docs/pilot2_memory/stage_ij_plan.md)
4. [2026 memory conflict 연구 조사](docs/background/related_work_memory_2026.md)
5. [Stage H 최신 결과](docs/pilot2_memory/stage_h_result.md)
6. [Stage G factorial 결과](docs/pilot2_memory/stage_g_result.md)
7. [파일럿 2 전체 계획과 다음 단계](docs/pilot2_memory/plan.md)
8. [새 memory 연구 문제 정의와 CMCR](docs/background/memory_problem_and_method.md)
9. [파일럿 1 결과](docs/pilot1_search/result.md)

배경 문서는 다음과 같다.

10. [파일럿 1 전체 판정표](results/pilot1_search/final_llm_judgment_table.md)
11. [기존 검색 문제 정의와 PCCR](docs/background/problem_and_method.md)
12. [관련 논문: 문제·방법·한계](docs/background/related_work.md)
13. [검색·memory 다중·복합 충돌 데이터 근거](docs/background/dataset_evidence.md)
14. [파일럿 1 사전 계획](docs/pilot1_search/plan.md)
15. [주석 지침](docs/pilot1_search/annotation_guideline.md)
16. [파일럿 1 실행 안내](docs/pilot1_search/runbook.md)

## 작업 구조

```text
docs/       문제 정의, 문헌 조사, 파일럿 계획·결과
src/        전처리·주석·평가 코드
data/       표본·주석·판정본·split
results/    파일럿 및 본실험 산출물
tests/      연구 전용 회귀 테스트
```

AIR 연구의 스키마나 코드를 암묵적으로 import하지 않는다. 재사용이 확정된 중립 유틸리티가 생길 때만 별도 공용 모듈로 승격한다.
