"""How good are the LLM supersedes links on LongMemEval, and how do they explain deletion's losses?

1. Precision: Claude Sonnet 5.5 labels every predicted link (earlier item, later item, both dated)
   as a true replacement or not, and names the error kind.
2. Recall proxy: a knowledge-update question's change counts as detected when some item from the
   later evidence session is linked to some item from the earlier evidence session.
3. History questions answered under deletion, split by whether the change was detected.

    python analyze_links.py     # after run_longmemeval.py and run_longmemeval.py --history --tag _hist

Writes results/lme_link_analysis.json and results/lme_link_labels.csv.
"""
from __future__ import annotations

import json

import pandas as pd

from cam import longmemeval as lme
from cam.env import load_env
from cam.llm_links import LLMLinker

DATA = "data/longmemeval/longmemeval_s_cleaned.json"

SYSTEM = """You check the long-term memory of a personal AI assistant. A link says that a LATER memory
item replaces an EARLIER one, meaning the earlier item is no longer true. Reply only with the JSON."""
SCHEMA = {"type": "object", "properties": {
    "label": {"type": "string", "enum": ["replacement", "addition", "different_thing", "same_value", "other"]},
    "reason": {"type": "string"}}, "required": ["label", "reason"], "additionalProperties": False}


def prompt(o, n) -> str:
    return (f"EARLIER ({o.created.isoformat()}): {o.content}\nLATER ({n.created.isoformat()}): {n.content}\n\n"
            "Label the link: replacement (the earlier item is no longer true because of the later one), "
            "addition (the later item adds to the earlier one, which stays true, e.g. a new purchase or "
            "event), different_thing (they are about different things), same_value (both say the same), "
            "or other.")


def main():
    load_env()
    qs = lme.load(DATA)
    sess = {}
    for x in qs:
        for sid, dstr, turns in lme.sessions_in_order(x):
            sess.setdefault((sid, dstr), lme.extract_prompt(dstr, turns))
    ext = LLMLinker("claude-haiku-5-5", "medium", "results/lme_extract_cache.json", workers=16)
    sids = list(sess)
    extracted = dict(zip(sids, ext.run([sess[s] for s in sids], lme.EXTRACT_SYSTEM, lme.EXTRACT_SCHEMA)))
    assert ext.usage["calls"] == 0, "extraction should be fully cached"
    scs = {x["question_id"]: lme.build_scenario(x, extracted) for x in qs}
    links = json.load(open("results/lme_llm_links.json"))

    rows = []
    for x in qs:
        byid = {m.id: m for m in scs[x["question_id"]].items}
        for n, o in links[x["question_id"]]:
            rows.append({"question_id": x["question_id"], "new": n, "old": o,
                         "old_text": byid[o].content, "new_text": byid[n].content,
                         "p": prompt(byid[o], byid[n])})
    judge = LLMLinker("claude-sonnet-5-5", "medium", "results/lme_linkcheck_cache.json", workers=16)
    res = judge.run([r["p"] for r in rows], SYSTEM, SCHEMA)
    df = pd.DataFrame(rows).drop(columns="p")
    df["label"], df["reason"] = [r["label"] for r in res], [r["reason"] for r in res]
    df.to_csv("results/lme_link_labels.csv", index=False)

    # recall proxy: a link from the latest evidence session into an older evidence session
    detected = {}
    for x in qs:
        if x["question_id"].endswith("_abs"):
            continue
        ev = [r[0] for r in lme.sessions_in_order(x) if r[0] in set(x["answer_session_ids"])]
        byid = {m.id: m for m in scs[x["question_id"]].items}
        detected[x["question_id"]] = any(byid[n].topic == ev[-1] and byid[o].topic in ev[:-1]
                                         for n, o in links[x["question_id"]]) if len(ev) > 1 else None

    h = pd.read_csv("results/lme_hist_rows.csv")
    h = h[h.budget == 300]
    h["src"] = h.question_id.str.replace("_hist", "", regex=False)
    h["detected"] = h.src.map(detected)
    split = (h[h.condition.isin(["rag+cr_llm", "rag+annotate_llm", "similarity_rag"])]
             .groupby(["detected", "condition"]).correct.agg(["mean", "size"]).round(3))

    out = {"links": len(df), "links_per_question": len(df) / len(qs),
           "label_counts": df.label.value_counts().to_dict(),
           "precision": float((df.label == "replacement").mean()),
           "change_detected": float(pd.Series([v for v in detected.values() if v is not None]).mean()),
           "questions_with_detection_info": sum(v is not None for v in detected.values()),
           "history_by_detection": {f"{d}|{c}": v for (d, c), v in split.to_dict("index").items()},
           "usage": judge.usage}
    json.dump(out, open("results/lme_link_analysis.json", "w"), indent=1)
    print(json.dumps(out, indent=1))
    print(df[df.label != "replacement"][["old_text", "new_text", "label"]].head(15).to_string())


if __name__ == "__main__":
    main()
