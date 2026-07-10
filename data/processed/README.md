# 전처리 산출물 (공통 스키마 JSONL)

**git 미포함.** 원본 문서 본문을 담고 있어(QACC는 CC BY-SA 3.0 ShareAlike 대상)
커밋하지 않는다. `data/raw/download.sh` + `preprocessing/` 코드 + `checksums.lock`으로
완전히 재현된다.

```bash
bash data/raw/download.sh                     # 체크섬 고정 다운로드
python -m preprocessing.ramdocs_prep          # 가장 기계적 → 먼저 (Phase 1-1)
python -m preprocessing.dragged_prep draft    # 골드 매핑 초안
python -m preprocessing.dragged_prep sheet    # 전수 인간 검토 시트 생성
python -m preprocessing.qacc_prep convert     # 스키마 변환 + DRAGged 중복 제거
python -m preprocessing.schema data/processed/*.jsonl   # 산출물 검증 + 게이트 통과율
```

| 파일 | 생성 | 내용 |
|---|---|---|
| `ramdocs_a.jsonl` | `ramdocs_prep` | 분해형(충돌 1요인) — **본 실험용**. N=1016 (충돌 495 / 비충돌 521) |
| `ramdocs_b.jsonl` | `ramdocs_prep` | 원본 결합형 — 향후 과제용 보관. N=500 |
| `ramdocs_pairs.jsonl` | `ramdocs_prep` | RQ3 within-item 매칭 대조쌍. 338쌍 (문서 수 고정) |
| `dragged.draft.jsonl` | `dragged_prep draft` | 골드 매핑 초안. N=458 |
| `dragged.jsonl` | `dragged_prep final` | 인간 검증 반영 확정본 (검토 시트 작성 후) |
| `qacc.draft.jsonl` | `qacc_prep convert` | 충돌 381 → DRAGged 중복 제거 후 333 |
| `qacc.jsonl` | `qacc_prep final` | 스크리닝 게이트 통과분 (판정 시트 작성 후) |

## 실측으로 확정된 수치 (2026-07-10)

- **DRAGged**: conflict_type 분포 161/115/115/62/5 — 계획서 Table 2와 정확히 일치.
  사실 충돌 67건 중 자동 해소 50 · 인간 검증 대기 11 · 날짜로 해소 불가 6
  → **채점 가능 상한 61건** (계획서 사전 점검 예상 56~61에 부합).
- **QACC**: 충돌 381건(답 2/3/4개 = 243/94/44) — 계획서 실측과 일치.
  DRAGged 중복 48건 제거(계획서 47), 그중 DRAGged가 비충돌로 판정한 경계 사례 28건(계획서 27).
- **RAMDocs**: 500문항, 문항당 평균 5.53문서, gold 평균 2.2개 — 계획서와 일치.
