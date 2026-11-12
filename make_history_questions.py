"""Derive earlier-value ("what was it before?") questions from LongMemEval knowledge-update questions.

Every knowledge-update question has two evidence sessions: one where the user states a value and a
later one where it changes. LongMemEval asks for the current value; only 15 of its questions ask
about an earlier one. For each of the other answerable questions, Claude Sonnet 5.5 reads the dated
evidence turns (never any memory system's output) and writes a question whose answer is the value
before the update, or marks the question unusable when no earlier value is stated explicitly.

    python make_history_questions.py

Writes data/lme_history_questions.json (LongMemEval format, ids end in "_hist", same haystacks) and
history_check.csv for a human to check every derived question against the evidence.
"""
from __future__ import annotations

import json
import re

import pandas as pd

from cam import longmemeval as lme
from cam.env import load_env
from cam.llm_links import LLMLinker

DATA = "data/longmemeval/longmemeval_s_cleaned.json"
OUT = "data/lme_history_questions.json"
HISTORY_Q = r"\b(previous|previously|before|initially|originally|first|used to|when I (just )?started)\b"

SYSTEM = """You write evaluation questions for a personal AI assistant with long-term memory.
You are shown the user's messages, with dates, where a fact about the user was stated and later
changed, plus the benchmark question and its answer about the CURRENT value.

Write one question asking for the value BEFORE the change, phrased the way the user would ask it
later (e.g. "What was my personal best in the charity 5K before my current one?"), and its answer.

Rules:
- The earlier value must be stated explicitly in the messages. If it is not (only implied, vague,
  or there is no earlier value), set usable to false.
- The question must not contain the earlier value, and should refer to the change so it has one
  clear answer (avoid "first" when there may have been values before the ones shown).
- The answer is the earlier value only, short, with alternatives in parentheses if useful."""

SCHEMA = {"type": "object", "properties": {
    "usable": {"type": "boolean"}, "question": {"type": "string"}, "answer": {"type": "string"},
    "evidence": {"type": "string", "description": "the user's words that state the earlier value"}},
    "required": ["usable", "question", "answer", "evidence"], "additionalProperties": False}


def prompt(x: dict) -> str:
    lines = []
    for sid, dstr, turns in lme.sessions_in_order(x):
        if sid in x["answer_session_ids"]:
            lines += [f"[{dstr}] USER: {t['content'][:1500]}" for t in turns
                      if t["role"] == "user" and t.get("has_answer")]
    return ("EVIDENCE (the user's messages, oldest first):\n" + "\n\n".join(lines)
            + f"\n\nBENCHMARK QUESTION: {x['question']}\nANSWER (current value): {x['answer']}")


def main():
    load_env()
    qs = [x for x in lme.load(DATA) if not x["question_id"].endswith("_abs")
          and not re.search(HISTORY_Q, x["question"], re.I)]
    gen = LLMLinker("claude-sonnet-5-5", "medium", "results/lme_histgen_cache.json", workers=8)
    res = gen.run([prompt(x) for x in qs], SYSTEM, SCHEMA)
    print("generate:", gen.usage)

    out, rows = [], []
    for x, r in zip(qs, res):
        rows.append({"question_id": x["question_id"] + "_hist", "usable": r["usable"],
                     "original_question": x["question"], "current_answer": x["answer"],
                     "history_question": r["question"], "history_answer": r["answer"],
                     "evidence": r["evidence"], "keep (yes/no)": ""})
        if r["usable"]:
            out.append({**x, "question_id": x["question_id"] + "_hist", "question": r["question"],
                        "answer": r["answer"], "derived_from": x["question_id"]})
    json.dump(out, open(OUT, "w"), indent=1)
    try:  # never overwrite the author's manual check
        marked = pd.read_csv("history_check.csv")["keep (yes/no)"].notna().any()
    except FileNotFoundError:
        marked = False
    if not marked:
        pd.DataFrame(rows).to_csv("history_check.csv", index=False)
    print(f"{len(qs)} source questions, {len(out)} usable derived questions -> {OUT}, history_check.csv")


if __name__ == "__main__":
    main()
