# ThinkConflict 새 레포 구축 계획서

> 이 문서는 새 레포의 부트스트랩 계획서다. 기존 `temporal-conflict-qa` 레포에서 데이터·코드를
> 이관하지 않고, `연구계획서_ThinkConflict.md`만을 기준으로 처음부터 새로 시작한다.
> 새 레포로 넘어가는 파일은 연구계획서와 이 문서 둘뿐이며, 첫 커밋에 포함시켜
> 구축 계획 자체가 git 이력의 시작점이 되게 한다.
> 작성일: 2026-07-10

---

## 1. 레포 이름

**추천: `thinkconflict`**

- 프로젝트 코드네임과 일치해 계획서·PPT·레포가 한 이름으로 연결된다.
- 짧고 검색 충돌이 없다 (GitHub에 동명 유명 레포 없음).
- 논문 공개 시 "ThinkConflict: ..." 형태의 레포 태그라인과 자연스럽게 이어진다.

차선 후보 (코드네임을 레포명에 쓰고 싶지 않을 때):

| 후보 | 성격 |
|---|---|
| `conflict-trace` | 충돌 + 추론 트레이스라는 관측 대상을 직접 드러냄 |
| `rag-conflict-diagnosis` | 서술형. 주제 검색성은 좋으나 길다 |

※ 더블블라인드 제출 시점에는 어차피 익명 미러(4open.science / Anonymous GitHub)를 따로 만들므로,
개인 레포 이름이 심사에 노출될 걱정은 하지 않아도 된다.

---

## 2. 시작점 원칙

- **가져오는 것**: `docs/연구계획서_ThinkConflict.md`(정본 계획서)와 이 문서. 끝.
- **데이터**: DRAGged·QACC·RAMDocs 3종 모두 원 출처에서 새로 받는다.
  `data/raw/download.sh` 하나로 전부 재현되게 만들고, 원본 파일 자체는 git에 넣지 않는다
  (LICENSE 사본과 다운로드 스크립트만 커밋).
- **코드**: 전부 새로 작성한다. 기존 레포의 파이프라인은 참고하지도, 복사하지도 않는다 —
  공통 스키마와 전처리 규약은 연구계획서에 이미 명세돼 있으므로 그것만 보고 구현한다.
- **문서 정본 규칙**: 이관 시점 이후 연구계획서 수정은 새 레포에서만 한다.
  기존 레포 사본은 스냅샷으로 동결.

---

## 3. 새 레포 디렉터리 구조

```
thinkconflict/
├── README.md                  # 한 줄 요약 + 연구 질문 4개 + 구조 안내
├── requirements.txt
├── docs/
│   ├── thinkconflict_repo_plan.md   # 이 문서
│   ├── 연구계획서_ThinkConflict.md   # 정본 계획서
│   └── preregistration.md           # 사전등록 규약 (§5 참조, 실험 전 커밋 필수)
├── data/
│   ├── raw/                   # 원본 (git 미포함, download.sh로 재현)
│   │   ├── download.sh        # DRAGged · QACC · RAMDocs 일괄 다운로드
│   │   ├── dragged/
│   │   ├── qacc/
│   │   └── ramdocs/
│   └── processed/             # 공통 스키마 JSON — 전처리 파이프라인 산출물
│       ├── dragged.jsonl
│       ├── qacc.jsonl
│       ├── ramdocs_a.jsonl    # 분해형 (충돌 1요인) = 본 실험용
│       └── ramdocs_b.jsonl    # 원본 결합형 = 향후 과제용 보관
├── preprocessing/
│   ├── schema.py              # 공통 스키마 정의 + 검증 (question·correct_answer·chunks[]·label)
│   ├── dragged_prep.py        # LLM 초벌 라벨 → 사람 전수 검토 시트 → 확정
│   ├── qacc_prep.py           # conflict_type 부여 + 사이비 충돌(표기차) 드롭 게이트
│   ├── ramdocs_prep.py        # 라벨 승계 + A/B 분리
│   └── review/                # 사람 검증 시트와 확정 결과 (검증 이력 자체가 산출물)
├── serving/
│   ├── launch_qwen.sh         # Qwen3.6-27B (vLLM, thinking on/off 토글)
│   ├── launch_gemma.sh        # Gemma-3-27B
│   ├── launch_gptoss.sh       # gpt-oss-20b (Harmony 파서 포함)
│   └── client.py              # 공통 생성 클라이언트 (t=0.6, top-p 0.95, 시드 관리)
├── diagnosis/
│   ├── trace_parser.py        # <think>/Harmony analysis 채널 추출
│   ├── labeler.py             # L1(탐지)·L2(해소)·FA(표출) 3단계 라벨링
│   ├── grading.py             # 동치 판정·any-gold·기권 분리 채점
│   └── metrics.py             # AIR · Loss_L1 · Loss_L2 · 4경로 분해 · LGR · HR · Flip
├── experiments/
│   ├── exp1_mitigation/       # RQ1·RQ2 — 5환경 × 3모델 × 3데이터셋, 전환 행렬
│   │   ├── envs/              # standard / cad / cd2 / recency_authority / reflection
│   │   └── transition.py      # 문항 짝지은 경로 이동 집계
│   ├── exp2_specificity/      # RQ3 — (a) 충돌 대조 + 혼합효과 회귀 (b) thinking on/off
│   └── exp3_causal/           # RQ4 — truncation / resampling / filler-token / 자연 종료점
├── results/                   # 실행 산출물 (raw 생성물은 git 미포함, 집계만 포함)
└── analysis/                  # 집계·그림·표 생성 노트북/스크립트
```

---

## 4. 구축 단계

각 Phase는 순서 의존적이며, Phase 0~1이 끝나야 GPU 실험이 의미 있다.

**Phase 0 — 부트스트랩 + 사전등록 (실험 코드 작성 전)**
1. 레포 생성, 이 문서와 연구계획서 커밋
2. `data/raw/download.sh` 작성 — 3개 데이터셋 원 출처·버전·체크섬 고정
3. `docs/preregistration.md` 작성·커밋: 라벨 규약(결론 확정·기권 분리·동치 채점·any-gold),
   N<20 셀 비교 금지, 인과 해석 규칙(filler-token 상한 확인 후 해석), 데이터셋별 분리 보고 원칙
4. 공통 스키마 확정 (`preprocessing/schema.py`)

**Phase 1 — 데이터 전처리 (3개 데이터셋 → 공통 스키마)**
1. RAMDocs: 라벨 승계 + A/B 분리 (가장 기계적 → 먼저)
2. QACC: conflict_type LLM 초벌 + 사이비 충돌 드롭 게이트 + 사람 검수 — ※ 유료 API 사용 전 비용 예측·승인 절차
3. DRAGged: 청크 라벨 LLM 초벌 → 사람 전수 검토 → 정오표 반영
4. 산출물 검증: 유효 충돌 게이트(정답+충돌 공존) 통과율, 데이터셋별 최종 N 확정 → 검정력 표 갱신

**Phase 2 — 서빙 + 트레이스 수집 인프라**
1. 3모델 서빙 스크립트 + 공통 클라이언트 (시드 5개 이상, 디코딩 고정)
2. 트레이스 파서 (Qwen `<think>` / gpt-oss Harmony) + 파싱 실패율 점검
3. **go/no-go 게이트**: 전면 마스킹 검사 — `<think>` 제거 시 답 분포 불변이면 진단 자체가 성립하지 않으므로 여기서 중단·재설계

**Phase 3 — 진단 프로토콜 구현**
1. L1·L2·FA 라벨러 + 채점기 (동치 판정·기권 분리·any-gold)
2. 라벨 타당성: 인간 이중 라벨 κ ≥ 0.7 확인 (계획서 기준)
3. 지표 산출기: AIR·Loss_L1·Loss_L2·4경로 분해 (분모 N 병기 강제)

**Phase 4 — 실험 1 (RQ1·RQ2): 완화 이득 분해**
1. 5환경 구현 — Standard / CAD(+AdaCAD, 대비 구간 2방식) / CD2 / Recency·Authority(RAMDocs 제외) / Reflection
2. 5환경 × 3모델 × 3데이터셋 실행 → 환경별 전환 행렬
3. LGR·HR·Flip 집계, 시드 다수결 + 불안정 플래그 분리

**Phase 5 — 실험 2 (RQ3): 충돌 고유성**
1. (a) DRAGged 자연 표본 between-item + 혼합효과 회귀 / RAMDocs 오정보↔노이즈 교체 within-item 최소대조
2. (b) Qwen thinking on/off 하드 토글 대조 (gpt-oss effort는 참고용)

**Phase 6 — 실험 3 (RQ4): 인과 개입**
1. Truncation(다지점) + On-policy Resampling(L2 직후) 주력
2. Filler-token 대조군 + 자연 종료점 기준선으로 형식 교란 상한 먼저 확정
3. 경로별 취약성: 4경로 각각에 동일 개입 → 뒤집힘 비율 비교

---

## 5. 사전등록 git 전략

새 레포를 파는 핵심 이유 중 하나. 규칙:

- 라벨 규약·해석 규칙·게이트 기준은 **해당 실험 데이터를 생성하기 전에** `docs/preregistration.md`로 커밋한다. 커밋 타임스탬프가 "실험 전에 못박았다"의 물증이 된다.
- 규약을 실험 후에 바꿔야 할 경우, 기존 항목을 지우지 않고 개정 이력(무엇을·왜)을 남긴다.
- `results/` 집계 산출물은 생성 즉시 커밋해 지표 계산 시점을 남긴다.

커밋 스타일은 기존과 동일: 한 줄, co-author 없음, 푸시는 명시 요청 시만.

---

## 6. 기존 레포(temporal-conflict-qa)의 이후 지위

- **동결 아카이브.** 새 커밋은 문서 정리·아카이브 안내 외에는 하지 않는다.
- V1~V3 파일럿 결과의 재현 근거로 보존한다 (PPT·계획서의 파일럿 수치 출처이므로 삭제 금지).
- 논문 제출 시 공개 대상은 새 레포(의 익명 미러)만이며, 이 레포는 비공개 유지.

동결 전 정리 체크리스트:

- [ ] `docs/~$ThinkConflict_연구보고.pptx` (파워포인트 잠금 파일) 삭제 + `.gitignore`에 `~$*` 추가
- [ ] PPT 수정: 슬라이드 17·18 중복 제거 / QACC 충돌 건수 381 vs 404 통일 / LGR 예시 행렬을 4상태(정상·취약정답·오답·기권)로 수정
- [ ] 마지막 상태를 커밋해 스냅샷 확정, README 상단에 "ThinkConflict는 새 레포로 이동" 안내 한 줄
