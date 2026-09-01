# 파일럿 1 · 자연 검색 문서의 `K/H` 분석

## 상태

완료했다. ConfRAG 120건, NatConfQA 22건, QACC 60건 등 총 202건에서 strict `K>1,H>1`은 관측되지 않았다.

따라서 자연 검색에서 query-level 복합 충돌이 충분히 흔하다는 주장은 유지하지 않으며, 기존 자연 `H=1/H>1` matched 파일럿 2도 수행하지 않는다.

## 읽는 순서

1. [결과와 연구 결정](result.md)
2. [사전 실험 계획](plan.md)
3. [실제 실행·재현 안내](runbook.md)
4. [향후 정식 주석 지침](annotation_guideline.md)

## 산출물

- [202건 전체 판정표](../../results/pilot1_search/final_llm_judgment_table.md)
- [최종 구조화 판정](../../data/pilot1_search/final_llm_judgments.jsonl)
- [표본 manifest](../../data/pilot1_search/sample_manifest.json)

사전 계획과 실제 실행은 다르다. 시간 제약으로 독립 인간 주석 대신 Codex direct 판정을 사용했으며, 정확한 변경과 한계는 `result.md`에 기록했다.
