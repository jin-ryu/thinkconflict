# ThinkConflict

문서 충돌(document conflict)을 서로 다른 두 연구 질문으로 나누어 관리하는 저장소다.

| 연구 | 핵심 질문 | 현재 상태 | 시작 문서 |
|---|---|---|---|
| [01 · AIR trace audit](studies/01_air_trace/README.md) | 충돌 상황에서 추론 모델의 인지·판정·표출 실패는 어디서 발생하는가? | 파일럿 완료, 본실험 설계 | [실험 계획](studies/01_air_trace/docs/experiments/01_experiment_plan.md) · [파일럿 결과](studies/01_air_trace/docs/experiments/02_pilot_result.md) |
| [02 · Composite conflict](studies/02_composite_conflict/README.md) | `K`와 `H`가 큰 검색 문맥에서 서로 다른 해결 연산을 어떻게 합성할 것인가? | 문제 정의·파일럿 설계 | [문제와 방법](studies/02_composite_conflict/docs/01_problem_and_method.md) · [파일럿 1](studies/02_composite_conflict/docs/04_pilot1_prevalence_plan.md) · [파일럿 2](studies/02_composite_conflict/docs/05_pilot2_h_effect_plan.md) |

## 저장소 구조

```text
studies/
  01_air_trace/             기존 추론 trace 분석 연구: 문서·코드·데이터·결과
  02_composite_conflict/    복합 충돌 연구: 문서와 향후 실험 공간
literature/papers/          두 연구가 함께 참고하는 논문 원문(git 미포함)
requirements.txt            현재 공통 Python 환경
pytest.ini                  루트에서 AIR 회귀 테스트를 실행하기 위한 설정
```

각 연구의 실행 명령과 정본 문서는 해당 연구의 `README.md`에서 확인한다. 연구 전용 산출물은 다른 연구 폴더에 두지 않는다.

## 빠른 검증

```bash
pip install -r requirements.txt
pytest
```

루트 `pytest`는 현재 구현이 존재하는 AIR 연구의 회귀 테스트를 실행한다.
