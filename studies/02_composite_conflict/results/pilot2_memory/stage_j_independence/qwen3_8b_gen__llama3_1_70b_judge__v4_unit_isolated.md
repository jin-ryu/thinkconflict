### qwen3_8b_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.849 | 0.487 | +0.361 | 0.565 | 0 | 0.303–0.4167 |
| K2 | 120 | 0.867 | 0.517 | +0.350 | 0.596 | 0 | – |
| K3 | 270 | 0.841 | 0.474 | +0.367 | 0.551 | 0 | – |
| homogeneous | 150 | 0.867 | 0.460 | +0.407 | 0.531 | 0 | – |
| heterogeneous | 240 | 0.838 | 0.504 | +0.333 | 0.587 | 0 | – |
| K2_H1 | 60 | 0.867 | 0.500 | +0.367 | 0.577 | 0 | 0.2333–0.5167 |
| K2_H2 | 60 | 0.867 | 0.533 | +0.333 | 0.615 | 2e-06 | 0.2167–0.45 |
| K3_H1 | 90 | 0.867 | 0.433 | +0.433 | 0.500 | 0 | 0.3111–0.5556 |
| K3_H2 | 90 | 0.822 | 0.444 | +0.378 | 0.540 | 0 | 0.2667–0.4889 |
| K3_H3 | 90 | 0.833 | 0.544 | +0.289 | 0.613 | 3e-06 | 0.1667–0.4 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.673 | 0.233 | 0.500 | +0.440 | 34/101 |
| K2_H1 | 30 | 0.733 | 0.433 | 0.700 | +0.300 | 13/22 |
| K2_H2 | 30 | 0.733 | 0.233 | 0.600 | +0.500 | 7/22 |
| K3_H1 | 30 | 0.733 | 0.267 | 0.600 | +0.467 | 8/22 |
| K3_H2 | 30 | 0.567 | 0.133 | 0.367 | +0.433 | 4/17 |
| K3_H3 | 30 | 0.600 | 0.100 | 0.233 | +0.500 | 2/18 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.992 | 0.600 | +0.392 | 0.597 | 0 |
| CONDITION | homogeneous | 50 | 1.000 | 0.620 | +0.380 | 0.620 | 4e-06 |
| CONDITION | heterogeneous | 80 | 0.988 | 0.588 | +0.400 | 0.582 | 0 |
| SUPERSEDE | ALL | 130 | 0.962 | 0.800 | +0.162 | 0.824 | 6e-06 |
| SUPERSEDE | homogeneous | 50 | 0.980 | 0.740 | +0.240 | 0.755 | 0.00049 |
| SUPERSEDE | heterogeneous | 80 | 0.950 | 0.838 | +0.113 | 0.868 | 0.012 |
| VERIFY_PREFER | ALL | 130 | 0.592 | 0.061 | +0.531 | 0.091 | 0 |
| VERIFY_PREFER | homogeneous | 50 | 0.620 | 0.020 | +0.600 | 0.032 | 0 |
| VERIFY_PREFER | heterogeneous | 80 | 0.575 | 0.087 | +0.487 | 0.130 | 0 |
