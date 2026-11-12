"""Evaluate memory selection on LongMemEval knowledge-update questions (real chat histories).

    python run_longmemeval.py --dry-run           # extraction cost estimate, no API calls
    python run_longmemeval.py --n 5               # pilot on the first 5 questions
    python run_longmemeval.py                     # all 78 knowledge-update questions (72 + 6 abstention)
    python run_longmemeval.py --history --tag _hist   # derived earlier-value questions (make_history_questions.py)

Data: data/longmemeval/longmemeval_s_cleaned.json from
https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
Every Claude call is cached under results/lme_*_cache.json, so re-runs are free.
"""
from __future__ import annotations

import argparse
import json
import re

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from cam import longmemeval as lme
from cam.env import load_env
from cam.llm_links import SCHEMA as LINK_SCHEMA, LLMLinker
from cam.memory import Config, Embedder, Tokens, assemble_context, predict_links

DATA = "data/longmemeval/longmemeval_s_cleaned.json"
HISTORY_DATA = "data/lme_history_questions.json"
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

# (name, config, link source) for selection over extracted memory items
ITEM_CONDITIONS = [
    ("sliding_window", Config("sliding_window", selector="recency"), None),
    ("similarity_rag", Config("similarity_rag", scoring="similarity", must_include=False,
                              conflict_resolution=False), None),
    ("rag+cr_heuristic", Config("rag_cr", scoring="similarity", must_include=False), "heuristic"),
    ("rag+cr_llm", Config("rag_cr", scoring="similarity", must_include=False), "llm"),
    ("method_full_llm", Config("method_full"), "llm"),
]
PAIRS = [("rag+cr_llm", "similarity_rag"), ("method_full_llm", "rag+cr_llm"),
         ("rag+cr_llm", "rag+cr_heuristic"), ("rag+annotate_llm", "similarity_rag"),
         ("rag+annotate_llm", "rag+cr_llm"), ("rag+annotate_rich_llm", "rag+annotate_llm"),
         ("rag+annotate_rich_llm_nodates", "rag+annotate_llm_nodates"),
         ("rag+annotate_rich_llm_nodates", "similarity_rag_nodates"), ("rag+cr_llm_nodates", "similarity_rag_nodates"),
         ("rag+annotate_llm_nodates", "similarity_rag_nodates"),
         ("rag+annotate_llm_nodates", "rag+cr_llm_nodates")]
# Questions that ask about an earlier value, which deleting superseded items cannot answer.
HISTORY_Q = r"\b(previous|previously|before|initially|originally|first|used to|when I (just )?started)\b"


def cost(usage: dict, model: str) -> float:
    if not model.startswith("claude"):
        return 0.0   # local model
    pi, po = PRICES.get(model, (4.0, 20.0))
    return usage["input_tokens"] / 1e6 * pi + usage["output_tokens"] / 1e6 * po


def boot_ci(v: np.ndarray, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    r = np.random.default_rng(seed)
    m = r.choice(v, (n, len(v))).mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None, help="only the first n questions")
    ap.add_argument("--types", nargs="+", default=["knowledge-update"],
                    help="LongMemEval question types, e.g. temporal-reasoning multi-session")
    ap.add_argument("--model", default="claude-haiku-5-5", help="extractor, linker and reader")
    ap.add_argument("--reader-model", default=None, help="defaults to --model")
    ap.add_argument("--judge-model", default="claude-haiku-5-5")
    ap.add_argument("--tag", default="", help="suffix for output files, e.g. _sonnet")
    ap.add_argument("--budgets", type=int, nargs="+", default=[300, 1000])
    ap.add_argument("--no-full-history", action="store_true", help="skip the ~115k-token baseline")
    ap.add_argument("--data", default=DATA, help="questions in LongMemEval format, e.g. data/locomo_updates.json")
    ap.add_argument("--history", action="store_true",
                    help="derived earlier-value questions, plus the original ones that ask about an earlier value")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    load_env()
    args.reader_model = args.reader_model or args.model
    out = lambda name, ext="csv": f"results/lme{args.tag}_{name}.{ext}"

    qs = lme.load(args.data, tuple(args.types))
    if args.history:
        qs = [x for x in qs if re.search(HISTORY_Q, x["question"], re.I) and not x["question_id"].endswith("_abs")]
        qs += lme.load_history(HISTORY_DATA)
    qs = qs[: args.n]
    print(f"{len(qs)} questions of type {', '.join(args.types)} ({sum(x['question_id'].endswith('_abs') for x in qs)} abstention)")

    # 1. extraction (one call per distinct session)
    sess = {}
    for x in qs:
        for sid, dstr, turns in lme.sessions_in_order(x):
            sess.setdefault((sid, dstr), lme.extract_prompt(dstr, turns))
    if args.dry_run:
        # Per-call costs measured on the knowledge-update run (Haiku 5.5): extraction ~$0.00027 per
        # session, linking ~$0.0095 per question, reading + judging ~$0.004 per question.
        cached = LLMLinker(args.model, "medium", "results/lme_extract_cache.json").cache
        probe = LLMLinker(args.model, "medium")
        new = sum(probe._key(p, lme.EXTRACT_SYSTEM) not in cached for p in sess.values())
        est = new * 0.00027 + len(qs) * (0.0095 + 0.004)
        print(f"{len(sess)} sessions ({new} not yet extracted); estimated ~${est:.2f} on Haiku 5.5 "
              "without the full-history baseline")
        return

    ext = LLMLinker(args.model, "medium", "results/lme_extract_cache.json", workers=16)
    sids = list(sess)
    extracted = dict(zip(sids, ext.run([sess[s] for s in sids], lme.EXTRACT_SYSTEM, lme.EXTRACT_SCHEMA)))
    print("extract:", ext.usage)
    scs = {x["question_id"]: lme.build_scenario(x, extracted) for x in qs}

    # 2. links: LLM (retrieve-then-verify) and the similarity heuristic
    emb, tok = Embedder(), Tokens()
    linker = LLMLinker(args.model, "medium", "results/lme_link_cache.json", workers=16)
    jobs = {qid: lme.link_prompts(sc, emb) for qid, sc in scs.items()}
    flat = [j for qid in scs for j in jobs[qid]]
    res = linker.run([p for p, _, _ in flat], lme.LINK_SYSTEM, LINK_SCHEMA)
    links, i = {}, 0
    for qid in scs:
        n = len(jobs[qid])
        links[qid] = {"llm": lme.parse_links(jobs[qid], res[i:i + n]),
                      "heuristic": predict_links(scs[qid].items, emb)}
        i += n
    print("link:", linker.usage)

    # 3. selection -> reading prompts
    plan = []  # (qid, condition, budget, tokens, prompt, latest_ev, stale_ev)
    for x in qs:
        qid, sc = x["question_id"], scs[x["question_id"]]
        s = sc.sessions[0]
        ans = [r for r in lme.sessions_in_order(x) if r[0] in set(x["answer_session_ids"])]
        latest = ans[-1][0] if ans else None
        older = {r[0] for r in ans[:-1]}
        plan.append((qid, "no_memory", 0, 0, lme.read_prompt_items(x, sc, []), None, None))
        for b in args.budgets:
            for name, cfg, src in ITEM_CONDITIONS:
                ids, used = assemble_context(sc, s, cfg, b, emb, tok, links[qid][src] if src else None)
                srcs = {m.topic for m in sc.items if m.id in set(ids)}
                plan.append((qid, name, b, used, lme.read_prompt_items(x, sc, ids),
                             latest in srcs, bool(srcs & older)))
                if name == "similarity_rag":
                    # same selection, superseded items marked instead of removed
                    outd = {o for n, o in links[qid]["llm"]}
                    plan.append((qid, "rag+annotate_llm", b, used,
                                 lme.read_prompt_items(x, sc, ids, outdated=outd), latest in srcs,
                                 bool(srcs & older)))
                    plan.append((qid, "rag+annotate_llm_nodates", b, used,
                                 lme.read_prompt_items(x, sc, ids, dated=False, outdated=outd),
                                 latest in srcs, bool(srcs & older)))
                    # richer flag: name the newer value that replaced each superseded item
                    byid = {m.id: m for m in sc.items}
                    rep = {}
                    for n, o in sorted(links[qid]["llm"], key=lambda l: byid[l[0]].created):
                        rep[o] = byid[n]   # the latest replacement wins
                    for dated, suf in ((True, ""), (False, "_nodates")):
                        plan.append((qid, "rag+annotate_rich_llm" + suf, b, used,
                                     lme.read_prompt_items(x, sc, ids, dated=dated, replaced_by=rep),
                                     latest in srcs, bool(srcs & older)))
                if name in ("similarity_rag", "rag+cr_llm"):
                    # ablation: the reader cannot order facts by date
                    plan.append((qid, name + "_nodates", b, used,
                                 lme.read_prompt_items(x, sc, ids, dated=False), latest in srcs,
                                 bool(srcs & older)))
        p = lme.read_prompt_raw(x, set(x["answer_session_ids"]))
        plan.append((qid, "oracle_sessions_raw", 0, tok.count(p), p, True, bool(older)))
        if not args.no_full_history:
            p = lme.read_prompt_raw(x)
            plan.append((qid, "full_history_raw", 0, tok.count(p), p, True, bool(older)))

    # 4. read, 5. judge
    if args.reader_model.startswith("ollama:"):   # local open-weight reader, e.g. ollama:qwen2.5:7b
        from cam.local_llm import OllamaReader
        reader = OllamaReader(args.reader_model[len("ollama:"):], "results/lme_read_cache_ollama.json")
    else:
        reader = LLMLinker(args.reader_model, "medium", "results/lme_read_cache.json", workers=16)
    # Full histories are ~150k tokens each: send them two at a time to stay under the
    # per-minute input-token rate limit.
    long_ = [p[4] for p in plan if p[3] > 20000]
    reader.run([p[4] for p in plan if p[3] <= 20000], lme.READ_SYSTEM, lme.READ_SCHEMA)
    reader.workers = 2
    reader.run(long_, lme.READ_SYSTEM, lme.READ_SCHEMA)
    answers = [r.get("answer", "") for r in reader.run([p[4] for p in plan], lme.READ_SYSTEM, lme.READ_SCHEMA)]
    print("read:", reader.usage)
    byq = {x["question_id"]: x for x in qs}
    judge = LLMLinker(args.judge_model, "low", "results/lme_judge_cache.json", workers=16)
    verdicts = judge.run([lme.judge_prompt(byq[p[0]], a) for p, a in zip(plan, answers)],
                         lme.JUDGE_SYSTEM, lme.JUDGE_SCHEMA)
    print("judge:", judge.usage)

    rows = [{"question_id": p[0], "abstention": p[0].endswith("_abs"), "condition": p[1], "budget": p[2],
             "context_tokens": p[3], "latest_evidence_in_ctx": p[5], "older_evidence_in_ctx": p[6],
             "answer": a, "correct": bool(v.get("correct", False))}
            for p, a, v in zip(plan, answers, verdicts)]
    df = pd.DataFrame(rows)
    df["asks_history"] = df.question_id.map({x["question_id"]: "derived_from" in x
                                             or bool(re.search(HISTORY_Q, x["question"], re.I)) for x in qs})
    df.to_csv(out("rows"), index=False)

    # summary with 95% bootstrap CIs over questions
    summ = []
    for (c, b), g in df.groupby(["condition", "budget"], sort=False):
        acc = g.correct.to_numpy(float)
        lo, hi = boot_ci(acc)
        na = g[~g.abstention]
        summ.append({"condition": c, "budget": b, "n": len(g), "accuracy": acc.mean(), "ci_lo": lo, "ci_hi": hi,
                     "acc_answerable": na.correct.mean(), "acc_abstention": g[g.abstention].correct.mean(),
                     "acc_history_q": g[g.asks_history].correct.mean(),
                     "acc_current_q": g[~g.asks_history & ~g.abstention].correct.mean(),
                     "context_tokens": g.context_tokens.mean(),
                     "latest_evidence_in_ctx": na.latest_evidence_in_ctx.astype(float).mean(),
                     "older_evidence_in_ctx": na.older_evidence_in_ctx.astype(float).mean()})
    summ = pd.DataFrame(summ)
    summ.to_csv(out("summary"), index=False)

    # paired exact McNemar tests at each budget
    tests = []
    for b in args.budgets:
        for a_, b_ in PAIRS:
            A = df[(df.condition == a_) & (df.budget == b)].set_index("question_id").correct
            B = df[(df.condition == b_) & (df.budget == b)].set_index("question_id").correct.reindex(A.index)
            w, l = int((A & ~B).sum()), int((~A & B).sum())
            p = binomtest(w, w + l).pvalue if w + l else 1.0
            tests.append({"budget": b, "a": a_, "b": b_, "a_only_correct": w, "b_only_correct": l, "p_mcnemar": p})
    pd.DataFrame(tests).to_csv(out("mcnemar"), index=False)

    nitems = [len(sc.items) for sc in scs.values()]
    stats = {"questions": len(qs), "sessions_extracted": len(sess),
             "items_per_question": float(np.mean(nitems)),
             "llm_links_per_question": float(np.mean([len(l["llm"]) for l in links.values()])),
             "heuristic_links_per_question": float(np.mean([len(l["heuristic"]) for l in links.values()])),
             "usage": {"extract": ext.usage, "link": linker.usage, "read": reader.usage, "judge": judge.usage},
             "usd_this_run": round(sum(cost(u.usage, u.model) for u in (ext, linker, reader, judge)), 2)}
    json.dump({"model": args.model, "reader_model": args.reader_model, "judge_model": args.judge_model, **stats},
              open(out("run", "json"), "w"), indent=1)
    json.dump({qid: l["llm"] for qid, l in links.items()}, open(out("llm_links", "json"), "w"))

    print(json.dumps(stats, indent=1))
    print(summ.round(3).to_string(index=False))
    print(pd.DataFrame(tests).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
