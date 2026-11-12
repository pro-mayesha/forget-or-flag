# Findings from the rebuilt benchmark and LongMemEval

Full tables with 95% CIs: `results/tables.md`. Figures: `figures/`.

## 1. With correct supersedes links, conflict resolution works (upper bound)
`method_full_gold` reaches CSR 0.98–1.00 and 0 contradictions at every budget. Similarity RAG,
full history and summaries reach CSR ≈ 0 and contradiction rates of 0.87–1.00 once the budget
lets both versions in. This reproduces the thesis result, but it is an **upper bound** because the
links come from gold labels.

## 2. Detecting the links is the real bottleneck (new, important)
Predicting links from embedding similarity (threshold 0.80) gives precision 1.00 / recall 0.29, and
CSR falls to **0.29** (contradiction 0.89) at budget 300. Lowering the threshold trades precision for
recall (0.6: P 0.59, R 0.78, CSR 0.78). Explicit corrections, implicit changes and reversals get
CSR **0.00** with the heuristic: they are worded differently from what they replace.
(Link precision is scored against the transitive closure of gold links: in a chain A -> B -> C,
"C replaces A" counts as correct.)

## 2b. A small LLM detector closes the gap on this benchmark
Claude Haiku 5.5 (effort medium), run incrementally after each session and never shown gold
labels, on all 200 scenarios (1,199 calls, ~2.6M input / 0.18M output tokens, about $0.35):

| Link detector | Precision | Recall | CSR @300 | Contradiction @300 |
|---|---|---|---|---|
| Similarity heuristic (0.80) | 1.00 | 0.29 | 0.29 | 0.89 |
| **Claude Haiku 5.5** | **0.99** | **1.00** | **0.995** | **0.001** |
| Gold links (upper bound) | – | – | 0.996 | 0.000 |

Recall is 1.00 on every update kind (correction, implicit, reversal, deadline shift, policy
update) and 0.995 on chains. A 4-scenario pilot with Opus 5.5 also scored 1.00 / 1.00.

**Error analysis (6 errors in 900 predictions):**
- 1 miss: a policy update where the currency changed (11,200 EUR -> 12,500 CAD).
- 5 "false positives" share one pattern. When the user drops a country, Haiku also marks that
  country's university deadline or visa rule as replaced (e.g. "Canada isn't working out ->
  Application deadline for University of Toronto"). Under our gold labels this is wrong, but it is
  arguably reasonable: these are **dependent facts** that became irrelevant. The gold schema only
  models direct replacement, not cascading invalidation. This is a good discussion point and a
  possible future extension.

**Caveat for the paper:** near-perfect LLM scores suggest the template benchmark is too easy for
an LLM. Many updates are signalled explicitly ("Update:", "Change of plan:"). Next: evaluate on
LongMemEval's knowledge-update questions and on harder, less explicit corrections before claiming
the problem is solved.

## 3. Must-include rules protect deadlines under tight budgets
Removing must-include drops deadline recall from 1.00 to 0.35 (budget 150) and 0.76 (budget 300).
Caveat: the gold "imminent" window is also 45 days, so the window sweep is partly circular.

## 4. The multi-factor score hurts relevance (negative result; revise the thesis claim)
Similarity-only scoring inside the full method gives higher relevant-item recall than the
multi-factor score (0.99 vs 0.92 at 300; 0.93 vs 0.83 at 150), with the same CSR and deadline
recall. Must-include already covers what the salience/recency terms were meant to protect.

## 5. The thesis token-efficiency claim does not hold up
When the budget binds, all methods fill it (≈145 / 274 tokens at 150 / 300). The thesis's ~10%
saving appeared only because the budget never bound.

## 6. Baselines behave sensibly
Sliding window gets decent CSR at tight budgets (it drops old items by accident) but very poor
deadline recall (0.16 at 150), and it fails on every reversal.

## 7. LongMemEval (real chat histories): hard deletion hurts, dated extraction is what helps
78 knowledge-update questions from LongMemEval_S (Wu et al., 2025; 72 answerable + 6 abstention),
~48 sessions and ~105k tokens of history each. Claude Haiku 5.5 extracts typed, dated memory items
from the user's messages (136 per question), links updates with the same incremental detector
(retrieve-then-verify: 10 most similar earlier items per new item), reads, and judges (judge prompt
adapted from LongMemEval). Total cost about $3. Tables: `results/tables.md`; figure:
`figures/longmemeval_accuracy.png`. QA accuracy, 95% bootstrap CIs, exact McNemar tests:

| Condition (budget 300 unless noted) | Accuracy | Current-value Qs (57) | Earlier-value Qs (15) |
|---|---|---|---|
| Full history, raw (~105k tokens) | 0.85 [0.77, 0.92] | 0.85 | 0.80 |
| Oracle evidence sessions, raw (~6k tokens) | 0.94 | 0.95 | 0.87 |
| **Similarity RAG over dated items** | **0.97** [0.94, 1.00] | 0.98 | 0.93 |
| RAG + LLM links, mark superseded as outdated | 0.96 | 0.98 | 0.87 |
| RAG + LLM links, delete superseded (thesis method) | 0.85 [0.77, 0.92] | 0.93 | **0.47** |
| Full method (+ multi-factor score, must-include) | 0.12 | 0.05 | 0.13 |
| Sliding window | 0.19 | 0.15 | 0.13 |

What this shows:
- **Deleting superseded items hurts on real data** (0.85 vs 0.97, 0 wins / 10 losses, p = 0.002).
  6 of the 10 losses are questions about an earlier value ("What was my *previous* personal best?",
  "How often did I play *before*, and now?"), which deletion makes unanswerable. The other 4 are
  extraction or link errors (e.g. "added a 1915-S quarter" linked as replacing "I have 37 coins").
  The synthetic benchmark had no questions about past values, so it could not reveal this.
- **Marking instead of deleting removes the harm** (0.96 vs 0.97, p = 1.0) but does not beat
  plain RAG: a capable reader already resolves conflicts from the dates.
- **Dates matter more than links.** Without dates, RAG falls to 0.87 at budget 300, and deleting
  superseded items does not recover it (0.83, p = 0.58; at budget 1000 it hurts, p = 0.02).
- **Must-include does not transfer.** With 136 open-domain items per question, the protected
  constraint/decision set (many "user is considering ..." items) fills the whole budget and pushes
  out the relevant facts (0.12 vs 0.85 for the same links without it, p < 0.001).
- **Structured, dated memory beats long context:** 300 tokens of extracted items (0.97) beat
  the full ~105k-token history (0.85), about 360x fewer tokens.

Robustness (done): with Claude Sonnet 5.5 as the reader the result replicates and is stronger
(RAG 0.96, flag 0.96, delete 0.80, p = 0.001; history questions 0.40). A second judge (Sonnet 5.5)
agrees with the Haiku judge on 98.7% of 858 verdicts (kappa 0.97). Files: `results/lme_sonnet_*`,
`results/lme_judge_agreement.json`. Pending: your blind grading of `human_check.csv`
(then `python judge_agreement.py --score human_check.csv`).

Caveats: 78 questions (wide CIs); one model family (Claude) for every role;
the extraction prompt was revised once after a 3-question pilot (it missed facts about the user's
friends); the evidence-coverage proxies in `lme_summary.csv` are coarse (source-session level).

## Suggested framing for the paper
The honest story is now stronger than the thesis's original claim, and it is a better paper:

"Validity-aware memory for long-horizon assistants: what helps and what hurts. On a controlled
benchmark, explicit supersedes filtering removes stale context, and a small LLM recovers almost all
update links (heuristics recover under a third). On real chat histories (LongMemEval), however,
*deleting* superseded facts hurts, because users also ask about past values; marking them as outdated
is safe; and the largest gain comes from extracting compact, dated memory items, which beats reading
the full history at 1/360 of the tokens. Hard must-include rules, which help in a narrow
domain, collapse in open-domain memory."

Contributions to claim: (1) the benchmark + metrics; (2) LLM link detection results; (3) the
synthetic-vs-real gap and its cause (questions about past values); (4) negative results on
deletion and must-include, with the "annotate, don't delete" fix.

## Earlier-value questions at scale (66 questions)

LongMemEval asks about an earlier value in only 15 knowledge-update questions (13 answerable after
removing abstention). `make_history_questions.py` derives one more per remaining question: Claude
Sonnet 5.5 reads only the two dated evidence turns and writes a "what was it before?" question; 56 of
59 were usable; the author checked all 56 by hand (`history_check.csv`) and rejected 3, leaving 53
(`cam.longmemeval.load_history` drops rejected ones). 13 original + 53 derived = 66. Same haystacks, memories and links.
`python run_longmemeval.py --history --tag _hist`.

| Reader (budget 300) | RAG | Flag | Delete | RAG, no dates | Flag, no dates | Delete, no dates |
|---|---|---|---|---|---|---|
| Haiku 5.5 | 0.955 | 0.939 | 0.152 | 0.909 | 0.894 | 0.167 |
| Sonnet 5.5 | 0.955 | 0.939 | 0.136 | 0.939 | 0.924 | 0.152 |
| Qwen2.5-7B | 0.727 | 0.727 | 0.182 | 0.652 | 0.697 | 0.212 |

Flag vs delete: 52–0, 53–0, 37–1 (all p < 1e-9). Flag vs RAG: no difference (1–2, 0–1, 1–1).
Budget 1000 (Haiku): RAG 0.939, flag 0.924, delete 0.182.

Mem0 on the same 66 questions: Mem0 2.x (keeps everything) 0.955 / 0.924 at budgets 300 / 1000;
Mem0 1.x (LLM update/delete step) 0.242 / 0.227; 2.x vs 1.x 48–1 and 47–1 (p < 1e-12). Mem0 1.x
logged 7 failed memory actions (hallucinated memory ids) during the rebuild.

LoCoMo has almost no superseded facts: mining both speakers of all 10 conversations
(`make_locomo_updates.py`) gave 22 candidate changes, of which 8 survived a check against the cited
dialogue turns. 16 questions are too few for any comparison (all conditions within 1–2 answers);
reported only as evidence that existing benchmarks rarely test updates.

## Link quality on real histories and richer flags

`python analyze_links.py`: Sonnet 5.5 labels the 214 LLM links on the 78 knowledge-update questions:
69% true replacements, 7% additions, 7% different things, 3% same value, 14% ambiguous. For 90% of
the 72 answerable questions the change is detected (a link from the later to the earlier evidence
session). History questions (Haiku, 300): change detected (60): delete .07, flag .93, keep .95;
missed (6): all 1.00. Deletion fails exactly where detection succeeds.

Rich flag ("[OUTDATED: replaced on DATE by: ...]", condition `rag+annotate_rich_llm`) never differs
significantly from the plain flag. Without dates, rich flag vs keep on the original questions:
Haiku .95 vs .87 (6–0, p = .03), Sonnet .92 vs .90 (3–1), Qwen .91 vs .85 (6–1).

## Judge check by hand

`python judge_agreement.py --score human_check.csv`: 60 blind answers graded by the author, including
all 11 on which the Haiku and Sonnet judges disagree. Haiku judge vs human 88.3% (kappa .73), Sonnet
judge vs human 93.3% (kappa .84). On the 49 answers where the judges agree, the human agrees on all 49;
on the 11 disagreements the human sides with Sonnet in 7 (Haiku is the stricter judge). History-set
judge agreement on 66 questions: 97.8% of 924 verdicts, kappa .96.
