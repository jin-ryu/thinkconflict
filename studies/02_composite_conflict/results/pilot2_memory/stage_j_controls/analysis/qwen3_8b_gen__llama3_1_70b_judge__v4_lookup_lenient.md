### qwen3_8b_gen__llama3_1_70b_judge__v4_lookup_lenient

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 | 0.2092–0.3741 |
| K2 | 60 | 0.983 | 0.700 | +0.283 | 0.695 | 7.6e-05 | – |
| K3 | 90 | 0.967 | 0.667 | +0.300 | 0.678 | 0 | – |
| no_conflict | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 | – |
| K2_C0 | 60 | 0.983 | 0.700 | +0.283 | 0.695 | 7.6e-05 | 0.1667–0.4 |
| K3_C0 | 90 | 0.967 | 0.667 | +0.300 | 0.678 | 0 | 0.2–0.4111 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.933 | 0.417 | 0.833 | +0.517 | 24/56 |
| K2_C0 | 30 | 0.967 | 0.467 | 0.867 | +0.500 | 13/29 |
| K3_C0 | 30 | 0.900 | 0.367 | 0.800 | +0.533 | 11/27 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 |
| LOOKUP | no_conflict | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 |
