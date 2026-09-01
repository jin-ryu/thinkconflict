### llama3_1_70b_awq_int4_gen__qwen3_32b_judge__v4_unit_isolated

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.761 | 0.644 | +0.118 | 0.768 | 2e-06 | 0.0651–0.1692 |
| K2 | 120 | 0.742 | 0.658 | +0.083 | 0.809 | 0.064 | – |
| K3 | 270 | 0.770 | 0.637 | +0.133 | 0.750 | 1.4e-05 | – |
| homogeneous | 150 | 0.793 | 0.613 | +0.180 | 0.731 | 7e-06 | – |
| heterogeneous | 240 | 0.742 | 0.662 | +0.079 | 0.792 | 0.014 | – |
| K2_H1 | 60 | 0.767 | 0.617 | +0.150 | 0.739 | 0.035 | 0.05–0.2667 |
| K2_H2 | 60 | 0.717 | 0.700 | +0.017 | 0.884 | 1 | -0.0833–0.1333 |
| K3_H1 | 90 | 0.811 | 0.611 | +0.200 | 0.726 | 0.00012 | 0.0889–0.3111 |
| K3_H2 | 90 | 0.756 | 0.633 | +0.122 | 0.750 | 0.035 | 0.0111–0.2444 |
| K3_H3 | 90 | 0.744 | 0.667 | +0.078 | 0.776 | 0.21 | -0.0444–0.1778 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.500 | 0.387 | 0.740 | +0.113 | 47/75 |
| K2_H1 | 30 | 0.600 | 0.533 | 0.700 | +0.067 | 15/18 |
| K2_H2 | 30 | 0.467 | 0.467 | 0.833 | +0.000 | 11/14 |
| K3_H1 | 30 | 0.733 | 0.467 | 0.800 | +0.267 | 13/22 |
| K3_H2 | 30 | 0.400 | 0.267 | 0.667 | +0.133 | 6/12 |
| K3_H3 | 30 | 0.300 | 0.200 | 0.700 | +0.100 | 2/9 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.939 | 0.900 | +0.038 | 0.910 | 0.33 |
| CONDITION | homogeneous | 50 | 0.960 | 0.940 | +0.020 | 0.958 | 1 |
| CONDITION | heterogeneous | 80 | 0.925 | 0.875 | +0.050 | 0.878 | 0.42 |
| SUPERSEDE | ALL | 130 | 0.969 | 0.869 | +0.100 | 0.881 | 0.0024 |
| SUPERSEDE | homogeneous | 50 | 0.980 | 0.800 | +0.180 | 0.816 | 0.0039 |
| SUPERSEDE | heterogeneous | 80 | 0.963 | 0.912 | +0.050 | 0.922 | 0.29 |
| VERIFY_PREFER | ALL | 130 | 0.377 | 0.162 | +0.215 | 0.122 | 0.00031 |
| VERIFY_PREFER | homogeneous | 50 | 0.440 | 0.100 | +0.340 | 0.045 | 0.00091 |
| VERIFY_PREFER | heterogeneous | 80 | 0.338 | 0.200 | +0.138 | 0.185 | 0.08 |
