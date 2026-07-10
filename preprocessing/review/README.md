# 사람 검증 시트 (검증 이력 자체가 산출물)

이 디렉터리의 파일은 **커밋 대상**이다. 라벨 규약이 실험 전에 확정됐음을, 그리고
인간 검증이 실제로 수행됐음을 남기는 물증이기 때문이다 (계획서 §5 사전등록 git 전략).

| 파일 | 생성 | 용도 |
|---|---|---|
| `dragged_review.csv` | `python -m preprocessing.dragged_prep sheet` | DRAGged 사실 충돌(temporal+misinfo) 67문항 전수 인간 검토 — 골드 매핑 교정 + 정답 정오표 |
| `qacc_screen.csv` | `python -m preprocessing.qacc_prep screen` | QACC 스크리닝 게이트 ①·③ 템플릿(N=333). 판정자 2종 결과와 인간 스팟체크를 채운 뒤 `verdict` 열이 `sharp`인 문항만 채점 트랙 투입 |
| `label_kappa.csv` | Phase 3-2 | 인간 2인 라벨(AIR·Discordant Hit 양성 전수 + 층화 표본 ~200건)과 Cohen's κ. L2 κ < 0.7이면 라벨 정의 수정 후 재라벨링 |

## 검토 규칙

- **복수 매칭은 제외 사유가 아니라 해소 대상**이다 (사전등록 §3.2). 시간 충돌은
  매칭 문서 중 `date` 최신본을 correct로 둔다. 매칭 문서를 날짜로 전혀 나눌 수 없을
  때만(전부 같은 날짜 = `date_tie`, 날짜 전무 = `date_absent`) 해소 불가로 플래그한다.
- **오정보 충돌은 최신성이 아니라 출처 권위로 갈린다** — 자동 해소하지 않고
  `multi_match_needs_authority`로 플래그해 사람에게 넘긴다(5건뿐이라 전수 검증 가능).
- 정답 오탈자를 발견하면 `corrected_answer` 컬럼에 기입한다 — 원본 값은
  `meta.answer_errata`에 보존된다. (실측 확인: `"Boston Celtis"`, `"Bolovia"`)
- `final_label`을 채운 문항은 `exclusion_flag`가 해제되어 채점 트랙에 들어간다.
- 판정자 불일치 문항은 인간 전문가가 adjudication하여 최종 라벨을 확정한다 (부록 A(b)).

## 실측 기준 검토 물량 (2026-07-10)

| 대상 | 건수 | 비고 |
|---|---|---|
| DRAGged 사실 충돌 전수 | 67문항 (623문서) | 그중 플래그 17건이 우선 검토 대상 |
| ├ 무매칭 | 6 | NLI·정오표 교정으로 회수 가능 |
| ├ 오정보 복수 매칭 | 5 | 출처 권위로 사람이 판정 |
| └ 날짜 해소 불가 | 6 | `date_tie` 3 + `date_absent` 3 |
| QACC 스크리닝 | 333문항 | sharp/soft 재분류 + 정답 재검증 16건 |
