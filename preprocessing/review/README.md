# 사람 검증 시트 (검증 이력 자체가 산출물)

이 디렉터리의 파일은 **커밋 대상**이다. 라벨 규약이 실험 전에 확정됐음을, 그리고
인간 검증이 실제로 수행됐음을 남기는 물증이기 때문이다 (계획서 §5 사전등록 git 전략).

| 파일 | 생성 | 용도 |
|---|---|---|
| `dragged_review.csv` | `python -m preprocessing.dragged_prep sheet` | DRAGged 사실 충돌(temporal+misinfo) 전수 인간 검토 — 정답 문서 골드 매핑 교정 + 정답 정오표(예: "Boston Celtis"→"Boston Celtics") |
| `qacc_screen.csv` | 판정자 2종 실행 후 수기 정리 | QACC 스크리닝 게이트 ① sharp/soft 재분류 + 인간 스팟체크. `verdict` 컬럼이 `sharp`인 문항만 채점 트랙 투입 |
| `label_kappa.csv` | Phase 3-2 | 인간 2인 라벨(AIR·Discordant Hit 양성 전수 + 층화 표본 ~200건)과 Cohen's κ. L2 κ < 0.7이면 라벨 정의 수정 후 재라벨링 |

## 검토 규칙

- **복수 매칭은 제외 사유가 아니라 해소 대상**이다 (사전등록 §3.2). 매칭 문서 중
  `date` 최신성 + 정답 지지로 유효 문서를 고른다. 날짜 동률·부재만 플래그한다.
- 정답 오탈자를 발견하면 `corrected_answer` 컬럼에 기입한다 — 원본 값은
  `meta.answer_errata`에 보존된다.
- 판정자 불일치 문항은 인간 전문가가 adjudication하여 최종 라벨을 확정한다 (부록 A(b)).
