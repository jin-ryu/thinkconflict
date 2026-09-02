# ProofWriter NatLang 20-item dry-run build

작성일: 2026-09-01  
상태: **PASS** / 모델 평가 전 구조 검증

## 구성

| label | 2-hop | 3-hop | 4-hop | 합계 |
|---|---:|---:|---:|---:|
| conflict | 5 | 5 | 5 | 15 |
| no_conflict | 2 | 2 | 1 | 5 |

- source split: {'dev': 9, 'test': 6}
- theory family: {'AttNonegNatLang': 15}
- C0: crowdsourced NatLang fact/rule sentences mixed across D1/D2 + terminal D3
- C1: proof에 필요한 원문 sentence만
- C2/C2T: 원본 mapping의 canonical fact/rule text와 representation
- C3/C4: 공식 proof-with-intermediates와 required item skeleton

## 자동 검사

- instance: 20개
- error: 0개
- PASS: `official_gold_proof_present`
- PASS: `terminal_polarity_valid`
- PASS: `source_sentence_coverage`
- PASS: `paired_control_count`
- PASS: `raw_text_is_human_paraphrased_natlang`

## 해석

공식 NatLang 문장과 canonical fact/rule mapping을 함께 사용하므로 일반 synthetic split보다 C1→C2 semantic compilation 개입을 구성하기에 적합하다. 충돌은 gold proof target의 반대 claim을 D3에 추가해 만들었고, control도 음수 terminal을 유지해 부정어 단서를 맞췄다.

## 모델 실행 전 남은 gate

- Facts and rules are mixed across D1/D2, but the synthetic micro-document style remains to be audited.
- ProofWriter NatLang provable targets are positive, so every terminal statement is negative; conflict and controls keep this cue matched.
- The NatLang source is AttNoneg unary-attribute reasoning only; binary relations require external transfer validation.
- Independent forward-chaining validation is recorded in a separate validation artifact.
- Human semantic-equivalence review of NatLang sentences remains pending.

따라서 현재 20개는 데이터 제작 방식 검증용이며 평가 모델에 입력하지 않는다.
