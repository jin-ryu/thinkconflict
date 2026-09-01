# 파일럿 3: CMCR-Linear 방법 개발·본실험 계획 (초안)

> 작성일: 2026-08-28
> 상태: **보류. 2026-08-28 Stage J에서 진입 조건 2~4가 미충족(H-B·H-C 기각). [stage_j_result.md](../pilot2_memory/stage_j_result.md)의 방향 제안 참고**
> 선행: [파일럿 2 Stage I–J 계획](../pilot2_memory/stage_ij_plan.md), [Stage H 결과](../pilot2_memory/stage_h_result.md)
> 근거: [plan.md §11.1](../pilot2_memory/plan.md#111-pilot-번호-결정)에 따라 CMCR 해결 방법론 자체를 개발·평가할 때만 파일럿 3을 연다

---

## 0. 진입 조건

파일럿 2 Stage J의 다음 결과를 모두 만족해야 한다. 상세 정의는 [stage_ij_plan.md §3](../pilot2_memory/stage_ij_plan.md#3-stage-j-간섭-검증-실험)에 있다.

1. J-0 frontier gate go
2. J-1 unit-level gap이 세 생성 모델 중 둘 이상에서 유의
3. J-2에서 no-conflict 통제군의 gap이 conflict cell보다 유의하게 작음
4. J-3(anchor 짝) 또는 J-4(policy leakage) 중 하나 이상 통과

Stage J가 실패하면 이 문서는 폐기하고 benchmark·분석 논문으로 전환한다.

---

## 1. 방법: CMCR-Linear

### 1.1 구조 (gold-free, 학습 없음)

```text
1. unit proposal        query를 atomic slot 후보로 분해
2. evidence ownership   record를 slot에 soft assignment, owner·조건 불확실성 기록
3. policy inference     slot별로 supersede / verify-prefer / condition / ask 중 하나 추론
4. local resolution     slot별 독립 해결 (slot 밖 record는 보이지 않음)
5. composition          slot 답을 하나의 응답으로 합성
6. selective recheck    누락 slot, 저신뢰 slot, order-disagreement slot만 재해결
```

Stage H에서 always-on verifier가 순증가 1건에 토큰 2배였으므로 6단계는 조건부다. 2~3단계를 한 call로 합치는 변형과 분리하는 변형을 둘 다 둔다.

### 1.2 비교군

| 조건 | 목적 |
|---|---|
| Direct | 현재 end-to-end |
| Generic CoT | 일반 추론 지시 |
| Global-policy ×2 (J-7) | collapse 재현 |
| **CAR-style** | Self-Ask 분해 + 모든 slot에 latest-wins. 2606.01435 대응. "분해만으로는 부족하고 policy 분리가 필요하다"를 보이는 핵심 baseline |
| CAAP-style | slot 분해 없이 instance 전체에 action 하나 |
| CMCR-Linear (2~3 합침) | |
| CMCR-Linear (분리) | |
| CMCR-Linear + selective recheck | |
| Oracle full_local (Stage H) | 상한 |

### 1.3 지표

- all-unit success, worst-order success, unit-level gap (J-1)
- policy inference 정확도 (gold policy 대비), evidence ownership F1
- leakage 혼동행렬 (J-4)
- cross-unit flip (J-5)
- token, call 수, latency. accuracy–cost frontier
- K3_H≥2를 primary stress subset으로 별도 보고

### 1.4 판정

- CMCR이 CAR-style보다 heterogeneous cell에서 유의하게 높고 homogeneous cell에서 나쁘지 않으면 method 기여 성립
- CAR-style과 동등하면 "분해만으로 충분"이므로 method 기여를 내리고 benchmark·분석 논문으로 간다
- Qwen에서 oracle gap의 절반 이상을 닫고 Llama에서 정확도 훼손 없이 order flip을 줄이면 통과

---


---

## 2. 외부 전이 (시간이 남을 때)

- held-out policy pair: 방법 설계·prompt 예시에서 한 조합(예: VERIFY_PREFER+CONDITION)을 제외하고 그 조합에서 평가
- TANGLE artifact가 공개되면 irreducible conflict(clarify/defer) unit을 하나 섞은 `K=2` 30건
- Memora quarterly 질문 중 update·delete가 둘 이상 필요한 문항을 `K>1,H=1` 자연 통제군으로 20건

---


---

## 3. 산출물 위치

```text
data/pilot3_cmcr/             held-out combination split, 외부 전이 instance
results/pilot3_cmcr/
├── run_manifest.yaml
├── method/                   CMCR-Linear 3 변형
├── baselines/                Direct, CoT, global-policy, CAR-style, CAAP-style
└── transfer/
src/composite_conflict/
├── cmcr_linear.py
├── run_pilot3_baselines.py
└── finalize_pilot3.py
```

---

## 4. 체크리스트

- [ ] 진입 조건 4개 확인, 날짜 기록
- [ ] CMCR-Linear 구현 (합침/분리/recheck 3 변형)
- [ ] CAR-style, CAAP-style baseline 구현
- [ ] 전 조건 실행, cost frontier
- [ ] K3_H≥2 subset 분석
- [ ] held-out policy pair
- [ ] TANGLE/Memora 전이 (artifact 확보 시)
