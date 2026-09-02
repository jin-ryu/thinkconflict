# ProofWriter feasibility audit for Pilot A

작성일: 2026-09-01  
상태: 모델 미사용 / 공식 아카이브 구조 검사 완료

## 결론

**PASS.** ProofWriter OWA에는 Pilot A의 1--4 hop proof-valid 통제 사례를 만들기에 충분한 gold proof 후보가 있다.

ProofWriter는 원래 conflict 데이터셋이 아니다. 본 판정은 검증된 proof의 결론과 반대 claim을 별도 문서로 추가해 multi-hop inter-context conflict를 구성할 수 있는지를 확인한 것이다.

## 공식 원본과 공개 제한

- release: `V2020.12.3`
- archive SHA-256: `bbc5694901e8306d0bd659aa1ad53ccfd02c201864f4b320ffa3777827d1fc26`
- archive size: `214185889` bytes
- audited subset: `OWA/depth-5`, dev와 test
- license: UNVERIFIED: official archive has no license file and its README does not state a license; do not redistribute original rows pending confirmation.

따라서 연구 내부 변환과 평가는 진행하되, 원본 JSONL이나 원문을 저장소에 재배포하지 않는다. 공개 artifact는 source ID, 변환 코드, 비원문 통계와 라이선스 확인 뒤 허용되는 파생물로 제한한다.

## Schema 검사

| split | theory 수 |
|---|---:|
| dev | 482 |
| test | 948 |

Schema 오류: **0건**

필요 필드인 facts, rules, query polarity, `QDep`, proof와 intermediate conclusion을 모두 확인했다. CWA의 negation-as-failure를 피하기 위해 OWA만 사용한다.

## 깨끗한 선형 proof 후보

아래 수치는 적어도 한 proof가 `QDep`와 같은 수의 명시적 rule application을 가지며, 반대 polarity target이 이미 주어졌거나 별도로 증명되지 않는 사례다.

| hop | dev + | dev - | test + | test - | split별 최소 총수 | 필요 수 |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 466 | 16 | 919 | 29 | 482 | 20 |
| 2 | 469 | 7 | 906 | 23 | 476 | 20 |
| 3 | 393 | 6 | 802 | 15 | 399 | 20 |
| 4 | 327 | 6 | 629 | 12 | 333 | 20 |

## 파일럿 선택 결정

- 이 표의 `OWA/depth-5`는 1--4 hop proof 공급량과 schema 안정성을 확인하는 보조 검사다.
- C0--C2의 실제 dry run은 crowdsourced paraphrase mapping이 있는 `OWA/NatLang`에서 고른다.
- conflict core는 QDep 2ㆍ3ㆍ4에서 각 20개, single-hop calibration은 QDep 1에서 가져온다.
- 같은 theory에서는 질문 하나만 채택한다.
- 실제 문서 분할 뒤 어느 한 문서만으로 target이 증명되지 않는지 다시 검사한다.
- symbolic replay와 paired no-conflict consistency는 별도 dry-run validator로 확인한다.

## 아직 검증되지 않은 것

- 여러 source document로 나눈 뒤의 proof 보존성
- conflict/control의 표면 단서 균형
- 합성 문장의 자연 문서 일반화
- 원본ㆍ파생 데이터 재배포 권한

20개 NatLang dry run과 symbolic validator 결과는 `data/pilot_a/`의 별도 보고서에 기록한다.
