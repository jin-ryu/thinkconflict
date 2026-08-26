# 02 · Compositional Conflict Resolution

독립 conflict unit 수 `K`와 서로 다른 해결 정책 수 `H`를 구분하고, 여러 정책을 하나의 응답으로 조합하는 학습 없는 해결 방법을 연구한다.

## 현재 방향

- **다중 충돌**: 독립적인 core conflict unit이 여러 개인 경우(`K>1`)
- **복합 충돌**: 서로 다른 core resolution policy가 함께 필요한 경우(`H>1`)
- 파일럿 1에서 자연 검색 문서 202건을 판정했으나 strict `K>1,H>1`은 0건이었다.
- 검색 문서의 자연 prevalence를 주요 동기로 삼는 방향은 중단한다.
- 파일럿 2는 long-term personalized memory에서 query-level `K/H` composition이 자연스럽고 독립적으로 어려운지 검증한다.
- 파일럿을 통과한 뒤에만 memory-unit decomposition → policy assignment → response-plan composition의 training-free pipeline을 개발한다.

generic memory conflict 또는 conflict-type routing만으로는 MemConflict·TANGLE과 차별화되지 않는다. 연구 후보의 핵심은 여러 memory slot에 서로 다른 action을 적용할 때 생기는 **global-policy collapse와 cross-unit contamination**이다.

## 읽는 순서

1. [현재 결론과 안내](START_HERE.md)
2. [파일럿 1 결과](docs/pilot1_search/result.md)
3. [파일럿 1 전체 판정표](results/pilot1/final_llm_judgment_table.md)
4. [파일럿 2: Compositional Memory Conflict](docs/pilot2_memory/plan.md)

배경 문서는 다음과 같다.

5. [기존 문제 정의와 제안 방법](docs/background/problem_and_method.md)
6. [관련 논문: 문제·방법·한계](docs/background/related_work.md)
7. [검색 다중·복합 충돌 데이터 근거](docs/background/dataset_evidence.md)
8. [파일럿 1 사전 계획](docs/pilot1_search/plan.md)
9. [주석 지침](docs/pilot1_search/annotation_guideline.md)
10. [파일럿 1 실행 안내](docs/pilot1_search/runbook.md)

## 작업 구조

```text
docs/       문제 정의, 문헌 조사, 파일럿 계획·결과
src/        전처리·주석·평가 코드
data/       표본·주석·판정본·split
results/    파일럿 및 본실험 산출물
tests/      연구 전용 회귀 테스트
```

AIR 연구의 스키마나 코드를 암묵적으로 import하지 않는다. 재사용이 확정된 중립 유틸리티가 생길 때만 별도 공용 모듈로 승격한다.
