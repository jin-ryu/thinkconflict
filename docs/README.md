# docs/ 문서 지도

**어디에 두는지가 곧 문서의 상태다.**

| 위치 | 유형 | 규칙 |
|---|---|---|
| `preregistration.md` (자리 고정) | 사전등록 규약 | **수정·이동 금지** — 커밋 타임스탬프가 사전등록의 물증. 개정은 새 조항 추가 커밋으로만 |
| `plan/` | 기준 문서 (살아있음) | 연구의 현재 정본. 계획이 바뀌면 **이 문서를 고친다** — 새 문서를 만들지 않는다 |
| `admin/` | 학사·행정 | 제출 양식 등 연구 내용과 무관한 파일 |

## plan/ — 기준 문서

| 파일 | 내용 |
|---|---|
| `연구계획서_ThinkConflict.md` | 정본 계획서 — 코드 주석의 "계획서 §x.x"가 가리키는 문서 |
| `ThinkConflict_연구보고.pptx` | 최신 연구 계획 발표본 (24슬라이드) — 5유형 분류(11p)·3단계 라벨(15p)·RQ별 지표(17p)의 근거 |

## 일회성 작업 문서는 남기지 않는다

인수인계·부트스트랩 절차서 같은 일회성 문서는 **작업이 끝나면 삭제**한다. 기록은 git 히스토리에 남는다:

```bash
git log --diff-filter=D --summary -- docs/   # 삭제된 문서 목록
git show <해시>:docs/archive/pilot_handoff.md # 내용 복원
```

삭제 이력: `pilot_handoff.md`(8/21 파일럿, 산출물은 results/) · `dragged_label_bootstrap.md`(적용 완료, 라벨·출처는 data/2_review/dragged/) · `thinkconflict_repo_plan.md`(구축 완료, 루트 README가 정본)

## 실행 기록은 여기가 아니다

실험을 **어떻게 돌렸는지**(설정·건수·중간 변경·한계)는 `results/RUNLOG.md`에 쓴다.
docs/는 "무엇을 왜 하는가"(계획·규약), results/는 "무엇을 어떻게 했는가"(기록)로 가른다.
