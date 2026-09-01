### qwen3_32b_thinking_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.854 | 0.582 | +0.272 | 0.673 | 0 | 0.2186–0.3258 |
| K2 | 120 | 0.850 | 0.617 | +0.233 | 0.716 | 0 | – |
| K3 | 270 | 0.856 | 0.567 | +0.289 | 0.654 | 0 | – |
| homogeneous | 150 | 0.860 | 0.613 | +0.247 | 0.705 | 0 | – |
| heterogeneous | 240 | 0.850 | 0.562 | +0.287 | 0.652 | 0 | – |
| K2_H1 | 60 | 0.817 | 0.617 | +0.200 | 0.735 | 0.0018 | 0.1–0.3167 |
| K2_H2 | 60 | 0.883 | 0.617 | +0.267 | 0.698 | 3.1e-05 | 0.1667–0.4 |
| K3_H1 | 90 | 0.889 | 0.611 | +0.278 | 0.688 | 0 | 0.1556–0.4222 |
| K3_H2 | 90 | 0.833 | 0.489 | +0.344 | 0.587 | 0 | 0.2444–0.4556 |
| K3_H3 | 90 | 0.844 | 0.600 | +0.244 | 0.684 | 1e-05 | 0.1444–0.3556 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.673 | 0.347 | 0.787 | +0.327 | 52/101 |
| K2_H1 | 30 | 0.700 | 0.567 | 0.800 | +0.133 | 17/21 |
| K2_H2 | 30 | 0.767 | 0.367 | 0.767 | +0.400 | 11/23 |
| K3_H1 | 30 | 0.767 | 0.500 | 0.833 | +0.267 | 15/23 |
| K3_H2 | 30 | 0.567 | 0.200 | 0.767 | +0.367 | 6/17 |
| K3_H3 | 30 | 0.567 | 0.100 | 0.767 | +0.467 | 3/17 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.962 | 0.900 | +0.061 | 0.936 | 0.0078 |
| CONDITION | homogeneous | 50 | 0.980 | 0.940 | +0.040 | 0.959 | 0.5 |
| CONDITION | heterogeneous | 80 | 0.950 | 0.875 | +0.075 | 0.921 | 0.031 |
| SUPERSEDE | ALL | 130 | 0.992 | 0.792 | +0.200 | 0.791 | 0 |
| SUPERSEDE | homogeneous | 50 | 1.000 | 0.880 | +0.120 | 0.880 | 0.031 |
| SUPERSEDE | heterogeneous | 80 | 0.988 | 0.738 | +0.250 | 0.734 | 1.1e-05 |
| VERIFY_PREFER | ALL | 130 | 0.608 | 0.054 | +0.554 | 0.063 | 0 |
| VERIFY_PREFER | homogeneous | 50 | 0.600 | 0.020 | +0.580 | 0.000 | 0 |
| VERIFY_PREFER | heterogeneous | 80 | 0.613 | 0.075 | +0.537 | 0.102 | 0 |
