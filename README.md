# Constraint-Aware Memory for Long-Horizon AI Assistants

Code and benchmark for *Constraint-Aware Memory for Long-Horizon AI Assistants:
Structured Retrieval and Conflict Resolution under Fixed Context Budgets*
(Mayesha Maliha Proma, undergraduate thesis, Tokyo International University, 2025).

The system selects which memory items enter an LLM's context window. It combines:

1. **Typed memory items** (constraint, deadline, decision, progress, preference) with provenance.
2. **Supersedes-based conflict resolution**: items replaced by a newer item are filtered out.
3. **Must-include rules**: active constraints, decisions and deadlines due within 45 days are protected.
4. **Multi-factor scoring** (similarity, recency, salience, decay) and **budget-aware packing**.

The original thesis code was lost; this is a clean re-implementation from the thesis text.

## Quick start

```bash
pip install -r requirements.txt
python run_benchmark.py        # ~20 s on a laptop; writes results/ and data/
python make_report.py          # writes results/tables.md and figures/
```

### LLM link detector (needs an Anthropic API key)

```bash
export ANTHROPIC_API_KEY=...                # your key; never commit it
python run_llm_links.py --dry-run --n 100   # cost estimate, no API calls
python run_llm_links.py --n 100             # Claude Opus 5.5 on all 200 scenarios
python make_report.py
```

Claude reads the memory stored so far plus each session's new items and returns, as structured JSON,
which earlier items each new item replaces. Responses are cached in `results/llm_cache.json`, so
re-runs cost nothing. `--model` and `--effort` select other models and effort levels.

### LongMemEval (real chat histories)

```bash
mkdir -p data/longmemeval && curl -L -o data/longmemeval/longmemeval_s_cleaned.json \
  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json
python run_longmemeval.py --dry-run          # cost estimate
python run_longmemeval.py                    # 78 knowledge-update questions, about $3 on Haiku 5.5
python make_report.py
```

Claude extracts typed, dated memory items from each session, links updates (retrieve-then-verify),
answers each question from the selected memory, and a judge grades the answer. Outputs:
`results/lme_rows.csv` (every answer), `lme_summary.csv`, `lme_mcnemar.csv`, `lme_run.json`.
Calls are cached in `results/lme_*_cache.json`.

More runs used in the paper:

```bash
python run_longmemeval.py --reader-model claude-sonnet-5-5 --budgets 300 --no-full-history --tag _sonnet
python run_longmemeval.py --reader-model ollama:qwen2.5:7b --budgets 300 --no-full-history --tag _qwen   # needs Ollama
python run_longmemeval.py --types temporal-reasoning multi-session --no-full-history --tag _tm

python make_history_questions.py                 # 56 derived "what was it before?" questions
python run_longmemeval.py --history --tag _hist  # the 69 earlier-value questions

python run_mem0.py                               # Mem0 2.x (additive)
python -m venv --system-site-packages .venv-mem0v1 && .venv-mem0v1/bin/pip install mem0ai==1.0.11
.venv-mem0v1/bin/python run_mem0.py --v1         # Mem0 1.x (LLM update/delete step)
python run_mem0.py --history; .venv-mem0v1/bin/python run_mem0.py --v1 --history

# LoCoMo: download locomo10.json from github.com/snap-research/locomo into data/locomo/
python make_locomo_updates.py && python run_longmemeval.py --data data/locomo_updates.json --tag _locomo
```

## Layout

| Path | Contents |
|---|---|
| `cam/schema.py` | Memory items, sessions, scenarios, gold-label helpers |
| `cam/llm_links.py` | Claude-based supersedes-link detector (incremental, cached) |
| `cam/memory.py` | `assemble_context`, all method/baseline configs, heuristic link predictor |
| `cam/generator.py` | Template generator (2 domains, 6 update kinds, distractors) |
| `cam/paper_scenarios.py` | Re-creations of thesis scenarios s01–s03 |
| `cam/longmemeval.py` | LongMemEval adapter: extraction, linking, reader and judge prompts |
| `cam/metrics.py` | CSR, contradiction, stale rate, must-include, deadline/relevant recall, bootstrap CIs |
| `data/` | Generated scenarios as JSON |
| `results/` | Session-level traces (`sessions_*.csv`), summaries, sweeps, `tables.md` |

## Methods compared

`no_memory`, `full_history` (ignores the budget), `sliding_window`, `summary_truncated`
(lossy per-item truncation), `similarity_rag` (vector retrieval), `method_full_gold`
(supersedes links from gold labels, an upper bound), `method_full_heuristic` (links predicted
from embedding similarity, no gold labels), plus ablations without must-include, without conflict
resolution, and with similarity-only scoring.

## Benchmark

200 generated scenarios (100 study-abroad, 100 project-planning), 6 sessions each, ~50 memory
items (~470 tokens) per scenario including 30 distractors, 3 update events per scenario drawn from
`correction`, `implicit`, `reversal`, `deadline_shift`, `policy_update`, `chain`. Budgets:
150 / 300 / 500 / 1000 tokens. The data is synthetic and template-based.

Embeddings: `sentence-transformers/all-MiniLM-L6-v2`. Tokens: `tiktoken` `cl100k_base`.
All runs are deterministic (seed 42).

See [FINDINGS.md](FINDINGS.md) for a summary of results.
