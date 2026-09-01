### llama3_1_70b_awq_int4_gen__qwen3_32b_judge__v4_unit_isolated

| subset | pairs | anchor atomic | anchor in SAME (worst) | anchor in DIFF (worst) | same ok/diff fail | diff ok/same fail | p | SAME (best) | DIFF (best) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.82 | 0.62 | 0.72 | 2 | 8 | 0.109 | 0.93 | 0.85 | 0.125 |
| SUPERSEDE | 20 | 0.95 | 0.85 | 0.90 | 2 | 3 | 1 | 1.00 | 0.95 | 1 |
| VERIFY_PREFER | 20 | 0.50 | 0.00 | 0.25 | 0 | 5 | 0.0625 | 0.80 | 0.60 | 0.219 |
| CONDITION | 20 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| anchor_atomic_correct_only | 49 | 1.00 | 0.73 | 0.84 | 1 | 6 | 0.125 | 0.96 | 0.96 | 1 |
| by:CONDITION->SUPERSEDE | 8 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:CONDITION->VERIFY_PREFER | 12 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->CONDITION | 5 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->VERIFY_PREFER | 15 | 0.93 | 0.80 | 0.87 | 2 | 3 | 1 | 1.00 | 0.93 | 1 |
| by:VERIFY_PREFER->CONDITION | 9 | 0.44 | 0.00 | 0.33 | 0 | 3 | 0.25 | 0.89 | 0.67 | 0.5 |
| by:VERIFY_PREFER->SUPERSEDE | 11 | 0.55 | 0.00 | 0.18 | 0 | 2 | 0.5 | 0.73 | 0.55 | 0.625 |

Per order (ALL): original: same 0.80 / diff 0.78 (p=1), reverse: same 0.65 / diff 0.77 (p=0.0391), interleaved: same 0.88 / diff 0.78 (p=0.109)

Partner worst-order accuracy (ALL): same: 0.65, diff: 0.57; partner atomic: same: 0.73, diff: 0.67
