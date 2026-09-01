### mistral_small_3_2_24b_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.960 | 0.593 | +0.367 | 0.597 | 0 | 0.274–0.4595 |
| K2 | 60 | 0.967 | 0.583 | +0.383 | 0.586 | 2e-06 | – |
| K3 | 90 | 0.956 | 0.600 | +0.356 | 0.605 | 0 | – |
| no_conflict | 150 | 0.960 | 0.593 | +0.367 | 0.597 | 0 | – |
| K2_C0 | 60 | 0.967 | 0.583 | +0.383 | 0.586 | 2e-06 | 0.2667–0.5167 |
| K3_C0 | 90 | 0.956 | 0.600 | +0.356 | 0.605 | 0 | 0.2444–0.4778 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.900 | 0.333 | 0.683 | +0.567 | 19/54 |
| K2_C0 | 30 | 0.933 | 0.367 | 0.733 | +0.567 | 11/28 |
| K3_C0 | 30 | 0.867 | 0.300 | 0.633 | +0.567 | 8/26 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.960 | 0.593 | +0.367 | 0.597 | 0 |
| LOOKUP | no_conflict | 150 | 0.960 | 0.593 | +0.367 | 0.597 | 0 |
