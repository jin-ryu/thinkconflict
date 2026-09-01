# Composite Conflict 문서 안내

연구 문서는 현재 연구 단계와 파일럿별로 구분한다.

## 현재 읽는 순서

1. [연구 전체 안내](../START_HERE.md)
2. [Stage J 결과](pilot2_memory/stage_j_result.md)
3. [파일럿 2 Stage I–J: 데이터 보강과 간섭 검증](pilot2_memory/stage_ij_plan.md)
4. [2026 memory conflict 연구 조사](background/related_work_memory_2026.md)
5. [Stage H 최신 결과](pilot2_memory/stage_h_result.md)
6. [Stage G factorial 결과](pilot2_memory/stage_g_result.md)
7. [파일럿 2: Compositional Memory Conflict](pilot2_memory/README.md)
8. [파일럿 1: 자연 검색 conflict](pilot1_search/README.md)

## 폴더 구조

```text
docs/
├── README.md
├── background/
│   ├── problem_and_method.md          # 기존 검색 연구안
│   ├── memory_problem_and_method.md   # 현재 memory 연구안
│   ├── related_work.md
│   ├── related_work_memory_2026.md    # 2026 memory conflict 조사
│   └── dataset_evidence.md
├── pilot1_search/
│   ├── README.md
│   ├── plan.md
│   ├── annotation_guideline.md
│   ├── runbook.md
│   └── result.md
├── pilot2_memory/
│   ├── README.md
│   ├── plan.md
│   ├── result.md
│   ├── stage_f_result.md
│   ├── stage_g_result.md
│   ├── stage_h_result.md
│   ├── stage_ij_plan.md               # Stage I–J 데이터 보강·간섭 검증 계획
│   └── stage_j_result.md              # Stage J 결과: 4 모델, 가설 판정, 방향 제안
└── pilot3_cmcr/
    └── plan.md                        # CMCR 방법 계획 초안, Stage J 통과 후
```

`background/problem_and_method.md`는 기존 검색 연구안을 보존한다. 현재 연구 본문은 `background/memory_problem_and_method.md`, 실행 계획의 정본은 `pilot2_memory/plan.md`(Stage A–H)와 `pilot2_memory/stage_ij_plan.md`(Stage I 이후)다. `dataset_evidence.md`는 검색 conflict와 memory conflict를 Part로 분리한다.

실험 데이터와 판정 결과는 문서 폴더에 복사하지 않는다.

- 파일럿 1 데이터: [`../data/pilot1_search/`](../data/pilot1_search/)
- 파일럿 1 결과표: [`../results/pilot1_search/`](../results/pilot1_search/)
- 파일럿 2 데이터: [`../data/pilot2_memory/`](../data/pilot2_memory/)
- 파일럿 2 결과: [`../results/pilot2_memory/`](../results/pilot2_memory/)
