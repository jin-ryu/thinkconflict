### mistral_small_3_2_24b_gen__llama3_1_70b_judge__v4_unit_isolated

| subset | pairs | anchor atomic | anchor in SAME (worst) | anchor in DIFF (worst) | same ok/diff fail | diff ok/same fail | p | SAME (best) | DIFF (best) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.85 | 0.68 | 0.78 | 0 | 6 | 0.0312 | 0.85 | 0.87 | 1 |
| SUPERSEDE | 20 | 0.85 | 0.70 | 0.75 | 0 | 1 | 1 | 0.90 | 0.80 | 0.5 |
| VERIFY_PREFER | 20 | 0.75 | 0.40 | 0.65 | 0 | 5 | 0.0625 | 0.65 | 0.85 | 0.125 |
| CONDITION | 20 | 0.95 | 0.95 | 0.95 | 0 | 0 | 1 | 1.00 | 0.95 | 1 |
| anchor_atomic_correct_only | 51 | 1.00 | 0.76 | 0.88 | 0 | 6 | 0.0312 | 0.92 | 0.92 | 1 |
| by:CONDITION->SUPERSEDE | 8 | 0.88 | 0.88 | 0.88 | 0 | 0 | 1 | 1.00 | 0.88 | 1 |
| by:CONDITION->VERIFY_PREFER | 12 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->CONDITION | 5 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->VERIFY_PREFER | 15 | 0.80 | 0.60 | 0.67 | 0 | 1 | 1 | 0.87 | 0.73 | 0.5 |
| by:VERIFY_PREFER->CONDITION | 9 | 0.78 | 0.44 | 0.67 | 0 | 2 | 0.5 | 0.67 | 0.89 | 0.5 |
| by:VERIFY_PREFER->SUPERSEDE | 11 | 0.73 | 0.36 | 0.64 | 0 | 3 | 0.25 | 0.64 | 0.82 | 0.5 |

Per order (ALL): original: same 0.75 / diff 0.78 (p=0.688), reverse: same 0.78 / diff 0.83 (p=0.508), interleaved: same 0.77 / diff 0.85 (p=0.0625)

Partner worst-order accuracy (ALL): same: 0.55, diff: 0.60; partner atomic: same: 0.75, diff: 0.68
