### llama3_1_70b_awq_int4_gen__qwen3_8b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.633 | 0.620 | +0.013 | 0.653 | 0.9 | -0.1141–0.1429 |
| K2 | 60 | 0.650 | 0.583 | +0.067 | 0.667 | 0.52 | – |
| K3 | 90 | 0.622 | 0.644 | -0.022 | 0.643 | 0.88 | – |
| no_conflict | 150 | 0.633 | 0.620 | +0.013 | 0.653 | 0.9 | – |
| K2_C0 | 60 | 0.650 | 0.583 | +0.067 | 0.667 | 0.52 | -0.1–0.2333 |
| K3_C0 | 90 | 0.622 | 0.644 | -0.022 | 0.643 | 0.88 | -0.1889–0.1667 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.350 | 0.417 | 0.850 | -0.067 | 10/21 |
| K2_C0 | 30 | 0.367 | 0.400 | 0.900 | -0.033 | 5/11 |
| K3_C0 | 30 | 0.333 | 0.433 | 0.800 | -0.100 | 5/10 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.633 | 0.620 | +0.013 | 0.653 | 0.9 |
| LOOKUP | no_conflict | 150 | 0.633 | 0.620 | +0.013 | 0.653 | 0.9 |
