"""Check the LongMemEval judge: a second model re-grades the same answers, and a stratified
sample is exported for a human to grade blind.

    python judge_agreement.py                         # Sonnet 5.5 re-grades the Haiku-reader answers
    python judge_agreement.py --score human_check.csv # after filling in the `human_correct` column

Writes results/lme_judge_agreement.json and human_check.csv (+ results/human_check_key.csv,
which holds the model verdicts; don't open it until you have graded the sample).
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from cam import longmemeval as lme
from cam.env import load_env
from cam.llm_links import LLMLinker

ROWS = "results/lme_rows.csv"
KEY = "results/human_check_key.csv"


def kappa(a: pd.Series, b: pd.Series) -> float:
    a, b = a.astype(bool), b.astype(bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge-model", default="claude-sonnet-5-5")
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--score", default=None, help="graded human_check.csv to score")
    args = ap.parse_args()

    if args.score:
        h = pd.read_csv(args.score).merge(pd.read_csv(KEY), on="item")
        h = h[h.human_correct.notna()]
        human = h.human_correct.astype(str).str.strip().str.lower().isin(["1", "yes", "y", "true", "correct"])
        res = {"n": len(h)}
        for col in ["haiku_judge", "second_judge"]:
            res[col] = {"agreement": float((human == h[col]).mean()), "kappa": kappa(human, h[col])}
        print(json.dumps(res, indent=1))
        json.dump(res, open("results/lme_human_agreement.json", "w"), indent=1)
        return

    load_env()
    qs = {x["question_id"]: x for x in lme.load("data/longmemeval/longmemeval_s_cleaned.json")}
    df = pd.read_csv(ROWS)
    df = df[df.budget.isin([0, 300])].reset_index(drop=True)
    df["answer"] = df.answer.fillna("")
    judge = LLMLinker(args.judge_model, "low", "results/lme_judge_cache_second.json", workers=16)
    v = judge.run([lme.judge_prompt(qs[r.question_id], r.answer) for r in df.itertuples()],
                  lme.JUDGE_SYSTEM, lme.JUDGE_SCHEMA)
    df["second_judge"] = [bool(x.get("correct", False)) for x in v]
    df = df.rename(columns={"correct": "haiku_judge"})

    res = {"second_judge_model": args.judge_model, "n": len(df),
           "agreement": float((df.haiku_judge == df.second_judge).mean()),
           "kappa": kappa(df.haiku_judge, df.second_judge),
           "accuracy_by_judge": df.groupby(["condition", "budget"])[["haiku_judge", "second_judge"]]
           .mean().round(3).reset_index().to_dict("records"),
           "usage": judge.usage}
    json.dump(res, open("results/lme_judge_agreement.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "accuracy_by_judge"}, indent=1))
    print(pd.DataFrame(res["accuracy_by_judge"]).to_string(index=False))

    # Blind human sample: every disagreement, filled up with a random mix of the rest.
    dis = df[df.haiku_judge != df.second_judge]
    rest = df.drop(dis.index).sample(max(args.sample - len(dis), 0), random_state=0)
    s = pd.concat([dis.head(args.sample), rest]).sample(frac=1, random_state=1).reset_index(drop=True)
    s["item"] = range(1, len(s) + 1)
    s["question"] = s.question_id.map(lambda q: qs[q]["question"])
    s["gold_answer"] = s.question_id.map(lambda q: qs[q]["answer"])
    s["human_correct"] = ""
    s[["item", "question", "gold_answer", "answer", "human_correct"]].to_csv("human_check.csv", index=False)
    s[["item", "question_id", "condition", "budget", "haiku_judge", "second_judge"]].to_csv(KEY, index=False)
    print(f"wrote human_check.csv ({len(s)} items, {len(dis)} judge disagreements included)")


if __name__ == "__main__":
    main()
