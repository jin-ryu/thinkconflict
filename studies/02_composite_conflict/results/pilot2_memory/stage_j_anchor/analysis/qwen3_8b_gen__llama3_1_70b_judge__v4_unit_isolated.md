### qwen3_8b_gen__llama3_1_70b_judge__v4_unit_isolated

| subset | pairs | anchor atomic | anchor in SAME (worst) | anchor in DIFF (worst) | same ok/diff fail | diff ok/same fail | p | SAME (best) | DIFF (best) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.95 | 0.53 | 0.57 | 1 | 3 | 0.625 | 0.80 | 0.82 | 1 |
| SUPERSEDE | 20 | 1.00 | 0.75 | 0.70 | 1 | 0 | 1 | 1.00 | 0.85 | 0.25 |
| VERIFY_PREFER | 20 | 0.85 | 0.05 | 0.10 | 0 | 1 | 1 | 0.45 | 0.65 | 0.219 |
| CONDITION | 20 | 1.00 | 0.80 | 0.90 | 0 | 2 | 0.5 | 0.95 | 0.95 | 1 |
| anchor_atomic_correct_only | 57 | 1.00 | 0.56 | 0.60 | 1 | 3 | 0.625 | 0.81 | 0.84 | 0.727 |
| by:CONDITION->SUPERSEDE | 8 | 1.00 | 0.62 | 0.75 | 0 | 1 | 1 | 0.88 | 0.88 | 1 |
| by:CONDITION->VERIFY_PREFER | 12 | 1.00 | 0.92 | 1.00 | 0 | 1 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->CONDITION | 5 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->VERIFY_PREFER | 15 | 1.00 | 0.67 | 0.60 | 1 | 0 | 1 | 1.00 | 0.80 | 0.25 |
| by:VERIFY_PREFER->CONDITION | 9 | 0.89 | 0.00 | 0.11 | 0 | 1 | 1 | 0.56 | 0.56 | 1 |
| by:VERIFY_PREFER->SUPERSEDE | 11 | 0.82 | 0.09 | 0.09 | 0 | 0 | 1 | 0.36 | 0.73 | 0.125 |

Per order (ALL): original: same 0.62 / diff 0.70 (p=0.267), reverse: same 0.63 / diff 0.68 (p=0.549), interleaved: same 0.72 / diff 0.73 (p=1)

Partner worst-order accuracy (ALL): same: 0.50, diff: 0.50; partner atomic: same: 0.88, diff: 0.82
