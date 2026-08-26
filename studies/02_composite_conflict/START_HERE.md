# Composite Conflict Study — START HERE

## 지금 확인할 결론

자연 검색 문서 202건을 strict `K/H` 기준으로 판정했지만 `K>1,H>1` 복합 충돌은 관측되지 않았다.

- ConfRAG 무작위 120건: 0건
- NatConfQA strict WH-mix 22건: 0건
- QACC 무작위 60건: 0건

따라서 “자연 검색에서 복합 충돌이 충분히 자주 발생한다”는 주장은 유지하지 않는다. ConfRAG 0/120의 양측 95% Wilson 상한은 약 3.1%다.

`K/H` formulation 자체는 유지하되, 다음 파일럿은 장기 사용자 메모리에서 여러 query-relevant conflict unit과 서로 다른 해결 정책의 조합이 자연스럽고 어려운지를 검증한다. 일반적인 memory-conflict 분류가 아니라 **Compositional Memory Conflict**가 새 연구 후보이다.

## 지금 볼 파일 세 개

1. [`docs/pilot1_search/result.md`](docs/pilot1_search/result.md)
   - 파일럿 1 결과, 실행 방식, 계획 대비 변경, 연구 결정
2. [`results/pilot1/final_llm_judgment_table.md`](results/pilot1/final_llm_judgment_table.md)
   - 데이터셋별 분포와 202건 전체 판정표
3. [`docs/pilot2_memory/plan.md`](docs/pilot2_memory/plan.md)
   - 새 파일럿 2의 문제 정의, 데이터, 실험, go/stop 기준

구조화된 최종 판정은 [`data/pilot1/final_llm_judgments.jsonl`](data/pilot1/final_llm_judgments.jsonl)에 있다.

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

## 나머지 문서의 용도

- `docs/background/problem_and_method.md`: 기존 검색 중심 논문 초안; memory 파일럿 통과 전에는 확정 본문이 아님
- `docs/background/related_work.md`: 검색 문서 conflict 관련 연구
- `docs/background/dataset_evidence.md`: 검색 conflict 데이터셋 조사
- `docs/pilot1_search/plan.md`: 파일럿 1의 사전 계획과 실제 실행 안내
- `docs/pilot1_search/annotation_guideline.md`, `docs/pilot1_search/runbook.md`: 재현·정식 주석 운영 자료

현재 의사결정에는 위 문서 전체를 읽을 필요가 없다.
