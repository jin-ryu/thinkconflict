# 라벨 이력 (검증 이력 자체가 산출물)

이 디렉터리의 `*_labels.csv`는 **커밋 대상**이다. 라벨 규약이 실험 전에 확정됐음을, 그리고
인간 검증이 실제로 수행됐음을 남기는 물증이기 때문이다 (계획서 §5 사전등록 git 전략).

**작업용 CSV는 여기가 아니라 `data/processed/<ds>/`에 있다.** 그쪽은 원본 본문을 담아
커밋할 수 없으므로(QACC CC BY-SA 3.0), `build` 단계가 **본문을 뺀 판정 결과만** 여기로
내보낸다.

| 파일 | 생성 | 내용 |
|---|---|---|
| `dragged_labels.csv` | `dragged_prep build` | 문서별 rule/llm/final 라벨 + 정답 정오표 |
| `qacc_labels.csv` | `qacc_prep build` | 문항별 sharp/soft 판정 + 유형 확정 |
| `label_kappa.csv` | Phase 3-2 | 인간 2인 라벨(AIR·Discordant Hit 양성 전수 + 층화 표본 ~200건)과 Cohen's κ. L2 κ < 0.7이면 라벨 정의 수정 후 재라벨링 |

## 검토는 어디서 하나

`data/processed/dragged/dragged.llm.csv` (또는 LLM 전이면 `dragged.draft.csv`)를
Excel/Numbers로 열어 **`final_label` 열만 채우면 된다.** 빈칸으로 두면 `llm_label`이,
그것도 없으면 `rule_label`이 쓰인다.

### 검토 규칙

- **복수 매칭은 제외 사유가 아니라 해소 대상**이다 (사전등록 §3.2). 시간 충돌은 매칭 문서 중
  `date` 최신본을 `correct`로 둔다. 날짜로 전혀 나눌 수 없을 때만(`date_tie`/`date_absent`)
  해소 불가로 플래그한다.
- **오정보 충돌은 최신성이 아니라 출처 권위로 갈린다** — 자동 해소하지 않고
  `multi_match_needs_authority`로 플래그해 사람에게 넘긴다(5건뿐이라 전수 판정 가능).
- **`rule_hint = unmatched`는 "무관 문서"가 아니다.** 정답과 다른 답을 주장하는 충돌 문서가
  여기 섞여 있다 — `text` 열을 보고 판단해야 한다 (사전등록 §7.6).
- 정답 오탈자는 `corrected_answer`에 기입한다. 원본 값은 `meta.answer_errata`에 보존된다.
  (실측 확인: `Boston Celtis`, `Bolovia`)
- `build`가 **규칙↔LLM 불일치 건수를 경고로 출력**한다 — 그 문서는 사람이 반드시 확인한다.
- QACC 판정자 2종이 불일치한 문항은 `llm_verdict`가 비어 있다 → 사람이 adjudication한다
  (부록 A(b)).

## 실측 기준 검토 물량 (2026-07-13)

| 대상 | 건수 | 비고 |
|---|---|---|
| DRAGged 사실 충돌 전수 | 67문항 (623문서) | 그중 **563문서가 확정 필요**(빈칸) |
| ├ 무매칭 | 6 | LLM·정오표로 회수 가능 |
| ├ 오정보 복수 매칭 | 5 | 출처 권위로 사람이 판정 |
| └ 날짜 해소 불가 | 5 | `date_tie` 3 + `date_absent` 2 |
| QACC 스크리닝 | 333문항 | sharp/soft 재분류 + 정답 재검증 12건 |
