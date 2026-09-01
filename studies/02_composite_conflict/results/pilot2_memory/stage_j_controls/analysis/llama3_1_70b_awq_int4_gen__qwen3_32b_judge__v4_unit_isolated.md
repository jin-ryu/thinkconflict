### llama3_1_70b_awq_int4_gen__qwen3_32b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.673 | 0.640 | +0.033 | 0.673 | 0.61 | -0.0909–0.1479 |
| K2 | 60 | 0.700 | 0.600 | +0.100 | 0.667 | 0.29 | – |
| K3 | 90 | 0.656 | 0.667 | -0.011 | 0.678 | 1 | – |
| no_conflict | 150 | 0.673 | 0.640 | +0.033 | 0.673 | 0.61 | – |
| K2_C0 | 60 | 0.700 | 0.600 | +0.100 | 0.667 | 0.29 | -0.05–0.2667 |
| K3_C0 | 90 | 0.656 | 0.667 | -0.011 | 0.678 | 1 | -0.1667–0.1556 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.417 | 0.400 | 0.833 | +0.017 | 10/25 |
| K2_C0 | 30 | 0.500 | 0.367 | 0.867 | +0.133 | 6/15 |
| K3_C0 | 30 | 0.333 | 0.433 | 0.800 | -0.100 | 4/10 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.673 | 0.640 | +0.033 | 0.673 | 0.61 |
| LOOKUP | no_conflict | 150 | 0.673 | 0.640 | +0.033 | 0.673 | 0.61 |
