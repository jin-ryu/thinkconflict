# Pilot A · Data audit protocol

작성일: 2026-09-01

## 1. 목적

MAGIC 원본의 `conflict` label을 그대로 gold certificate로 승격하지 않는다. 각 사례가 Pilot A의 oracle ladder에 적합하려면 아래 다섯 gate를 모두 통과해야 한다.

## 2. 판정 단위

각 conflict path와 그 path에 대응하는 original triplet을 하나의 proof unit으로 판정한다. N-conflict 사례는 conflict 하나라도 실패하면 전체 사례를 primary에서 제외한다.

## 3. Gate

### G1 · Source fact coverage

- 모든 original triplet의 의미가 `context1`에 명시되어야 한다.
- 모든 perturb triplet의 의미가 `context2`에 명시되어야 한다.
- 철자ㆍ대소문자ㆍ명백한 alias는 허용한다.
- 약한 연관 표현을 강한 관계로 승격하지 않는다. 예: `linked to`는 `identical to`의 근거가 아니다.

### G2 · Graph-to-text fidelity

- 원문의 주어ㆍ목적어ㆍ극성ㆍ방향이 triplet과 일치해야 한다.
- `A part of B`와 `B contains A`처럼 안전한 역관계만 허용한다.
- 관계가 생략ㆍ약화ㆍ강화되거나 주체가 바뀌면 실패다.

### G3 · Proof-step soundness

각 인접 edge를 연결하는 추론 규칙이 자연어로 설명 가능해야 한다.

- 허용 예: 명시적 subclass/instance 전이, 동치관계 전이, 명시된 disjointness의 상속.
- 자동 허용하지 않는 예: `connects with`, `located in`, `born in`, `residence`, `described by source`의 임의 전이.
- type이 다른 node를 연결하는 category error가 없어야 한다.
- 필요한 세계지식ㆍ상식 가정은 `assumptions`에 명시하고, 논쟁적이면 제외한다.

### G4 · Terminal incompatibility

Proof의 마지막 두 claim이 동시에 참일 수 없어야 한다. 단순한 차이, 관련성 부족, 서로 다른 언어ㆍ장소ㆍ분류는 모순이 아니다.

### G5 · Dataset hygiene

- primary 안에 동일 entity/path 중복이 없어야 한다.
- context 길이와 relation family 층화가 유지되어야 한다.
- 비정규 triplet arity, 빈 문맥, 잘못된 ID가 없어야 한다.
- no-conflict는 conflict 사례와 길이ㆍentityㆍ관계군을 맞추되 label artifact가 없어야 한다.

## 4. 판정값

| 값 | 의미 | 처리 |
|---|---|---|
| `accept` | G1--G5 모두 통과 | primary 유지 가능 |
| `exclude` | 하나 이상의 명확한 실패 | 같은 파일의 reserve rank 순서로 교체 |
| `ambiguous` | 두 해석이 가능하거나 가정이 필요 | primary 사용 금지; adjudication 대상 |
| `pending` | 아직 검토하지 않음 | 모델 실행 금지 |

## 5. 독립성

- Assistant prescreen과 자동 NLI는 후보 우선순위만 정하며 gold가 아니다.
- Annotator A/B는 서로의 판정을 보지 않고 G1--G4를 각각 기록한다.
- 불일치는 근거 문장과 허용 추론 규칙을 명시해 adjudication한다.
- 최종 manifest는 모든 primary와 control이 합의된 뒤 `frozen_post_audit`로 바꾼다.

## 6. No-conflict 품질 기준

1. Anchor와 동일한 entityㆍrelation family를 유지한다.
2. 문장 수는 anchor의 ±1, whitespace token 수는 ±15%를 목표로 한다.
3. Conflict를 만드는 terminal edge만 양립 가능한 edge로 교체한다.
4. `not`, `however`, `contrary`, `conflict` 같은 표면 단서 분포가 label을 노출하지 않게 한다.
5. Annotator A/B가 `consistent`로 합의하고, 원 conflict proof가 더는 성립하지 않음을 확인한다.
