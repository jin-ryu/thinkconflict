# 최종 산출물 (실험이 읽는 유일한 입력)

여기 있는 JSONL은 **검토가 끝난 것만** 들어온다. 두 겹으로 막는다:

1. **`build`가 미완료 상태의 최종본을 만들지 않는다.** 사실 충돌에 라벨 미확정 문서가
   남아 있으면(DRAGged), 게이트 ①이 안 끝났으면(QACC) 오류로 중단한다.
2. **실험이 `data/review/` 경로를 거부한다.** `serving/client.py`·`diagnosis/run_labeling.py`가
   초안 경로를 입력으로 받으면 실행을 멈춘다.

검토 전 데이터로 실험을 돌려 놓고 결과를 믿는 사고를 코드로 막는 장치다 —
라벨이 미확정이어도 파이프라인은 아무 불평 없이 숫자를 뱉기 때문이다(AIR도, 전환 행렬도).

## 현재 상태

RAMDocs만 최종본이 있다. 원본에 라벨이 내장돼 있어 **검토가 필요 없는 유일한 데이터셋**이다.
DRAGged·QACC는 `data/review/`에서 검토 중이며, 끝나면 여기에 유형별 파일이 생긴다.

## 파일 하나가 곧 하나의 실험 조건이다

트랙 플래그를 아이템에 달고 다니지 않는다 — **충돌 유형별로 파일이 나뉘어 있고**,
분석이 필요한 파일만 골라 합친다. 정답이 없는 의견 충돌은 애초에 채점 파일에 섞이지 않으므로,
실수로 채점 파이프라인에 넣을 수 없다.

| 파일 | N | 정답 | 쓰임 |
|---|---|---|---|
| `dragged_temporal.jsonl` | 62 | ✅ | **채점**(정확도·AIR) 충돌군 + 자기일관성 충돌측 |
| `dragged_misinfo.jsonl` | 5 | ✅ | 〃 |
| `dragged_none.jsonl` | 161 | ✅ | **채점** 비충돌 대조군(ⓒ) + 자기일관성 비상충측 |
| `dragged_opinion.jsonl` | 115 | ❌ | **자기일관성 전용** (정답이 하나로 안 정해지는 질문) |
| `dragged_complementary.jsonl` | 115 | ❌ | 자기일관성 비상충측 |
| `qacc_temporal/misinfo/opinion.jsonl` | 게이트 통과분 | 유형별 | 〃 (DRAGged와 동일 구조) |
| `ramdocs_a.jsonl` | 1,016 | ✅ | 분해형(충돌 1요인) — **본 실험용** |
| `ramdocs_b.jsonl` | 500 | ✅ | 원본 결합형 — 향후 과제용 |
| `ramdocs_pairs.jsonl` | 676 | ✅ | RQ3 within-item 매칭 338쌍 — **쪼개면 안 된다**(충돌·대조 짝이 한 파일에 있어야 함) |

**실험별로 쓰는 파일**

```
정확도·AIR·4경로 (RQ1·RQ2) : dragged_temporal + dragged_misinfo   vs  dragged_none
자기일관성 (§3.2 이중 트랙)  : + dragged_opinion (충돌측 182)       vs  + dragged_complementary (비상충측 276)
RQ3 매칭 대조              : ramdocs_pairs (단일 파일)
```

> ⚠️ **공개 시 라이선스 확인.** 이 산출물은 원본 문서 본문을 포함한다. 논문용 익명 미러를
> 만들 때 QACC 파생물은 **CC BY-SA 3.0**(저작자 표시 + 동일조건변경허락) 대상임을 확인할 것.
> 라이선스 사본: `data/raw/LICENSES/`.

검증: `python -m preprocessing.schema data/processed/*/*.jsonl`
