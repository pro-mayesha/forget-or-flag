"""Run all methods x budgets on the paper scenarios and the generated benchmark.

    python run_benchmark.py                 # full run (200 generated scenarios)
    python run_benchmark.py --n 20          # quick run
"""
from __future__ import annotations

import argparse
import os
from dataclasses import replace

import pandas as pd

from cam.generator import generate_benchmark
from cam.memory import METHODS, Config, Embedder, Tokens, assemble_context, predict_links
from cam.metrics import aggregate, csr_by_kind, link_prf, session_row
from cam.paper_scenarios import paper_scenarios
from cam.schema import save_scenarios

BUDGETS = [150, 300, 500, 1000]
THRESHOLDS = [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]


def run_suite(scenarios, emb, tok, methods=METHODS, budgets=BUDGETS, threshold=None):
    rows = []
    for sc in scenarios:
        links = predict_links(sc.items, emb, **({"threshold": threshold} if threshold else {}))
        for cfg in methods:
            for b in budgets:
                for s in sc.sessions:
                    lk = links if cfg.links == "heuristic" else None
                    sel, used = assemble_context(sc, s, cfg, b, emb, tok, lk)
                    rows.append({"method": cfg.name, "budget": b, **session_row(sc, s, sel, used)})
    return pd.DataFrame(rows)


def link_quality(scenarios, emb, threshold=None):
    pred, gold = set(), set()
    for sc in scenarios:
        pred |= set(predict_links(sc.items, emb, **({"threshold": threshold} if threshold else {})))
        gold |= set(sc.gold_links())
    return link_prf(pred, gold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="scenarios per domain")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    emb, tok = Embedder(), Tokens()
    print(f"embedder: {emb.kind}")
    suites = {"paper": paper_scenarios(), "generated": generate_benchmark(args.n, args.seed)}
    save_scenarios(suites["paper"], "data/paper_scenarios.json")
    save_scenarios(suites["generated"], "data/generated_benchmark.json")

    for name, scs in suites.items():
        print(f"[{name}] {len(scs)} scenarios")
        df = run_suite(scs, emb, tok)
        df.to_csv(f"{args.out}/sessions_{name}.csv", index=False)
        aggregate(df).to_csv(f"{args.out}/summary_{name}.csv", index=False)
        csr_by_kind(df).to_csv(f"{args.out}/csr_by_kind_{name}.csv")
        pd.DataFrame([link_quality(scs, emb)]).to_csv(f"{args.out}/link_quality_{name}.csv", index=False)

    # sensitivity of the heuristic link predictor to its threshold (generated suite, budget 300)
    gen = suites["generated"]
    sweep = []
    for t in THRESHOLDS:
        cfg = Config(f"method_full_heuristic@{t}", links="heuristic")
        agg = aggregate(run_suite(gen, emb, tok, [cfg], [300], threshold=t), n_boot=200).iloc[0]
        sweep.append({"threshold": t, **link_quality(gen, emb, t),
                      "CSR": agg.CSR, "StaleRate": agg.StaleRate, "Contradiction": agg.Contradiction,
                      "RelevantRecall": agg.RelevantRecall, "MustInclude": agg.MustInclude})
    pd.DataFrame(sweep).to_csv(f"{args.out}/threshold_sweep.csv", index=False)

    # sensitivity to the 45-day must-include window (generated suite, budget 300)
    import cam.memory as M
    import cam.schema as S
    win = []
    for d in [14, 30, 45, 60, 90]:
        M.IMMINENT_DAYS = d  # method's window; gold window stays at 45 days
        agg = aggregate(run_suite(gen, emb, tok, [Config("method_full_gold")], [300]), n_boot=200).iloc[0]
        win.append({"window_days": d, "DeadlineRecall": agg.DeadlineRecall,
                    "RelevantRecall": agg.RelevantRecall, "Tokens": agg.Tokens})
    M.IMMINENT_DAYS = S.IMMINENT_DAYS
    pd.DataFrame(win).to_csv(f"{args.out}/window_sweep.csv", index=False)
    print("done")


if __name__ == "__main__":
    main()
