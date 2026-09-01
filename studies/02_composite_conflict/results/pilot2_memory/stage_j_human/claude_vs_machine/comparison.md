### Machine (v4 judge) vs Claude (LLM, blind)

| group | n units | agreement | kappa | machine acc | annotator acc | machine ok / annot wrong | machine wrong / annot ok |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | 420 | 0.931 | 0.821 | 0.714 | 0.769 | 3 | 26 |
| cell:A_DIFF | 24 | 0.917 | 0.778 | 0.750 | 0.750 | 1 | 1 |
| cell:A_SAME | 24 | 1.000 | 1.0 | 0.708 | 0.708 | 0 | 0 |
| cell:K2_C0 | 24 | 0.750 | 0.385 | 0.625 | 0.875 | 0 | 6 |
| cell:K2_H1 | 48 | 0.958 | 0.913 | 0.583 | 0.625 | 0 | 2 |
| cell:K2_H2 | 48 | 0.938 | 0.818 | 0.750 | 0.812 | 0 | 3 |
| cell:K3_C0 | 36 | 0.889 | 0.652 | 0.750 | 0.861 | 0 | 4 |
| cell:K3_H1 | 72 | 0.972 | 0.94 | 0.625 | 0.653 | 0 | 2 |
| cell:K3_H2 | 72 | 0.917 | 0.748 | 0.778 | 0.806 | 2 | 4 |
| cell:K3_H3 | 72 | 0.944 | 0.801 | 0.806 | 0.861 | 0 | 4 |
| gen:llama70b_C0 | 30 | 0.900 | 0.737 | 0.700 | 0.800 | 0 | 3 |
| gen:llama70b_G | 78 | 0.936 | 0.835 | 0.705 | 0.769 | 0 | 5 |
| gen:llama70b_anchor | 24 | 0.958 | 0.895 | 0.708 | 0.750 | 0 | 1 |
| gen:mistral24b_G | 78 | 0.949 | 0.861 | 0.731 | 0.782 | 0 | 4 |
| gen:qwen3_32b_C0 | 30 | 0.767 | 0.286 | 0.700 | 0.933 | 0 | 7 |
| gen:qwen3_32b_G | 78 | 0.897 | 0.723 | 0.731 | 0.782 | 2 | 6 |
| gen:qwen3_32b_anchor | 24 | 0.958 | 0.895 | 0.750 | 0.708 | 1 | 0 |
| gen:qwen3_8b_G | 78 | 1.000 | 1.0 | 0.692 | 0.692 | 0 | 0 |
| policy:CONDITION | 118 | 0.975 | 0.844 | 0.898 | 0.924 | 0 | 3 |
| policy:LOOKUP | 60 | 0.833 | 0.528 | 0.700 | 0.867 | 0 | 10 |
| policy:SUPERSEDE | 109 | 0.963 | 0.0 | 0.963 | 1.000 | 0 | 4 |
| policy:VERIFY_PREFER | 133 | 0.910 | 0.808 | 0.353 | 0.398 | 3 | 9 |

Annotator error labels by policy: {"VERIFY_PREFER": {"latest_applied": 69, "abstain": 11}, "LOOKUP": {"wrong_owner": 7, "partial": 1}, "CONDITION": {"wrong_condition": 9}}
