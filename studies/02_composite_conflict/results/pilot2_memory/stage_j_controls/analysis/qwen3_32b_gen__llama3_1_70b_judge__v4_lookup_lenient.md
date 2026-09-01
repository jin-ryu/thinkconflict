### qwen3_32b_gen__llama3_1_70b_judge__v4_lookup_lenient

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.987 | 0.820 | +0.167 | 0.824 | 0 | 0.1027–0.2318 |
| K2 | 60 | 0.983 | 0.817 | +0.167 | 0.814 | 0.0063 | – |
| K3 | 90 | 0.989 | 0.822 | +0.167 | 0.832 | 6.1e-05 | – |
| no_conflict | 150 | 0.987 | 0.820 | +0.167 | 0.824 | 0 | – |
| K2_C0 | 60 | 0.983 | 0.817 | +0.167 | 0.814 | 0.0063 | 0.0667–0.2833 |
| K3_C0 | 90 | 0.989 | 0.822 | +0.167 | 0.832 | 6.1e-05 | 0.0889–0.2444 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.967 | 0.617 | 0.950 | +0.350 | 36/58 |
| K2_C0 | 30 | 0.967 | 0.667 | 1.000 | +0.300 | 19/29 |
| K3_C0 | 30 | 0.967 | 0.567 | 0.900 | +0.400 | 17/29 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.987 | 0.820 | +0.167 | 0.824 | 0 |
| LOOKUP | no_conflict | 150 | 0.987 | 0.820 | +0.167 | 0.824 | 0 |
