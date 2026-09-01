### mistral_small_3_2_24b_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.808 | 0.608 | +0.200 | 0.724 | 0 | 0.1505–0.25 |
| K2 | 120 | 0.842 | 0.667 | +0.175 | 0.772 | 1.9e-05 | – |
| K3 | 270 | 0.793 | 0.582 | +0.211 | 0.701 | 0 | – |
| homogeneous | 150 | 0.827 | 0.613 | +0.213 | 0.718 | 0 | – |
| heterogeneous | 240 | 0.796 | 0.604 | +0.192 | 0.728 | 0 | – |
| K2_H1 | 60 | 0.833 | 0.600 | +0.233 | 0.720 | 0.00012 | 0.1333–0.35 |
| K2_H2 | 60 | 0.850 | 0.733 | +0.117 | 0.824 | 0.065 | 0.0167–0.2167 |
| K3_H1 | 90 | 0.822 | 0.622 | +0.200 | 0.716 | 0.00028 | 0.0778–0.3222 |
| K3_H2 | 90 | 0.789 | 0.589 | +0.200 | 0.718 | 0.00012 | 0.1–0.3222 |
| K3_H3 | 90 | 0.767 | 0.533 | +0.233 | 0.667 | 1.9e-05 | 0.1444–0.3222 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.553 | 0.367 | 0.673 | +0.187 | 49/83 |
| K2_H1 | 30 | 0.733 | 0.467 | 0.733 | +0.267 | 14/22 |
| K2_H2 | 30 | 0.700 | 0.467 | 0.833 | +0.233 | 12/21 |
| K3_H1 | 30 | 0.600 | 0.467 | 0.767 | +0.133 | 12/18 |
| K3_H2 | 30 | 0.400 | 0.300 | 0.567 | +0.100 | 7/12 |
| K3_H3 | 30 | 0.333 | 0.133 | 0.467 | +0.200 | 4/10 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.954 | 0.785 | +0.169 | 0.806 | 1e-05 |
| CONDITION | homogeneous | 50 | 0.980 | 0.940 | +0.040 | 0.939 | 0.62 |
| CONDITION | heterogeneous | 80 | 0.938 | 0.688 | +0.250 | 0.720 | 1.1e-05 |
| SUPERSEDE | ALL | 130 | 0.946 | 0.808 | +0.139 | 0.854 | 8e-06 |
| SUPERSEDE | homogeneous | 50 | 0.920 | 0.760 | +0.160 | 0.826 | 0.0078 |
| SUPERSEDE | heterogeneous | 80 | 0.963 | 0.838 | +0.125 | 0.870 | 0.002 |
| VERIFY_PREFER | ALL | 130 | 0.523 | 0.231 | +0.292 | 0.338 | 0 |
| VERIFY_PREFER | homogeneous | 50 | 0.580 | 0.140 | +0.440 | 0.172 | 1e-05 |
| VERIFY_PREFER | heterogeneous | 80 | 0.487 | 0.287 | +0.200 | 0.462 | 0.0025 |
