### mistral_small_3_2_24b_gen__qwen3_8b_judge__v3_evidence

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.713 | 0.477 | +0.236 | 0.629 | 0 | 0.1841–0.2908 |
| K2 | 120 | 0.717 | 0.533 | +0.183 | 0.721 | 1e-05 | – |
| K3 | 270 | 0.711 | 0.452 | +0.259 | 0.589 | 0 | – |
| homogeneous | 150 | 0.733 | 0.627 | +0.107 | 0.809 | 0.0025 | – |
| heterogeneous | 240 | 0.700 | 0.383 | +0.317 | 0.512 | 0 | – |
| K2_H1 | 60 | 0.750 | 0.633 | +0.117 | 0.844 | 0.016 | 0.0333–0.2167 |
| K2_H2 | 60 | 0.683 | 0.433 | +0.250 | 0.585 | 0.00073 | 0.1167–0.3833 |
| K3_H1 | 90 | 0.722 | 0.622 | +0.100 | 0.785 | 0.064 | -0.0111–0.2111 |
| K3_H2 | 90 | 0.700 | 0.500 | +0.200 | 0.651 | 0.00053 | 0.0889–0.3111 |
| K3_H3 | 90 | 0.711 | 0.233 | +0.478 | 0.328 | 0 | 0.4–0.5556 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.433 | 0.353 | 0.567 | +0.080 | 47/65 |
| K2_H1 | 30 | 0.700 | 0.600 | 0.733 | +0.100 | 18/21 |
| K2_H2 | 30 | 0.367 | 0.267 | 0.600 | +0.100 | 6/11 |
| K3_H1 | 30 | 0.567 | 0.567 | 0.633 | +0.000 | 15/17 |
| K3_H2 | 30 | 0.333 | 0.267 | 0.533 | +0.067 | 6/10 |
| K3_H3 | 30 | 0.200 | 0.067 | 0.333 | +0.133 | 2/6 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.915 | 0.785 | +0.131 | 0.807 | 0.0023 |
| CONDITION | homogeneous | 50 | 0.940 | 0.940 | +0.000 | 0.936 | 1 |
| CONDITION | heterogeneous | 80 | 0.900 | 0.688 | +0.212 | 0.722 | 0.00049 |
| SUPERSEDE | ALL | 130 | 1.000 | 0.561 | +0.439 | 0.561 | 0 |
| SUPERSEDE | homogeneous | 50 | 1.000 | 0.900 | +0.100 | 0.900 | 0.062 |
| SUPERSEDE | heterogeneous | 80 | 1.000 | 0.350 | +0.650 | 0.350 | 0 |
| VERIFY_PREFER | ALL | 130 | 0.223 | 0.085 | +0.139 | 0.207 | 0.00091 |
| VERIFY_PREFER | homogeneous | 50 | 0.260 | 0.040 | +0.220 | 0.000 | 0.0074 |
| VERIFY_PREFER | heterogeneous | 80 | 0.200 | 0.113 | +0.087 | 0.375 | 0.092 |
