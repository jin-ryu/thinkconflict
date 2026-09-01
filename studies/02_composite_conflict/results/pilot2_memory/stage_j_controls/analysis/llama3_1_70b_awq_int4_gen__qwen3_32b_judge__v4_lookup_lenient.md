### llama3_1_70b_awq_int4_gen__qwen3_32b_judge__v4_lookup_lenient

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 150 | 0.693 | 0.640 | +0.053 | 0.673 | 0.37 | -0.0685–0.1711 |
| K2 | 60 | 0.717 | 0.583 | +0.133 | 0.628 | 0.15 | – |
| K3 | 90 | 0.678 | 0.678 | +0.000 | 0.705 | 1 | – |
| no_conflict | 150 | 0.693 | 0.640 | +0.053 | 0.673 | 0.37 | – |
| K2_C0 | 60 | 0.717 | 0.583 | +0.133 | 0.628 | 0.15 | -0.0333–0.3167 |
| K3_C0 | 90 | 0.678 | 0.678 | +0.000 | 0.705 | 1 | -0.1444–0.1667 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0.433 | 0.400 | 0.817 | +0.033 | 11/26 |
| K2_C0 | 30 | 0.500 | 0.367 | 0.833 | +0.133 | 6/15 |
| K3_C0 | 30 | 0.367 | 0.433 | 0.800 | -0.067 | 5/11 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| LOOKUP | ALL | 150 | 0.693 | 0.640 | +0.053 | 0.673 | 0.37 |
| LOOKUP | no_conflict | 150 | 0.693 | 0.640 | +0.053 | 0.673 | 0.37 |
