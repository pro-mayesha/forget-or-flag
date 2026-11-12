"""Turn results/*.csv into markdown tables (results/tables.md) and figures (figures/*.png)."""
from __future__ import annotations

import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R, F = "results", "figures"
METRICS = ["CSR", "Contradiction", "StaleRate", "MustInclude", "DeadlineRecall", "RelevantRecall", "Tokens"]
MAIN = ["no_memory", "full_history", "sliding_window", "summary_truncated", "similarity_rag",
        "method_full_heuristic", "method_full_gold"]
ABL = ["method_full_gold", "ablate_no_must_include", "ablate_no_conflict_res", "ablate_similarity_scoring"]


def fmt(row, m):
    v = row[m]
    if pd.isna(v):
        return "–"
    if m == "Tokens":
        return f"{v:.0f}"
    return f"{v:.2f} [{row[m + '_lo']:.2f}, {row[m + '_hi']:.2f}]"


def table(df, methods, budget, title):
    d = df[(df.budget == budget) & df.method.isin(methods)].set_index("method").loc[methods]
    lines = [f"### {title} (budget = {budget} tokens)", "",
             "| Method | " + " | ".join(METRICS) + " |", "|---" * (len(METRICS) + 1) + "|"]
    for m, row in d.iterrows():
        lines.append(f"| {m} | " + " | ".join(fmt(row, k) for k in METRICS) + " |")
    return "\n".join(lines) + "\n"


def md(df, index=True):
    """Minimal DataFrame -> markdown (avoids the optional tabulate dependency)."""
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    rows = ["| " + " | ".join(cols) + " |", "|---" * len(cols) + "|"]
    rows += ["| " + " | ".join("–" if pd.isna(v) else str(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join(rows)


def main():
    os.makedirs(F, exist_ok=True)
    gen = pd.read_csv(f"{R}/summary_generated.csv")
    pap = pd.read_csv(f"{R}/summary_paper.csv")
    out = ["# Results\n", "Values are pooled means with 95% bootstrap CIs over scenarios. "
           "full_history ignores the budget (oracle for recall).\n"]
    for b in [150, 300, 500, 1000]:
        out.append(table(gen, MAIN, b, "Generated benchmark: main comparison"))
    out.append(table(gen, ABL, 300, "Generated benchmark: ablations"))
    out.append(table(gen, ABL, 150, "Generated benchmark: ablations"))
    out.append(table(pap, MAIN, 500, "Re-created thesis scenarios s01–s03"))
    kind = pd.read_csv(f"{R}/csr_by_kind_generated.csv")
    k = kind[kind.budget == 300].drop(columns="budget").set_index("method").loc[MAIN[1:]]
    out += ["### CSR by update kind (generated, budget = 300)", "", md(k.round(2)), ""]
    out += ["### Heuristic supersedes-link detection vs gold", "",
            pd.read_csv(f"{R}/link_quality_generated.csv").round(3).pipe(md, index=False), "",
            "### Link-threshold sensitivity (budget = 300)", "",
            pd.read_csv(f"{R}/threshold_sweep.csv").round(3).pipe(md, index=False), "",
            "### Must-include window sensitivity (method_full_gold, budget = 300; gold window 45 days)", "",
            pd.read_csv(f"{R}/window_sweep.csv").round(3).pipe(md, index=False), ""]
    for path in sorted(glob.glob(f"{R}/summary_llm_*.csv")):
        tag = path.split("summary_llm_")[1][:-4]
        run = json.load(open(f"{R}/llm_run_{tag}.json"))
        s = pd.read_csv(path)
        llm_methods = ["similarity_rag", "method_full_heuristic", "method_full_llm", "method_full_gold"]
        out.append(f"## LLM link detector: {tag} ({run['n_scenarios']} scenarios)\n")
        for b in [150, 300]:
            out.append(table(s, llm_methods, b, "Selection metrics on the same subset"))
        out += ["### Link detection quality (precision vs. transitive gold closure; recall by update kind)", "",
                pd.read_csv(f"{R}/llm_link_quality_{tag}.csv").round(3).pipe(md, index=False), ""]
    if os.path.exists(f"{R}/lme_summary.csv"):
        ls = pd.read_csv(f"{R}/lme_summary.csv")
        run = json.load(open(f"{R}/lme_run.json"))
        cols = ["condition", "budget", "accuracy", "ci_lo", "ci_hi", "acc_current_q", "acc_history_q",
                "acc_abstention", "context_tokens"]
        out += [f"## LongMemEval_S knowledge-update ({run['questions']} questions; reader, extractor, linker "
                f"and judge: {run['model']})\n",
                f"{run['items_per_question']:.0f} extracted items per question; "
                f"{run['llm_links_per_question']:.1f} LLM links and {run['heuristic_links_per_question']:.1f} "
                "heuristic links per question. acc_history_q: questions about an earlier value (13 original + 2 abstention = 15); "
                "acc_current_q: questions about the current value (57).", "",
                ls[cols].round(3).pipe(md, index=False), "",
                "### Paired exact McNemar tests", "",
                pd.read_csv(f"{R}/lme_mcnemar.csv").round(4).pipe(md, index=False), ""]
    open(f"{R}/tables.md", "w").write("\n".join(out))

    # Figure: metrics vs budget for key methods
    keys = ["similarity_rag", "sliding_window", "method_full_heuristic", "method_full_gold"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.4))
    for ax, m in zip(axes, ["CSR", "Contradiction", "DeadlineRecall", "RelevantRecall"]):
        for meth in keys:
            d = gen[gen.method == meth].sort_values("budget")
            ax.plot(d.budget, d[m], marker="o", label=meth)
            ax.fill_between(d.budget, d[m + "_lo"], d[m + "_hi"], alpha=0.15)
        ax.set_title(m); ax.set_xlabel("token budget"); ax.set_xscale("log"); ax.minorticks_off()
        ax.set_xticks([150, 300, 500, 1000]); ax.set_xticklabels([150, 300, 500, 1000]); ax.set_ylim(-0.03, 1.03)
    axes[0].legend(fontsize=7)
    fig.tight_layout(); fig.savefig(f"{F}/metrics_vs_budget.png", dpi=200)

    # Figure: threshold sweep
    sw = pd.read_csv(f"{R}/threshold_sweep.csv")
    fig, ax = plt.subplots(figsize=(5, 3.4))
    for m in ["precision", "recall", "CSR", "RelevantRecall"]:
        ax.plot(sw.threshold, sw[m], marker="o", label=m)
    ax.set_xlabel("cosine threshold for predicted supersedes"); ax.set_ylim(0, 1.03); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{F}/threshold_sweep.png", dpi=200)

    # Figure: CSR by kind
    fig, ax = plt.subplots(figsize=(7, 3.4))
    k.loc[["similarity_rag", "sliding_window", "method_full_heuristic", "method_full_gold"]].T.plot.bar(ax=ax)
    ax.set_ylabel("CSR"); ax.set_ylim(0, 1.05); ax.legend(fontsize=7); plt.xticks(rotation=20)
    fig.tight_layout(); fig.savefig(f"{F}/csr_by_kind.png", dpi=200)

    # Figure: link recall by update kind, heuristic vs each LLM run
    for path in sorted(glob.glob(f"{R}/llm_link_quality_*.csv")):
        tag = path.split("llm_link_quality_")[1][:-4]
        q = pd.read_csv(path)
        q = q[q.kind.notna()].pivot(index="kind", columns="detector", values="recall")
        fig, ax = plt.subplots(figsize=(7, 3.4))
        q.plot.bar(ax=ax)
        ax.set_ylabel("link recall"); ax.set_ylim(0, 1.05); ax.legend(fontsize=7); plt.xticks(rotation=20)
        fig.tight_layout(); fig.savefig(f"{F}/link_recall_by_kind_{tag}.png", dpi=200)
    # Figure: LongMemEval accuracy at budget 300, current-value vs history questions
    if os.path.exists(f"{R}/lme_summary.csv"):
        ls = pd.read_csv(f"{R}/lme_summary.csv")
        order = [("full_history_raw", 0), ("oracle_sessions_raw", 0), ("similarity_rag", 300),
                 ("rag+annotate_llm", 300), ("rag+cr_llm", 300), ("rag+cr_heuristic", 300),
                 ("method_full_llm", 300), ("sliding_window", 300)]
        d = pd.concat([ls[(ls.condition == c) & (ls.budget == b)] for c, b in order])
        lab = [c if b == 0 else f"{c} @{b}" for c, b in order]
        x = np.arange(len(d))
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.bar(x - 0.2, d.acc_current_q, 0.4, label="current-value questions (57)")
        ax.bar(x + 0.2, d.acc_history_q, 0.4, label="earlier-value questions (15)")
        ax.set_xticks(x); ax.set_xticklabels(lab, rotation=25, ha="right", fontsize=8)
        ax.set_ylabel("QA accuracy"); ax.set_ylim(0, 1.05); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(f"{F}/longmemeval_accuracy.png", dpi=200)
    print(open(f"{R}/tables.md").read())


if __name__ == "__main__":
    main()
