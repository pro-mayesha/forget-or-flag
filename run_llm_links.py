"""Evaluate Claude as the supersedes-link detector, next to gold and heuristic links.

    python run_llm_links.py --dry-run              # cost estimate only, no API calls
    python run_llm_links.py --n 25                 # 25 scenarios per domain (50 total)
    python run_llm_links.py --n 100                # full generated benchmark

Requires ANTHROPIC_API_KEY (or another Anthropic credential) in the environment.
Run run_benchmark.py first so data/generated_benchmark.json exists.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from cam.env import load_env
from cam.llm_links import LLMLinker, estimate_cost
from cam.memory import Config, Embedder, Tokens, assemble_context, predict_links
from cam.metrics import aggregate, csr_by_kind, link_prf, session_row
from cam.schema import load_scenarios

BUDGETS = [150, 300, 500, 1000]
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="scenarios per domain")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    load_env()

    allsc = load_scenarios("data/generated_benchmark.json")
    by_dom: dict[str, list] = {}
    for sc in allsc:
        by_dom.setdefault(sc.domain, []).append(sc)
    scs = [sc for d in by_dom.values() for sc in d[: args.n]]

    p_in, p_out = PRICES.get(args.model, (4.0, 20.0))
    est = estimate_cost(scs, p_in, p_out)
    print(f"{len(scs)} scenarios, {est['calls']} calls, ~{est['input_tokens']:,} in / "
          f"~{est['output_tokens']:,} out tokens, estimated ~${est['usd']} on {args.model} (before caching)")
    if args.dry_run:
        return

    linker = LLMLinker(args.model, args.effort)
    llm = linker.predict(scs)
    print("usage this run:", linker.usage)

    emb, tok = Embedder(), Tokens()
    tag = f"{args.model}_{args.effort}"
    gold = {sc.id: set(sc.gold_links()) for sc in scs}
    heur = {sc.id: predict_links(sc.items, emb) for sc in scs}

    # link-level quality, overall and by update kind
    rows = []
    for name, src in [("heuristic@0.80", heur), (f"llm:{tag}", llm)]:
        pred = {(sid, *l) for sid, ls in src.items() for l in ls}
        g = {(sid, *l) for sid, ls in gold.items() for l in ls}
        rows.append({"detector": name, **link_prf(pred, g)})
    kinds = {(sc.id, m.id, o): m.update_kind for sc in scs for m in sc.items for o in m.supersedes}
    for name, src in [("heuristic@0.80", heur), (f"llm:{tag}", llm)]:
        pred = {(sid, *l) for sid, ls in src.items() for l in ls}
        for k in sorted(set(kinds.values())):
            gk = {x for x, kk in kinds.items() if kk == k}
            rows.append({"detector": name, "kind": k, "recall": len(pred & gk) / len(gk)})
    pd.DataFrame(rows).to_csv(f"results/llm_link_quality_{tag}.csv", index=False)

    # end-to-end selection metrics on the same subset
    methods = [(Config("method_full_gold"), None), (Config("method_full_heuristic"), heur),
               (Config(f"method_full_llm"), llm), (Config("similarity_rag", scoring="similarity",
                                                          must_include=False, conflict_resolution=False), None)]
    out = []
    for sc in scs:
        for cfg, src in methods:
            for b in BUDGETS:
                for s in sc.sessions:
                    sel, used = assemble_context(sc, s, cfg, b, emb, tok, src[sc.id] if src else None)
                    out.append({"method": cfg.name, "budget": b, **session_row(sc, s, sel, used)})
    df = pd.DataFrame(out)
    df.to_csv(f"results/sessions_llm_{tag}.csv", index=False)
    aggregate(df).to_csv(f"results/summary_llm_{tag}.csv", index=False)
    csr_by_kind(df).to_csv(f"results/csr_by_kind_llm_{tag}.csv")
    json.dump({"model": args.model, "effort": args.effort, "n_scenarios": len(scs), **linker.usage},
              open(f"results/llm_run_{tag}.json", "w"), indent=1)

    print(pd.DataFrame(rows).round(3).to_string(index=False))
    s = aggregate(df, n_boot=200)
    print(s[s.budget == 300][["method", "CSR", "Contradiction", "StaleRate", "DeadlineRecall",
                              "RelevantRecall"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
