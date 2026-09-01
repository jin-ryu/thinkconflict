### mistral_small_3_2_24b_gen__llama3_1_70b_judge__v4_lookup_lenient

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.973 | 0.600 | +0.373 | 0.610 | 0 | 0.2847–0.4675 |
| K2 | 60 | 0.983 | 0.600 | +0.383 | 0.610 | 0 | – |
| K3 | 90 | 0.967 | 0.600 | +0.367 | 0.609 | 0 | – |
| no_conflict | 150 | 0.973 | 0.600 | +0.373 | 0.610 | 0 | – |
| K2_C0 | 60 | 0.983 | 0.600 | +0.383 | 0.610 | 0 | 0.2667–0.5333 |
| K3_C0 | 90 | 0.967 | 0.600 | +0.367 | 0.609 | 0 | 0.2444–0.4889 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.933 | 0.350 | 0.683 | +0.583 | 20/56 |
| K2_C0 | 30 | 0.967 | 0.400 | 0.767 | +0.567 | 12/29 |
| K3_C0 | 30 | 0.900 | 0.300 | 0.600 | +0.600 | 8/27 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.973 | 0.600 | +0.373 | 0.610 | 0 |
| LOOKUP | no_conflict | 150 | 0.973 | 0.600 | +0.373 | 0.610 | 0 |
