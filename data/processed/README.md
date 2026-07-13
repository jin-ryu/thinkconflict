# 최종 산출물 (실험이 읽는 유일한 입력)

여기 있는 JSONL은 **검토가 끝난 것만** 들어온다. 작업 중인 초안은 `data/interim/`에 있고,
`serving/client.py`·`diagnosis/run_labeling.py`는 `data/interim/` 경로를 **거부한다** —
검토 전 데이터로 실험을 돌려 놓고 결과를 믿는 사고를 코드로 막는다.

| 파일 | 생성 | 상태 |
|---|---|---|
| `ramdocs_a.jsonl` | `ramdocs_prep` | ✅ 분해형(충돌 1요인) — **본 실험용**, N=1,016 |
| `ramdocs_b.jsonl` | `ramdocs_prep` | ✅ 원본 결합형 — 향후 과제용, N=500 |
| `ramdocs_pairs.jsonl` | `ramdocs_prep` | ✅ RQ3 within-item 매칭 338쌍 |
| `dragged.jsonl` | `dragged_prep build` | ⏳ 검토 후 생성 (상한 62건) |
| `qacc.jsonl` | `qacc_prep build` | ⏳ 판정 후 생성 (예상 ~134건) |

> ⚠️ **공개 시 라이선스 확인.** 이 산출물은 원본 문서 본문을 포함한다. 논문용 익명 미러를
> 만들 때 QACC 파생물은 **CC BY-SA 3.0**(저작자 표시 + 동일조건변경허락) 대상임을 확인할 것.
> 라이선스 사본: `data/raw/LICENSES/`.

검증: `python -m preprocessing.schema data/processed/*.jsonl`
