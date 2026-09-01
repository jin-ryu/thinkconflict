### qwen3_8b_gen__llama3_1_70b_judge__v3_evidence

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.844 | 0.326 | +0.518 | 0.371 | 0 | 0.4632–0.5751 |
| K2 | 120 | 0.867 | 0.400 | +0.467 | 0.462 | 0 | – |
| K3 | 270 | 0.833 | 0.293 | +0.541 | 0.329 | 0 | – |
| homogeneous | 150 | 0.867 | 0.373 | +0.493 | 0.423 | 0 | – |
| heterogeneous | 240 | 0.829 | 0.296 | +0.533 | 0.337 | 0 | – |
| K2_H1 | 60 | 0.917 | 0.483 | +0.433 | 0.527 | 0 | 0.2833–0.5833 |
| K2_H2 | 60 | 0.817 | 0.317 | +0.500 | 0.388 | 0 | 0.3833–0.6167 |
| K3_H1 | 90 | 0.833 | 0.300 | +0.533 | 0.347 | 0 | 0.3889–0.6667 |
| K3_H2 | 90 | 0.856 | 0.267 | +0.589 | 0.299 | 0 | 0.4889–0.6889 |
| K3_H3 | 90 | 0.811 | 0.311 | +0.500 | 0.343 | 0 | 0.3667–0.6222 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.680 | 0.160 | 0.447 | +0.520 | 22/102 |
| K2_H1 | 30 | 0.867 | 0.400 | 0.667 | +0.467 | 12/26 |
| K2_H2 | 30 | 0.633 | 0.133 | 0.467 | +0.500 | 4/19 |
| K3_H1 | 30 | 0.667 | 0.167 | 0.567 | +0.500 | 4/20 |
| K3_H2 | 30 | 0.633 | 0.033 | 0.400 | +0.600 | 1/19 |
| K3_H3 | 30 | 0.600 | 0.067 | 0.133 | +0.533 | 1/18 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.915 | 0.523 | +0.392 | 0.546 | 0 |
| CONDITION | homogeneous | 50 | 0.940 | 0.600 | +0.340 | 0.617 | 7.6e-05 |
| CONDITION | heterogeneous | 80 | 0.900 | 0.475 | +0.425 | 0.500 | 0 |
| SUPERSEDE | ALL | 130 | 0.977 | 0.408 | +0.569 | 0.409 | 0 |
| SUPERSEDE | homogeneous | 50 | 1.000 | 0.520 | +0.480 | 0.520 | 0 |
| SUPERSEDE | heterogeneous | 80 | 0.963 | 0.338 | +0.625 | 0.338 | 0 |
| VERIFY_PREFER | ALL | 130 | 0.638 | 0.046 | +0.592 | 0.060 | 0 |
| VERIFY_PREFER | homogeneous | 50 | 0.660 | 0.000 | +0.660 | 0.000 | 0 |
| VERIFY_PREFER | heterogeneous | 80 | 0.625 | 0.075 | +0.550 | 0.100 | 0 |
