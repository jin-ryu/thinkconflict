# 02 · Composite Conflict Resolution

실제 검색 문맥에서 독립적인 충돌 단위의 수 `K`와 서로 다른 해결 연산의 수 `H`를 분리하고, `H>1`인 복합 충돌을 학습 없이 해결하는 연구다.

## 현재 결론

- **다중 충돌**: 독립적인 core conflict unit이 여러 개인 경우(`K>1`)
- **복합 충돌**: 서로 다른 core resolution operator가 함께 필요한 경우(`H>1`)
- 1차 목표는 ConfRAG·NatConfQA 등 자연 검색 문서에서 `K/H`를 주석해 복합 충돌의 존재와 분포를 검증하는 것이다.
- 2차 목표는 파일럿 1의 동일 데이터를 재사용해, 같은 `K`에서도 `H`가 높을 때 기존 방법의 성능이 떨어지는지 검증하는 것이다.
- 이후 atomic conflict decomposition → operator assignment → global plan composition으로 이어지는 training-free PCCR 파이프라인을 개발한다.

## 정본 문서

1. [문제 정의와 제안 방법](docs/01_problem_and_method.md)
2. [관련 논문: 문제·방법·한계](docs/02_related_work.md)
3. [다중·복합 충돌 데이터 근거](docs/03_dataset_evidence.md)
4. [파일럿 1: 자연 복합 충돌 존재·분포](docs/04_pilot1_prevalence_plan.md)
5. [파일럿 2: H의 독립 난이도 효과](docs/05_pilot2_h_effect_plan.md)

문서 번호가 읽는 순서다. 날짜는 파일명 대신 문서의 변경 이력과 Git으로 관리한다.

## 작업 구조

```text
docs/       문제 정의, 문헌 조사, 파일럿 계획
src/        전처리·주석·PCCR·평가 코드(구현 시 하위 패키지 생성)
data/       이 연구에서 만든 표본·주석·판정본·split
results/    파일럿 및 본실험 산출물
tests/      복합 충돌 연구 전용 회귀 테스트
```

AIR 연구의 스키마나 코드를 암묵적으로 import하지 않는다. 재사용이 확정된 중립 유틸리티가 생길 때만 별도 공용 모듈로 승격한다.
