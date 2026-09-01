### mistral_small_3_2_24b_gen__llama3_1_70b_judge__v3_evidence

Unit-level (worst-order composite vs atomic)

| subset | n units | atomic | in-composite | gap | retained given atomic ok | McNemar p | gap CI95 |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL | 390 | 0.787 | 0.420 | +0.367 | 0.482 | 0 | 0.3036–0.4289 |
| K2 | 120 | 0.817 | 0.500 | +0.317 | 0.561 | 0 | – |
| K3 | 270 | 0.774 | 0.385 | +0.389 | 0.445 | 0 | – |
| homogeneous | 150 | 0.827 | 0.433 | +0.393 | 0.492 | 0 | – |
| heterogeneous | 240 | 0.762 | 0.412 | +0.350 | 0.475 | 0 | – |
| K2_H1 | 60 | 0.850 | 0.483 | +0.367 | 0.569 | 0 | 0.2333–0.5 |
| K2_H2 | 60 | 0.783 | 0.517 | +0.267 | 0.553 | 0.0025 | 0.1167–0.4167 |
| K3_H1 | 90 | 0.811 | 0.400 | +0.411 | 0.438 | 0 | 0.2444–0.5667 |
| K3_H2 | 90 | 0.778 | 0.444 | +0.333 | 0.500 | 1e-06 | 0.2–0.4556 |
| K3_H3 | 90 | 0.733 | 0.311 | +0.422 | 0.394 | 0 | 0.3111–0.5333 |

Independence null (base level)

| cell | bases | ceiling: all atomic ok | observed worst-order | observed best-order | shortfall | success given all atomic ok (all orders) |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 150 | 0.520 | 0.233 | 0.573 | +0.287 | 25/78 |
| K2_H1 | 30 | 0.767 | 0.333 | 0.733 | +0.433 | 10/23 |
| K2_H2 | 30 | 0.567 | 0.267 | 0.733 | +0.300 | 4/17 |
| K3_H1 | 30 | 0.633 | 0.300 | 0.567 | +0.333 | 7/19 |
| K3_H2 | 30 | 0.367 | 0.200 | 0.533 | +0.167 | 3/11 |
| K3_H3 | 30 | 0.267 | 0.067 | 0.300 | +0.200 | 1/8 |

By unit policy (worst-order), homogeneous vs heterogeneous partner

| policy | subset | n | atomic | in-composite | gap | retained | p |
|---|---|---:|---:|---:|---:|---:|---:|
| CONDITION | ALL | 130 | 0.931 | 0.692 | +0.238 | 0.711 | 0 |
| CONDITION | homogeneous | 50 | 0.960 | 0.800 | +0.160 | 0.812 | 0.021 |
| CONDITION | heterogeneous | 80 | 0.912 | 0.625 | +0.287 | 0.644 | 1.5e-05 |
| SUPERSEDE | ALL | 130 | 0.992 | 0.354 | +0.638 | 0.357 | 0 |
| SUPERSEDE | homogeneous | 50 | 1.000 | 0.380 | +0.620 | 0.380 | 0 |
| SUPERSEDE | heterogeneous | 80 | 0.988 | 0.338 | +0.650 | 0.342 | 0 |
| VERIFY_PREFER | ALL | 130 | 0.439 | 0.215 | +0.223 | 0.281 | 8.2e-05 |
| VERIFY_PREFER | homogeneous | 50 | 0.520 | 0.120 | +0.400 | 0.115 | 8.8e-05 |
| VERIFY_PREFER | heterogeneous | 80 | 0.388 | 0.275 | +0.113 | 0.419 | 0.12 |
