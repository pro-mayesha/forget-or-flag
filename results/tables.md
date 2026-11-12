# Results

Values are pooled means with 95% bootstrap CIs over scenarios. full_history ignores the budget (oracle for recall).

### Generated benchmark: main comparison (budget = 150 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| no_memory | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | – | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0 |
| full_history | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.06, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 466 |
| sliding_window | 0.92 [0.90, 0.93] | 0.07 [0.06, 0.09] | 0.00 [0.00, 0.01] | 0.27 [0.26, 0.28] | 0.16 [0.14, 0.17] | 0.79 [0.77, 0.82] | 145 |
| summary_truncated | 0.66 [0.64, 0.69] | 0.32 [0.29, 0.35] | 0.02 [0.01, 0.02] | 0.42 [0.41, 0.43] | 0.28 [0.27, 0.31] | 0.85 [0.83, 0.87] | 139 |
| similarity_rag | 0.00 [0.00, 0.00] | 0.87 [0.85, 0.89] | 0.12 [0.12, 0.13] | 0.44 [0.43, 0.45] | 0.58 [0.56, 0.61] | 0.95 [0.94, 0.96] | 145 |
| method_full_heuristic | 0.35 [0.32, 0.39] | 0.83 [0.79, 0.86] | 0.11 [0.11, 0.12] | 0.98 [0.97, 0.98] | 1.00 [1.00, 1.00] | 0.82 [0.79, 0.84] | 145 |
| method_full_gold | 0.98 [0.97, 0.99] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.99 [0.99, 1.00] | 1.00 [1.00, 1.00] | 0.83 [0.81, 0.86] | 145 |

### Generated benchmark: main comparison (budget = 300 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| no_memory | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | – | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0 |
| full_history | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.05, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 466 |
| sliding_window | 0.55 [0.53, 0.58] | 0.51 [0.47, 0.55] | 0.02 [0.02, 0.02] | 0.50 [0.49, 0.51] | 0.35 [0.33, 0.38] | 0.88 [0.86, 0.90] | 274 |
| summary_truncated | 0.21 [0.18, 0.23] | 0.94 [0.92, 0.96] | 0.04 [0.04, 0.04] | 0.80 [0.79, 0.81] | 0.73 [0.71, 0.75] | 0.96 [0.95, 0.97] | 243 |
| similarity_rag | 0.00 [0.00, 0.00] | 0.94 [0.92, 0.95] | 0.08 [0.08, 0.09] | 0.78 [0.77, 0.78] | 0.92 [0.90, 0.93] | 0.99 [0.98, 1.00] | 275 |
| method_full_heuristic | 0.29 [0.26, 0.32] | 0.89 [0.86, 0.92] | 0.07 [0.06, 0.07] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.91 [0.90, 0.93] | 274 |
| method_full_gold | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.92 [0.90, 0.94] | 274 |

### Generated benchmark: main comparison (budget = 500 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| no_memory | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | – | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0 |
| full_history | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.06, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 466 |
| sliding_window | 0.19 [0.17, 0.22] | 0.96 [0.94, 0.97] | 0.04 [0.04, 0.04] | 0.82 [0.81, 0.83] | 0.76 [0.74, 0.78] | 0.97 [0.96, 0.98] | 408 |
| summary_truncated | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.05, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 280 |
| similarity_rag | 0.00 [0.00, 0.01] | 1.00 [1.00, 1.00] | 0.06 [0.06, 0.06] | 0.96 [0.96, 0.97] | 1.00 [0.99, 1.00] | 1.00 [1.00, 1.00] | 408 |
| method_full_heuristic | 0.29 [0.25, 0.32] | 0.89 [0.87, 0.92] | 0.04 [0.04, 0.05] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.97 [0.96, 0.98] | 406 |
| method_full_gold | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.98 [0.97, 0.99] | 401 |

### Generated benchmark: main comparison (budget = 1000 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| no_memory | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | – | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0 |
| full_history | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.05, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 466 |
| sliding_window | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.05, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 466 |
| summary_truncated | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.05, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 280 |
| similarity_rag | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.06 [0.05, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 466 |
| method_full_heuristic | 0.29 [0.25, 0.32] | 0.89 [0.87, 0.92] | 0.04 [0.04, 0.04] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 456 |
| method_full_gold | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 436 |

### Generated benchmark: ablations (budget = 300 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| method_full_gold | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.92 [0.90, 0.94] | 274 |
| ablate_no_must_include | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.83 [0.82, 0.84] | 0.76 [0.74, 0.79] | 0.93 [0.91, 0.94] | 274 |
| ablate_no_conflict_res | 0.01 [0.00, 0.01] | 1.00 [1.00, 1.00] | 0.10 [0.10, 0.10] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.91 [0.89, 0.93] | 274 |
| ablate_similarity_scoring | 0.99 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.99 [0.99, 1.00] | 274 |

### Generated benchmark: ablations (budget = 150 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| method_full_gold | 0.98 [0.97, 0.99] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.99 [0.99, 1.00] | 1.00 [1.00, 1.00] | 0.83 [0.81, 0.86] | 145 |
| ablate_no_must_include | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.49 [0.48, 0.50] | 0.35 [0.33, 0.38] | 0.85 [0.83, 0.87] | 145 |
| ablate_no_conflict_res | 0.12 [0.10, 0.15] | 0.96 [0.94, 0.98] | 0.16 [0.15, 0.17] | 0.95 [0.94, 0.96] | 1.00 [1.00, 1.00] | 0.79 [0.76, 0.81] | 145 |
| ablate_similarity_scoring | 0.98 [0.97, 0.99] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.99 [0.99, 1.00] | 1.00 [1.00, 1.00] | 0.93 [0.91, 0.95] | 145 |

### Re-created thesis scenarios s01–s03 (budget = 500 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| no_memory | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | – | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0 |
| full_history | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.02 [0.00, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 233 |
| sliding_window | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.02 [0.00, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 233 |
| summary_truncated | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.02 [0.00, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 138 |
| similarity_rag | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 0.02 [0.00, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 233 |
| method_full_heuristic | 0.50 [0.00, 1.00] | 0.80 [0.00, 1.00] | 0.01 [0.00, 0.06] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 219 |
| method_full_gold | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 229 |

### CSR by update kind (generated, budget = 300)

| method | chain | correction | deadline_shift | implicit | policy_update | reversal |
|---|---|---|---|---|---|---|
| full_history | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| sliding_window | 0.36 | 0.73 | 0.69 | 0.8 | 0.79 | 0.0 |
| summary_truncated | 0.1 | 0.27 | 0.28 | 0.38 | 0.3 | 0.0 |
| similarity_rag | 0.0 | 0.01 | 0.0 | 0.0 | 0.0 | 0.0 |
| method_full_heuristic | 0.64 | 0.0 | 0.45 | 0.0 | 0.46 | 0.0 |
| method_full_gold | 0.99 | 0.99 | 1.0 | 1.0 | 1.0 | 1.0 |

### Heuristic supersedes-link detection vs gold

| precision | recall | f1 | n_pred | n_gold |
|---|---|---|---|---|
| 1.0 | 0.286 | 0.445 | 326 | 804 |

### Link-threshold sensitivity (budget = 300)

| threshold | precision | recall | f1 | n_pred | n_gold | CSR | StaleRate | Contradiction | RelevantRecall | MustInclude |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.6 | 0.589 | 0.781 | 0.672 | 1352 | 804 | 0.78 | 0.019 | 0.399 | 0.903 | 0.902 |
| 0.7 | 0.828 | 0.527 | 0.644 | 673 | 804 | 0.53 | 0.043 | 0.729 | 0.91 | 0.977 |
| 0.75 | 0.861 | 0.429 | 0.573 | 545 | 804 | 0.432 | 0.051 | 0.799 | 0.913 | 0.985 |
| 0.8 | 1.0 | 0.286 | 0.445 | 326 | 804 | 0.287 | 0.066 | 0.893 | 0.915 | 1.0 |
| 0.85 | 1.0 | 0.215 | 0.354 | 230 | 804 | 0.216 | 0.075 | 0.937 | 0.915 | 1.0 |
| 0.9 | 1.0 | 0.092 | 0.169 | 80 | 804 | 0.098 | 0.09 | 0.981 | 0.913 | 1.0 |
| 0.95 | 1.0 | 0.046 | 0.088 | 37 | 804 | 0.052 | 0.095 | 0.995 | 0.912 | 1.0 |

### Must-include window sensitivity (method_full_gold, budget = 300; gold window 45 days)

| window_days | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|
| 14 | 0.801 | 0.922 | 274.058 |
| 30 | 0.908 | 0.921 | 274.058 |
| 45 | 1.0 | 0.92 | 274.048 |
| 60 | 1.0 | 0.919 | 274.062 |
| 90 | 1.0 | 0.917 | 273.977 |

## LLM link detector: claude-haiku-5-5_medium (200 scenarios)

### Selection metrics on the same subset (budget = 150 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| similarity_rag | 0.00 [0.00, 0.00] | 0.87 [0.85, 0.89] | 0.12 [0.12, 0.13] | 0.44 [0.43, 0.45] | 0.58 [0.56, 0.61] | 0.95 [0.94, 0.96] | 145 |
| method_full_heuristic | 0.35 [0.32, 0.39] | 0.83 [0.79, 0.86] | 0.11 [0.11, 0.12] | 0.98 [0.97, 0.98] | 1.00 [1.00, 1.00] | 0.82 [0.79, 0.84] | 145 |
| method_full_llm | 0.98 [0.97, 0.99] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.99 [0.99, 1.00] | 1.00 [0.99, 1.00] | 0.83 [0.81, 0.86] | 145 |
| method_full_gold | 0.98 [0.97, 0.99] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.99 [0.99, 1.00] | 1.00 [1.00, 1.00] | 0.83 [0.81, 0.86] | 145 |

### Selection metrics on the same subset (budget = 300 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| similarity_rag | 0.00 [0.00, 0.00] | 0.94 [0.92, 0.95] | 0.08 [0.08, 0.09] | 0.78 [0.77, 0.78] | 0.92 [0.90, 0.93] | 0.99 [0.98, 1.00] | 275 |
| method_full_heuristic | 0.29 [0.26, 0.32] | 0.89 [0.86, 0.92] | 0.07 [0.06, 0.07] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.91 [0.90, 0.93] | 274 |
| method_full_llm | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [0.99, 1.00] | 0.92 [0.90, 0.94] | 274 |
| method_full_gold | 1.00 [0.99, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.92 [0.90, 0.94] | 274 |

### Link detection quality (precision vs. transitive gold closure; recall by update kind)

| detector | precision | recall | f1 | n_pred | n_gold | kind |
|---|---|---|---|---|---|---|
| heuristic@0.80 | 1.0 | 0.286 | 0.445 | 326.0 | 804.0 | – |
| llm:claude-haiku-5-5_medium | 0.994 | 0.999 | 0.997 | 900.0 | 804.0 | – |
| heuristic@0.80 | – | 0.64 | – | – | – | chain |
| heuristic@0.80 | – | 0.0 | – | – | – | correction |
| heuristic@0.80 | – | 0.438 | – | – | – | deadline_shift |
| heuristic@0.80 | – | 0.0 | – | – | – | implicit |
| heuristic@0.80 | – | 0.463 | – | – | – | policy_update |
| heuristic@0.80 | – | 0.0 | – | – | – | reversal |
| llm:claude-haiku-5-5_medium | – | 0.995 | – | – | – | chain |
| llm:claude-haiku-5-5_medium | – | 1.0 | – | – | – | correction |
| llm:claude-haiku-5-5_medium | – | 1.0 | – | – | – | deadline_shift |
| llm:claude-haiku-5-5_medium | – | 1.0 | – | – | – | implicit |
| llm:claude-haiku-5-5_medium | – | 1.0 | – | – | – | policy_update |
| llm:claude-haiku-5-5_medium | – | 1.0 | – | – | – | reversal |

## LLM link detector: claude-opus-5-5_medium (4 scenarios)

### Selection metrics on the same subset (budget = 150 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| similarity_rag | 0.00 [0.00, 0.00] | 0.94 [0.85, 1.00] | 0.12 [0.09, 0.15] | 0.46 [0.39, 0.51] | 0.51 [0.28, 0.66] | 0.95 [0.86, 1.00] | 146 |
| method_full_heuristic | 0.59 [0.53, 0.64] | 0.72 [0.50, 0.90] | 0.09 [0.04, 0.13] | 0.97 [0.94, 1.00] | 1.00 [1.00, 1.00] | 0.82 [0.71, 0.95] | 146 |
| method_full_llm | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.97 [0.94, 1.00] | 1.00 [1.00, 1.00] | 0.82 [0.71, 0.95] | 146 |
| method_full_gold | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.97 [0.94, 1.00] | 1.00 [1.00, 1.00] | 0.82 [0.71, 0.95] | 146 |

### Selection metrics on the same subset (budget = 300 tokens)

| Method | CSR | Contradiction | StaleRate | MustInclude | DeadlineRecall | RelevantRecall | Tokens |
|---|---|---|---|---|---|---|---|
| similarity_rag | 0.00 [0.00, 0.00] | 0.94 [0.85, 1.00] | 0.09 [0.06, 0.11] | 0.75 [0.70, 0.81] | 0.94 [0.83, 1.00] | 0.95 [0.86, 1.00] | 275 |
| method_full_heuristic | 0.41 [0.36, 0.47] | 0.94 [0.85, 1.00] | 0.06 [0.05, 0.07] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.86 [0.74, 1.00] | 274 |
| method_full_llm | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.91 [0.83, 1.00] | 275 |
| method_full_gold | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.91 [0.83, 1.00] | 275 |

### Link detection quality (precision vs. transitive gold closure; recall by update kind)

| detector | precision | recall | f1 | n_pred | n_gold | kind |
|---|---|---|---|---|---|---|
| heuristic@0.80 | 1.0 | 0.412 | 0.583 | 8.0 | 17.0 | – |
| llm:claude-opus-5-5_medium | 1.0 | 1.0 | 1.0 | 20.0 | 17.0 | – |
| heuristic@0.80 | – | 1.0 | – | – | – | chain |
| heuristic@0.80 | – | 0.0 | – | – | – | correction |
| heuristic@0.80 | – | 0.0 | – | – | – | implicit |
| heuristic@0.80 | – | 0.5 | – | – | – | policy_update |
| heuristic@0.80 | – | 0.0 | – | – | – | reversal |
| llm:claude-opus-5-5_medium | – | 1.0 | – | – | – | chain |
| llm:claude-opus-5-5_medium | – | 1.0 | – | – | – | correction |
| llm:claude-opus-5-5_medium | – | 1.0 | – | – | – | implicit |
| llm:claude-opus-5-5_medium | – | 1.0 | – | – | – | policy_update |
| llm:claude-opus-5-5_medium | – | 1.0 | – | – | – | reversal |

## LongMemEval_S knowledge-update (78 questions; reader, extractor, linker and judge: claude-haiku-5-5)

136 extracted items per question; 2.7 LLM links and 0.7 heuristic links per question. acc_history_q: questions about an earlier value (13 original + 2 abstention = 15); acc_current_q: questions about the current value (57).

| condition | budget | accuracy | ci_lo | ci_hi | acc_current_q | acc_history_q | acc_abstention | context_tokens |
|---|---|---|---|---|---|---|---|---|
| no_memory | 0 | 0.077 | 0.026 | 0.141 | 0.0 | 0.133 | 1.0 | 0.0 |
| sliding_window | 300 | 0.192 | 0.103 | 0.282 | 0.153 | 0.133 | 1.0 | 293.744 |
| similarity_rag | 300 | 0.974 | 0.936 | 1.0 | 0.983 | 0.933 | 0.833 | 293.679 |
| rag+annotate_llm | 300 | 0.962 | 0.91 | 1.0 | 0.983 | 0.867 | 0.833 | 293.679 |
| rag+annotate_llm_nodates | 300 | 0.949 | 0.897 | 0.987 | 0.966 | 0.867 | 0.833 | 293.679 |
| rag+annotate_rich_llm | 300 | 0.974 | 0.936 | 1.0 | 0.983 | 0.933 | 0.833 | 293.679 |
| rag+annotate_rich_llm_nodates | 300 | 0.949 | 0.897 | 0.987 | 0.966 | 0.867 | 0.833 | 293.679 |
| similarity_rag_nodates | 300 | 0.872 | 0.795 | 0.949 | 0.898 | 0.8 | 0.667 | 293.679 |
| rag+cr_heuristic | 300 | 0.962 | 0.923 | 1.0 | 0.983 | 0.867 | 1.0 | 294.064 |
| rag+cr_llm | 300 | 0.846 | 0.769 | 0.923 | 0.932 | 0.467 | 0.833 | 292.782 |
| rag+cr_llm_nodates | 300 | 0.833 | 0.744 | 0.91 | 0.898 | 0.533 | 0.833 | 292.782 |
| method_full_llm | 300 | 0.115 | 0.051 | 0.192 | 0.051 | 0.133 | 1.0 | 292.603 |
| sliding_window | 1000 | 0.423 | 0.321 | 0.538 | 0.458 | 0.133 | 0.833 | 993.808 |
| similarity_rag | 1000 | 0.936 | 0.872 | 0.987 | 0.949 | 0.867 | 0.833 | 993.603 |
| rag+annotate_llm | 1000 | 0.949 | 0.897 | 0.987 | 0.949 | 0.933 | 0.833 | 993.603 |
| rag+annotate_llm_nodates | 1000 | 0.923 | 0.859 | 0.974 | 0.949 | 0.867 | 0.667 | 993.603 |
| rag+annotate_rich_llm | 1000 | 0.962 | 0.923 | 1.0 | 0.983 | 0.933 | 0.667 | 993.603 |
| rag+annotate_rich_llm_nodates | 1000 | 0.949 | 0.897 | 0.987 | 0.966 | 0.867 | 0.833 | 993.603 |
| similarity_rag_nodates | 1000 | 0.936 | 0.872 | 0.987 | 0.932 | 0.933 | 0.833 | 993.603 |
| rag+cr_heuristic | 1000 | 0.923 | 0.859 | 0.974 | 0.966 | 0.733 | 0.833 | 993.577 |
| rag+cr_llm | 1000 | 0.821 | 0.731 | 0.897 | 0.881 | 0.533 | 0.833 | 993.846 |
| rag+cr_llm_nodates | 1000 | 0.821 | 0.731 | 0.898 | 0.881 | 0.533 | 1.0 | 993.846 |
| method_full_llm | 1000 | 0.218 | 0.128 | 0.308 | 0.203 | 0.133 | 0.833 | 994.115 |
| oracle_sessions_raw | 0 | 0.936 | 0.885 | 0.987 | 0.949 | 0.867 | 0.833 | 6101.974 |
| full_history_raw | 0 | 0.846 | 0.769 | 0.923 | 0.847 | 0.8 | 0.833 | 105493.769 |

### Paired exact McNemar tests

| budget | a | b | a_only_correct | b_only_correct | p_mcnemar |
|---|---|---|---|---|---|
| 300 | rag+cr_llm | similarity_rag | 0 | 10 | 0.002 |
| 300 | method_full_llm | rag+cr_llm | 1 | 58 | 0.0 |
| 300 | rag+cr_llm | rag+cr_heuristic | 1 | 10 | 0.0117 |
| 300 | rag+annotate_llm | similarity_rag | 1 | 2 | 1.0 |
| 300 | rag+annotate_llm | rag+cr_llm | 9 | 0 | 0.0039 |
| 300 | rag+annotate_rich_llm | rag+annotate_llm | 1 | 0 | 1.0 |
| 300 | rag+annotate_rich_llm_nodates | rag+annotate_llm_nodates | 1 | 1 | 1.0 |
| 300 | rag+annotate_rich_llm_nodates | similarity_rag_nodates | 6 | 0 | 0.0312 |
| 300 | rag+cr_llm_nodates | similarity_rag_nodates | 5 | 8 | 0.5811 |
| 300 | rag+annotate_llm_nodates | similarity_rag_nodates | 7 | 1 | 0.0703 |
| 300 | rag+annotate_llm_nodates | rag+cr_llm_nodates | 9 | 0 | 0.0039 |
| 1000 | rag+cr_llm | similarity_rag | 1 | 10 | 0.0117 |
| 1000 | method_full_llm | rag+cr_llm | 1 | 48 | 0.0 |
| 1000 | rag+cr_llm | rag+cr_heuristic | 1 | 9 | 0.0215 |
| 1000 | rag+annotate_llm | similarity_rag | 1 | 0 | 1.0 |
| 1000 | rag+annotate_llm | rag+cr_llm | 10 | 0 | 0.002 |
| 1000 | rag+annotate_rich_llm | rag+annotate_llm | 2 | 1 | 1.0 |
| 1000 | rag+annotate_rich_llm_nodates | rag+annotate_llm_nodates | 2 | 0 | 0.5 |
| 1000 | rag+annotate_rich_llm_nodates | similarity_rag_nodates | 2 | 1 | 1.0 |
| 1000 | rag+cr_llm_nodates | similarity_rag_nodates | 2 | 11 | 0.0225 |
| 1000 | rag+annotate_llm_nodates | similarity_rag_nodates | 2 | 3 | 1.0 |
| 1000 | rag+annotate_llm_nodates | rag+cr_llm_nodates | 11 | 3 | 0.0574 |
