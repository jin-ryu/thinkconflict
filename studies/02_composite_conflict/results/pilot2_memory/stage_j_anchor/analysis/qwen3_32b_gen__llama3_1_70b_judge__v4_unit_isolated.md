### qwen3_32b_gen__llama3_1_70b_judge__v4_unit_isolated

| subset | pairs | anchor atomic | anchor in SAME (worst) | anchor in DIFF (worst) | same ok/diff fail | diff ok/same fail | p | SAME (best) | DIFF (best) | p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.82 | 0.58 | 0.72 | 2 | 10 | 0.0386 | 0.83 | 0.90 | 0.344 |
| SUPERSEDE | 20 | 0.95 | 0.85 | 0.85 | 1 | 1 | 1 | 0.95 | 1.00 | 1 |
| VERIFY_PREFER | 20 | 0.50 | 0.10 | 0.35 | 1 | 6 | 0.125 | 0.55 | 0.70 | 0.508 |
| CONDITION | 20 | 1.00 | 0.80 | 0.95 | 0 | 3 | 0.25 | 1.00 | 1.00 | 1 |
| anchor_atomic_correct_only | 49 | 1.00 | 0.69 | 0.84 | 2 | 9 | 0.0654 | 0.90 | 0.96 | 0.375 |
| by:CONDITION->SUPERSEDE | 8 | 1.00 | 0.75 | 0.88 | 0 | 1 | 1 | 1.00 | 1.00 | 1 |
| by:CONDITION->VERIFY_PREFER | 12 | 1.00 | 0.83 | 1.00 | 0 | 2 | 0.5 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->CONDITION | 5 | 1.00 | 1.00 | 1.00 | 0 | 0 | 1 | 1.00 | 1.00 | 1 |
| by:SUPERSEDE->VERIFY_PREFER | 15 | 0.93 | 0.80 | 0.80 | 1 | 1 | 1 | 0.93 | 1.00 | 1 |
| by:VERIFY_PREFER->CONDITION | 9 | 0.44 | 0.00 | 0.44 | 0 | 4 | 0.125 | 0.67 | 0.89 | 0.625 |
| by:VERIFY_PREFER->SUPERSEDE | 11 | 0.55 | 0.18 | 0.27 | 1 | 2 | 1 | 0.45 | 0.55 | 1 |

Per order (ALL): original: same 0.77 / diff 0.77 (p=1), reverse: same 0.68 / diff 0.75 (p=0.344), interleaved: same 0.70 / diff 0.88 (p=0.00739)

Partner worst-order accuracy (ALL): same: 0.57, diff: 0.48; partner atomic: same: 0.90, diff: 0.73
