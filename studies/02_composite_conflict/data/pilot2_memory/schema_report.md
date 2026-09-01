# Pilot 2 MemConflict schema audit

> 자동 집계 결과. 자연성·독립 conflict-unit 여부는 아직 판정하지 않은 pair pool이다.

## Source

- revision: `ec51d5d36e87f7665d1337f3a88cbde95fc2a964`
- file: `Data/Step4_4.jsonl`
- personas: 30
- sessions: 1,579
- questions: 3,750

## Question distribution

| Conflict type | Policy | Questions |
|---|---|---:|
| `conditional_conflict` | `CONDITION` | 444 |
| `dynamic_conflict` | `SUPERSEDE` | 2,946 |
| `static_conflict` | `VERIFY_PREFER` | 360 |

- all three types를 가진 personas: 30/30
- question-bearing sessions: 1,276
- multi-type sessions: 324

## Session type combinations

| Conflict types in one session | Sessions |
|---|---:|
| `dynamic_conflict` | 688 |
| `static_conflict` | 244 |
| `conditional_conflict+dynamic_conflict` | 208 |
| `conditional_conflict+static_conflict` | 112 |
| `conditional_conflict` | 20 |
| `conditional_conflict+dynamic_conflict+static_conflict` | 2 |
| `dynamic_conflict+static_conflict` | 2 |

## Raw same-session pair pool

- total pairs: 5,686
- homogeneous-policy pairs: 4,662
- heterogeneous-policy pairs: 1,024

| Distinct policy set | Pairs |
|---|---:|
| `SUPERSEDE` | 4,528 |
| `CONDITION+SUPERSEDE` | 851 |
| `CONDITION+VERIFY_PREFER` | 155 |
| `CONDITION` | 134 |
| `SUPERSEDE+VERIFY_PREFER` | 18 |

## Interpretation

- 세 conflict type의 atomic question은 모든 persona에 존재한다.
- 서로 다른 type의 question이 같은 session에 함께 있는 사례도 존재한다.
- 그러나 같은 session이라는 사실은 하나의 자연스러운 goal이나 독립 `K=2`를 보장하지 않는다.
- 특히 동일 dynamic event의 ‘변경 여부/변경 내용’ 질문은 두 질문이어도 하나의 conflict unit일 수 있다.
- 따라서 pair pool은 prevalence 결과가 아니라 LLM 초벌과 연구자 검토를 위한 후보 모집단이다.
