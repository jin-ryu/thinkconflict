### llama3_1_70b_awq_int4_gen__qwen3_8b_judge__v3_evidence

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.772 | 0.533 | +0.238 | 0.654 | 0 | 0.1797–0.2955 |
| K2 | 120 | 0.767 | 0.633 | +0.133 | 0.793 | 0.00085 | – |
| K3 | 270 | 0.774 | 0.489 | +0.285 | 0.593 | 0 | – |
| homogeneous | 150 | 0.820 | 0.607 | +0.213 | 0.732 | 0 | – |
| heterogeneous | 240 | 0.742 | 0.487 | +0.254 | 0.601 | 0 | – |
| K2_H1 | 60 | 0.817 | 0.633 | +0.183 | 0.755 | 0.0034 | 0.0667–0.3167 |
| K2_H2 | 60 | 0.717 | 0.633 | +0.083 | 0.837 | 0.18 | 0.0–0.1833 |
| K3_H1 | 90 | 0.822 | 0.589 | +0.233 | 0.716 | 1e-06 | 0.1333–0.3444 |
| K3_H2 | 90 | 0.778 | 0.456 | +0.322 | 0.557 | 0 | 0.2–0.4556 |
| K3_H3 | 90 | 0.722 | 0.422 | +0.300 | 0.492 | 1.4e-05 | 0.1556–0.4222 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.507 | 0.373 | 0.633 | +0.133 | 50/76 |
| K2_H1 | 30 | 0.767 | 0.600 | 0.700 | +0.167 | 18/23 |
| K2_H2 | 30 | 0.433 | 0.433 | 0.733 | +0.000 | 11/13 |
| K3_H1 | 30 | 0.667 | 0.500 | 0.700 | +0.167 | 15/20 |
| K3_H2 | 30 | 0.467 | 0.167 | 0.600 | +0.300 | 5/14 |
| K3_H3 | 30 | 0.200 | 0.167 | 0.433 | +0.033 | 1/6 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.969 | 0.862 | +0.108 | 0.865 | 0.0026 |
| CONDITION | homogeneous | 50 | 1.000 | 0.880 | +0.120 | 0.880 | 0.031 |
| CONDITION | heterogeneous | 80 | 0.950 | 0.850 | +0.100 | 0.855 | 0.057 |
| SUPERSEDE | ALL | 130 | 1.000 | 0.638 | +0.361 | 0.638 | 0 |
| SUPERSEDE | homogeneous | 50 | 1.000 | 0.880 | +0.120 | 0.880 | 0.031 |
| SUPERSEDE | heterogeneous | 80 | 1.000 | 0.487 | +0.512 | 0.487 | 0 |
| VERIFY_PREFER | ALL | 130 | 0.346 | 0.100 | +0.246 | 0.111 | 3e-06 |
| VERIFY_PREFER | homogeneous | 50 | 0.460 | 0.060 | +0.400 | 0.087 | 1.1e-05 |
| VERIFY_PREFER | heterogeneous | 80 | 0.275 | 0.125 | +0.150 | 0.136 | 0.029 |
