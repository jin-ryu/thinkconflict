### qwen3_8b_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 | 0.2105–0.3758 |
| K2 | 60 | 0.967 | 0.700 | +0.267 | 0.707 | 0.00015 | – |
| K3 | 90 | 0.978 | 0.667 | +0.311 | 0.670 | 0 | – |
| no_conflict | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 | – |
| K2_C0 | 60 | 0.967 | 0.700 | +0.267 | 0.707 | 0.00015 | 0.15–0.3833 |
| K3_C0 | 90 | 0.978 | 0.667 | +0.311 | 0.670 | 0 | 0.2111–0.4333 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.933 | 0.383 | 0.833 | +0.550 | 22/56 |
| K2_C0 | 30 | 0.933 | 0.433 | 0.867 | +0.500 | 12/28 |
| K3_C0 | 30 | 0.933 | 0.333 | 0.800 | +0.600 | 10/28 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 |
| LOOKUP | no_conflict | 150 | 0.973 | 0.680 | +0.293 | 0.685 | 0 |
