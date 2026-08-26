# Composite Conflict 문서 안내

연구 문서는 현재 연구 단계와 파일럿별로 구분한다.

## 현재 읽는 순서

1. [연구 전체 안내](../START_HERE.md)
2. [파일럿 1: 자연 검색 conflict](pilot1_search/README.md)
3. [파일럿 2: Compositional Memory Conflict](pilot2_memory/README.md)

## 폴더 구조

```text
docs/
├── README.md
├── background/
│   ├── problem_and_method.md
│   ├── related_work.md
│   └── dataset_evidence.md
├── pilot1_search/
│   ├── README.md
│   ├── plan.md
│   ├── annotation_guideline.md
│   ├── runbook.md
│   └── result.md
└── pilot2_memory/
    ├── README.md
    └── plan.md
```

`background/`는 검색 문서 conflict를 중심으로 작성했던 문제 정의와 문헌 조사 기록이다. 파일럿 1의 부정 결과 이후 현재 실행 계획의 정본은 `pilot2_memory/plan.md`다.

실험 데이터와 판정 결과는 문서 폴더에 복사하지 않는다.

- 파일럿 1 데이터: [`../data/pilot1/`](../data/pilot1/)
- 파일럿 1 결과표: [`../results/pilot1/`](../results/pilot1/)
