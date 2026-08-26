# 파일럿 2 · Compositional Memory Conflict

## 상태

계획 완료, 실행 전이다. 기존 검색 기반 `H` 효과 실험을 대체한다.

## 핵심 질문

1. 동일 persona의 long-term memory에서 자연스러운 `K>1,H>1` 사용자 요청을 구성할 수 있는가?
2. `K=2`를 고정해도 `H=2`에서 기존 모델의 all-unit success가 낮아지는가?
3. 하나의 정책을 모든 memory slot에 적용하는 global-policy collapse가 나타나는가?
4. gold unit과 unit별 policy를 제공하면 성능이 회복되는가?

## 이 파일럿의 역할

generic memory conflict taxonomy나 단일 action routing을 다시 제안하지 않는다. MemConflict와 TANGLE이 주로 한 target attribute/aspect를 평가한다는 공백을 바탕으로, 여러 query-relevant conflict unit의 해결 정책을 하나의 응답으로 조합하는 문제만 검증한다.

상세 데이터 구성, baseline, 평가 지표와 go/revise/stop 기준은 [실험 계획](plan.md)을 따른다. 파일럿 1의 근거는 [검색 conflict 결과](../pilot1_search/result.md)에 있다.
