### qwen3_32b_gen__llama3_1_70b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.756 | 0.551 | +0.205 | 0.719 | 0 | 0.1602–0.2513 |
| K2 | 120 | 0.767 | 0.600 | +0.167 | 0.783 | 2e-06 | – |
| K3 | 270 | 0.752 | 0.530 | +0.222 | 0.690 | 0 | – |
| homogeneous | 150 | 0.773 | 0.527 | +0.247 | 0.681 | 0 | – |
| heterogeneous | 240 | 0.746 | 0.567 | +0.179 | 0.743 | 0 | – |
| K2_H1 | 60 | 0.783 | 0.567 | +0.217 | 0.723 | 0.00024 | 0.1–0.3333 |
| K2_H2 | 60 | 0.750 | 0.633 | +0.117 | 0.844 | 0.016 | 0.05–0.2 |
| K3_H1 | 90 | 0.767 | 0.500 | +0.267 | 0.652 | 0 | 0.1667–0.3778 |
| K3_H2 | 90 | 0.722 | 0.489 | +0.233 | 0.646 | 1.9e-05 | 0.1444–0.3333 |
| K3_H3 | 90 | 0.767 | 0.600 | +0.167 | 0.768 | 0.00028 | 0.0778–0.2556 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.480 | 0.273 | 0.560 | +0.207 | 39/72 |
| K2_H1 | 30 | 0.700 | 0.500 | 0.733 | +0.200 | 15/21 |
| K2_H2 | 30 | 0.500 | 0.300 | 0.633 | +0.200 | 9/15 |
| K3_H1 | 30 | 0.600 | 0.300 | 0.633 | +0.300 | 9/18 |
| K3_H2 | 30 | 0.300 | 0.200 | 0.467 | +0.100 | 5/9 |
| K3_H3 | 30 | 0.300 | 0.067 | 0.333 | +0.233 | 1/9 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.962 | 0.777 | +0.185 | 0.808 | 0 |
| CONDITION | homogeneous | 50 | 0.960 | 0.740 | +0.220 | 0.771 | 0.00098 |
| CONDITION | heterogeneous | 80 | 0.963 | 0.800 | +0.163 | 0.831 | 0.00024 |
| SUPERSEDE | ALL | 130 | 0.992 | 0.823 | +0.169 | 0.830 | 0 |
| SUPERSEDE | homogeneous | 50 | 0.980 | 0.800 | +0.180 | 0.816 | 0.0039 |
| SUPERSEDE | heterogeneous | 80 | 1.000 | 0.838 | +0.163 | 0.838 | 0.00024 |
| VERIFY_PREFER | ALL | 130 | 0.315 | 0.054 | +0.262 | 0.098 | 0 |
| VERIFY_PREFER | homogeneous | 50 | 0.380 | 0.040 | +0.340 | 0.105 | 1.5e-05 |
| VERIFY_PREFER | heterogeneous | 80 | 0.275 | 0.062 | +0.212 | 0.091 | 0.00049 |
