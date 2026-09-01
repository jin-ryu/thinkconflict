### qwen3_32b_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.980 | 0.767 | +0.213 | 0.775 | 0 | 0.1429–0.2895 |
| K2 | 60 | 0.983 | 0.733 | +0.250 | 0.729 | 0.00028 | – |
| K3 | 90 | 0.978 | 0.789 | +0.189 | 0.807 | 1.5e-05 | – |
| no_conflict | 150 | 0.980 | 0.767 | +0.213 | 0.775 | 0 | – |
| K2_C0 | 60 | 0.983 | 0.733 | +0.250 | 0.729 | 0.00028 | 0.1333–0.3833 |
| K3_C0 | 90 | 0.978 | 0.789 | +0.189 | 0.807 | 1.5e-05 | 0.1111–0.2778 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.950 | 0.533 | 0.917 | +0.417 | 31/57 |
| K2_C0 | 30 | 0.967 | 0.567 | 1.000 | +0.400 | 16/29 |
| K3_C0 | 30 | 0.933 | 0.500 | 0.833 | +0.433 | 15/28 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.980 | 0.767 | +0.213 | 0.775 | 0 |
| LOOKUP | no_conflict | 150 | 0.980 | 0.767 | +0.213 | 0.775 | 0 |
