# Pilot A dataset build report

생성일: 2026-09-01
상태: **provisional_pre_audit — 아직 모델 실행 금지**

## 구성 결과

| 구성 | primary | reserve | no-conflict template |
|---|---:|---:|---:|
| multi-hop | 60 | 30 | 20 |
| single-hop | 16 | 8 | 4 |
| 합계 | 76 | 38 | 24 |

최종 목표 100개는 conflict 76개와 paired no-conflict 24개다. 현재 conflict 표본은 구성됐지만 no-conflict는 template만 생성됐으므로 완성된 gold는 100개가 아니다.

## 자동 검사

- 원본: MAGIC revision `b96dbb2c7960ed14adc98b2feb4e693f9554df12`
- 원본 checksum과 파일별 레코드 수: 통과
- stable ID와 source-record SHA-256: 생성
- primary 내 conflict-count 균형: multi-hop 파일별 15, single-hop 파일별 4
- primary length quartile 분포: `{1: 20, 2: 22, 3: 18, 4: 16}`
- primary relation 종류: 36
- lexical endpoint coverage 경고: 11건
- noncanonical triplet arity 경고: 0건

11개 lexical 경고의 assistant prescreen에서는 별칭ㆍ표기 차이 5개와 proof fact 실제 누락 의심 6개를 구분했다. 이 판정은 `assistant_prescreen.jsonl`에 `gold=false`로 기록했으며 두 사람의 독립 판정을 대체하지 않는다.

Lexical coverage는 endpoint 문자열의 존재만 보는 triage다. 0건이어도 proof에 필요한 관계ㆍ조건이 모두 서술됐다는 뜻이 아니며, 사람의 proof-coverage 판정을 대체하지 않는다.

## 다음 gate

1. `review_annotations.jsonl`의 primary 76개를 두 사람이 확인한다.
2. 제외 사례는 같은 파일의 reserve rank 순서로 교체하고 manifest를 `frozen_post_audit`로 갱신한다.
3. `generated/no_conflict_templates.jsonl`의 24개 control을 작성하고 독립 합의한다.
4. 100개 모두에 gold certificate와 C0--C4를 작성한 뒤에만 모델 입력을 생성한다.
