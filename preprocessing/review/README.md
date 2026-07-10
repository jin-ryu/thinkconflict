# 사람 검증 시트 (검증 이력 자체가 산출물)

이 디렉터리의 파일은 **커밋 대상**이다. 라벨 규약이 실험 전에 확정됐음을, 그리고
인간 검증이 실제로 수행됐음을 남기는 물증이기 때문이다 (계획서 §5 사전등록 git 전략).

| 파일 | 생성 | 용도 |
|---|---|---|
| `dragged_review.csv` | `python -m preprocessing.dragged_prep sheet` | DRAGged 사실 충돌(temporal+misinfo) 67문항 전수 인간 검토 — 골드 매핑 교정 + 정답 정오표 |
| `dragged_llm_labels.csv` | `python -m preprocessing.llm_assist dragged` | LLM 초벌 라벨 제안(PPT 12p ①). 검토자가 위 시트를 채울 때 참조 — 확정은 항상 사람 |
| `qacc_screen.csv` | `python -m preprocessing.qacc_prep screen` | QACC 스크리닝 게이트 ①·③ 템플릿(N=333). LLM 판정자 2종이 judge1/judge2(+type) 열을 채우고, 사람이 `verdict`·`final_type`을 확정 — `sharp`만 채점 트랙 투입 |
| `label_kappa.csv` | Phase 3-2 | 인간 2인 라벨(AIR·Discordant Hit 양성 전수 + 층화 표본 ~200건)과 Cohen's κ. L2 κ < 0.7이면 라벨 정의 수정 후 재라벨링 |

## LLM 초벌 워크플로 (Phase 1의 LLM 소요 전부 — `preprocessing/llm_assist.py`)

**순서가 중요하다**: `llm_assist dragged`를 먼저 돌려야 `dragged_prep sheet`가
LLM 제안을 `llm_label` 열로 프리필한다.

```bash
# 어떤 OpenAI 호환 엔드포인트든 사용 가능 — 자체 서빙 오픈 모델이면 비용 0
python -m preprocessing.dragged_prep draft                                    # 규칙: correct만 확정
python -m preprocessing.llm_assist  dragged --base-url http://HOST:PORT/v1 --model MODEL
python -m preprocessing.dragged_prep sheet                                    # LLM 제안 프리필
#   ↳ 사람이 dragged_review.csv의 final_label을 확정
python -m preprocessing.dragged_prep final

python -m preprocessing.qacc_prep   screen                                    # 판정 시트 템플릿
python -m preprocessing.llm_assist  qacc --judge 1 --base-url ... --model MODEL_A
python -m preprocessing.llm_assist  qacc --judge 2 --base-url ... --model MODEL_B  # 다른 계열
#   ↳ 사람이 verdict·final_type을 확정
python -m preprocessing.qacc_prep   final
```

- RAMDocs는 LLM이 필요 없다(라벨 원본 승계).
- 판정자 2종은 서로 다른 계열이어야 한다(부록 A(a) 자기선호 편향 통제).
- 중단 후 재실행하면 이미 판정된 행은 건너뛴다(재개 가능).

### `dragged_review.csv` 컬럼 읽는 법

| 컬럼 | 의미 |
|---|---|
| `rule_label` | 규칙이 확정한 것 — `correct`만 채워진다 (60문서) |
| `rule_hint` | `matched_older`(정답 문자열을 담았으나 구버전) / `unmatched`(정답 문자열 없음) — **참고용, 확정 아님** |
| `llm_label` | LLM 초벌 제안 (`llm_assist dragged` 실행 시) |
| `final_label` | **검토자가 확정하는 값.** 비워 두면 `llm_label`이 대신 쓰인다 |
| `doc_excerpt` | 판단을 돕는 본문 앞 40단어 |

`rule_hint = unmatched`라고 해서 무관한 문서가 아니다 — 정답과 **다른 답을 주장하는
충돌 문서**가 여기 섞여 있다(예: 정답 "at least 1,759"에 "1,762"를 주장하는 문서).
이 구분이 유효 충돌 게이트를 좌우하므로 본문을 보고 판단해야 한다 (사전등록 §7.6).

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
