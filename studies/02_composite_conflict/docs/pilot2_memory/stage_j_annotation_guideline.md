# Stage J 주석 지침 (unit별 정오와 오류 유형)

> 대상: `results/pilot2_memory/stage_j_human/human_sample_blind.jsonl` 168 trial (56 층 × 3)
> 주석자는 `_machine` 필드가 없는 blind 파일만 본다. 기계 판정과의 비교는 주석 후 `annotate_pilot2_stage_j_compare.py`로 수행한다.

## 입력

각 trial: `query`(복합 질문), `memory_records`(dated record 목록), `candidate_final_answer`, `units`(unit별 atomic_question, policy, gold_atomic_answer, evidence_ids).

## unit별 판정 `correct`

candidate_final_answer 중 **해당 unit의 질문에 답하는 부분만** 보고 판정한다. 다른 unit의 오류는 이 unit 판정에 영향을 주지 않는다.

- `true`: unit 질문에 대한 결론이 gold와 같다. 표현 차이, 설명 누락, 답에 적힌 날짜가 target date와 다른 것은 감점하지 않는다. "Yes"를 서술문으로 함의해도 정답.
- `false`: 결론이 다르거나, unit을 다루지 않았거나, 확정을 회피했다.

policy별 기준:
- `SUPERSEDE`: target date에 유효한 최신 상태를 말해야 한다. 이전 상태를 이력으로 함께 언급하는 것은 정답. 이전 상태만 말하면 오답. gold가 "X에서 Y로 바뀜"일 때 Y만 말해도 정답(변화 여부 질문이면 변화가 있었다는 결론이 맞으면 정답).
- `VERIFY_PREFER`: 검증된 값(verified_profile_record)을 답으로 내야 한다. 불일치를 언급하는 것은 선택. 상충 값을 답으로 내거나 "conflicting, cannot determine"으로 끝나면 오답.
- `CONDITION`: 질문한 item에 대응하는 조건(또는 조건에 대응하는 item)을 말해야 한다. 여러 조건을 나열만 하고 해당 조건이 없으면 오답.
- `LOOKUP`(통제군): record에 있는 값을 말해야 한다. gold에 적힌 필드만 요구한다(예: Career_Status는 고용 상태·회사·직함·업종).

## 오류 유형 `label` (correct=false일 때 하나)

| label | 뜻 |
|---|---|
| `stale_kept` | SUPERSEDE unit에서 이전 값을 답으로 냄 |
| `latest_applied` | VERIFY_PREFER unit에서 나중의 상충 값을 답으로 냄 |
| `wrong_owner` | 다른 사람(이웃·친구·가족)의 record 값을 사용자 것으로 답함 |
| `wrong_condition` | CONDITION unit에서 다른 조건/item을 답함 |
| `abstain` | 정보가 있는데 "확정할 수 없다/불일치"로 끝냄 |
| `omission` | unit을 전혀 다루지 않음 |
| `partial` | 결론의 일부만 맞음(예: 두 항목 중 하나 누락) |
| `other` | 위에 없음(비고에 기록) |

correct=true이면 label은 `correct`.

## 기록

`annotation.units[i]`에 `correct`, `label`, `note`를 채운다. 애매한 경우 note에 이유를 남긴다.
