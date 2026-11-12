# Forget or Flag? Handling Superseded Facts in Long-Term Memory for AI Assistants

Code, data and results for the manuscript *Forget or Flag? Handling Superseded Facts in Long-Term
Memory for AI Assistants* (Mayesha Maliha Proma, in preparation for ACL 2027), which extends the
undergraduate thesis *Constraint-Aware Memory for Long-Horizon AI Assistants* (Tokyo International
University, 2025; advisors Prof. Parag Kulkarni and Prof. Fatih Ozaydin).

When a user changes their plans ("I'm applying to Canada now, not Germany"), what should an
assistant's long-term memory do with the old fact? It can **keep** it, **delete** it, or **flag** it
as outdated. This repository compares the three on a controlled benchmark and on real chat
histories from LongMemEval, and checks the result in the open-source memory library Mem0.

## Main results

**Deleting outdated facts breaks questions about the past.** On 66 questions that ask for an
earlier value ("What was my personal best *before* the one I hoped to beat?"), at a 300-token
memory budget:

| Reader | Keep (RAG) | Flag as outdated | Delete |
|---|---|---|---|
| Claude Haiku 5.5 | 0.955 | 0.939 | 0.152 |
| Claude Sonnet 5.5 | 0.955 | 0.939 | 0.136 |
| Qwen2.5-7B (open weights) | 0.727 | 0.727 | 0.182 |

Flag vs. delete: 52–0, 53–0 and 37–1 discordant answers (exact McNemar, all p < 1e-9).

**The same failure appears in Mem0.** On the same 66 questions, Mem0 1.x, whose LLM step updates or
deletes memories, scored **0.24**; Mem0 2.x, which keeps everything, scored **0.95** (48–1, p < 1e-12).

**Compact, dated memory beats long context.** On 78 LongMemEval knowledge-update questions,
300 tokens of extracted, dated memory items reached 0.97 accuracy, against 0.85 for the full
~105k-token chat history (about 360× fewer tokens).

**Detecting updates needs an LLM.** On a 200-scenario synthetic benchmark of user updates
(corrections, implicit changes, reversals, deadline shifts, policy updates, chains), an embedding
similarity heuristic found 29% of update links; Claude Haiku 5.5 found 100% at 0.99 precision.

**Negative results we report.** Hard "must-include" rules that help in a narrow domain collapse
on open-domain memory (0.12 vs. 0.85), and the thesis's multi-factor scoring lowered relevant-item
recall compared with similarity alone. The synthetic benchmark is easy for an LLM: many updates are
signalled explicitly.

**Evaluation checks.** A second LLM judge agrees with the first on 98.7% of 858 verdicts
(κ = 0.97); the author graded 60 answers blind, including all judge disagreements
(`human_check.csv`). Hand-checked derived questions are in `history_check.csv`.

Full tables with 95% bootstrap confidence intervals: [`results/tables.md`](results/tables.md).
Figures: [`figures/`](figures/).

## Quick start (synthetic benchmark, no API key)

```bash
pip install -r requirements.txt
python run_benchmark.py        # ~20 s on a laptop; writes data/ and results/
python make_report.py          # writes results/tables.md and figures/
```

All synthetic runs are deterministic (seed 42).

## Experiments that call an LLM

Put an Anthropic API key in the environment (`export ANTHROPIC_API_KEY=...`) or in a `.env` file
(`scripts/set_key.sh` asks for it with hidden input). `.env` is in `.gitignore`. Every call is cached
under `results/`, so re-running with the cached files costs nothing.

```bash
# LLM link detector on the synthetic benchmark
python run_llm_links.py --dry-run --n 100   # cost estimate, no API calls
python run_llm_links.py --n 100

# LongMemEval knowledge-update questions (about $3 on Haiku 5.5)
mkdir -p data/longmemeval && curl -L -o data/longmemeval/longmemeval_s_cleaned.json \
  https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json
python run_longmemeval.py --dry-run
python run_longmemeval.py

# Other readers and question types
python run_longmemeval.py --reader-model claude-sonnet-5-5 --budgets 300 --no-full-history --tag _sonnet
python run_longmemeval.py --reader-model ollama:qwen2.5:7b --budgets 300 --no-full-history --tag _qwen   # needs Ollama
python run_longmemeval.py --types temporal-reasoning multi-session --no-full-history --tag _tm

# The 66 earlier-value questions (13 from LongMemEval + 53 derived and checked by hand)
python make_history_questions.py
python run_longmemeval.py --history --tag _hist

# Mem0 2.x (additive) and Mem0 1.x (LLM update/delete step); needs mem0ai and qdrant-client
python run_mem0.py
python -m venv --system-site-packages .venv-mem0v1 && .venv-mem0v1/bin/pip install mem0ai==1.0.11
.venv-mem0v1/bin/python run_mem0.py --v1
python run_mem0.py --history; .venv-mem0v1/bin/python run_mem0.py --v1 --history

# LoCoMo: download locomo10.json from github.com/snap-research/locomo into data/locomo/
python make_locomo_updates.py && python run_longmemeval.py --data data/locomo_updates.json --tag _locomo

# Link quality and judge agreement
python analyze_links.py
python judge_agreement.py --score human_check.csv

python make_report.py
```

## Layout

| Path | Contents |
|---|---|
| `cam/schema.py` | Memory items, sessions, scenarios, gold-label helpers |
| `cam/memory.py` | Context assembly, all methods and baselines, heuristic link predictor |
| `cam/llm_links.py` | LLM update-link detector (incremental, cached) |
| `cam/longmemeval.py` | LongMemEval adapter: extraction, linking, reader and judge prompts |
| `cam/generator.py` | Synthetic scenario generator (2 domains, 6 update kinds, distractors) |
| `cam/metrics.py` | Metrics and bootstrap confidence intervals |
| `data/` | Generated benchmark, derived earlier-value questions, LoCoMo updates |
| `results/` | Per-answer rows, summaries, McNemar tests, run logs, `tables.md` |
| `figures/` | Plots used in the paper |
| `paper/` | LaTeX source and PDF of the manuscript |

## Methods compared

`no_memory`, `full_history` (ignores the budget), `sliding_window`, `summary_truncated`,
`similarity_rag` (keep), `rag+annotate_llm` (flag), `rag+cr_llm` (delete), versions with and
without dates, the full thesis method, and ablations.

## Note on the code

The original thesis code was not preserved. This repository re-implements the thesis method from
the thesis text and adds the LongMemEval, Mem0 and LoCoMo experiments reported in the manuscript.
One model family (Claude) fills most roles; the Qwen2.5-7B reader is the exception.

## Data credits

LongMemEval (Wu et al., 2025), LoCoMo (Maharana et al., 2024) and Mem0 belong to their authors and
are used under their licenses. The large source files are not included; the commands above download them.

## Citation

```bibtex
@unpublished{proma2026forget,
  author = {Proma, Mayesha Maliha},
  title  = {Forget or Flag? Handling Superseded Facts in Long-Term Memory for AI Assistants},
  note   = {Manuscript in preparation},
  year   = {2026}
}
```
