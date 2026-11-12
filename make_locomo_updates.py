"""Build knowledge-update questions (current and earlier value) from LoCoMo (Maharana et al., 2024).

LoCoMo has almost no questions about facts that change, so we mine them: for each speaker in each of
the 10 conversations, Claude Sonnet 5.5 reads that speaker's dated session observations and lists
facts whose value was stated and later replaced (a count, job, place, plan, possession ...). A second
Sonnet call checks every candidate against the original dialogue turns it cites, and only confirmed
ones are kept. Each fact yields two questions, asked by that speaker in the first person: the
current value and the value before the change.

    python make_locomo_updates.py

Writes data/locomo_updates.json in LongMemEval format (the speaker is the "user", the other person
the "assistant"), so run_longmemeval.py --data runs every condition on it unchanged, and
locomo_check.csv for a human to check every question.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

import pandas as pd

from cam.env import load_env
from cam.llm_links import LLMLinker

SRC = "data/locomo/locomo10.json"
OUT = "data/locomo_updates.json"
MODEL = "claude-sonnet-5-5"

MINE_SYSTEM = """You find facts that CHANGE over time in a long series of conversations.
You are shown dated observations about one person, each with the id of the dialogue turn it comes from.

List every fact about this person whose value is stated explicitly at one time and later stated
with a different value that replaces it: a count that goes up, a job or role that changes, a move,
a changed plan or decision, a pet, car or possession that is replaced, a new personal record, a
status that changes. Do NOT list separate events (two different trips are both still true), facts
that only add detail, or anything where either value is vague or only implied.

For each, write two questions the person would ask an assistant that remembers the conversations,
in the first person ("my", "I"): one about the CURRENT value, and one about the value BEFORE the
change, which refers to the change so it has one clear answer and does not contain the earlier
value. Give short answers."""

ITEM = {"type": "object", "properties": {
    "attribute": {"type": "string"},
    "earlier_value": {"type": "string"}, "earlier_turn": {"type": "string"},
    "later_value": {"type": "string"}, "later_turn": {"type": "string"},
    "current_question": {"type": "string"}, "current_answer": {"type": "string"},
    "history_question": {"type": "string"}, "history_answer": {"type": "string"}},
    "required": ["attribute", "earlier_value", "earlier_turn", "later_value", "later_turn",
                 "current_question", "current_answer", "history_question", "history_answer"],
    "additionalProperties": False}
MINE_SCHEMA = {"type": "object", "properties": {"changes": {"type": "array", "items": ITEM}},
               "required": ["changes"], "additionalProperties": False}

CHECK_SYSTEM = """You check evaluation questions against the original dialogue. Reply only with the requested JSON."""
CHECK_SCHEMA = {"type": "object", "properties": {"valid": {"type": "boolean"}, "reason": {"type": "string"}},
                "required": ["valid", "reason"], "additionalProperties": False}


def parse_dt(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%I:%M %p on %d %B, %Y")


def sessions(c: dict) -> list[tuple[int, datetime, list[dict]]]:
    conv = c["conversation"]
    nums = sorted(int(m.group(1)) for k in conv if (m := re.fullmatch(r"session_(\d+)", k)))
    return [(n, parse_dt(conv[f"session_{n}_date_time"]), conv[f"session_{n}"]) for n in nums]


def mine_prompt(c: dict, speaker: str) -> str:
    lines = []
    for n, dt, _ in sessions(c):
        for text, turn in c["observation"].get(f"session_{n}_observation", {}).get(speaker, []):
            lines.append(f"[{dt:%Y-%m-%d}] ({turn}) {text}")
    return f"PERSON: {speaker}\n\nOBSERVATIONS (oldest first):\n" + "\n".join(lines)


def turn_text(c: dict) -> dict[str, tuple[datetime, str]]:
    return {t["dia_id"]: (dt, f"{t['speaker']}: {t['text']}") for _, dt, turns in sessions(c) for t in turns}


def check_prompt(ch: dict, turns: dict, speaker: str) -> str:
    ev = []
    for k in ("earlier_turn", "later_turn"):
        tid = ch[k].strip("() ")
        dt, txt = turns.get(tid, (None, "(turn not found)"))
        ev.append(f"[{tid}, {dt:%Y-%m-%d}] {txt}" if dt else f"[{tid}] {txt}")
    return (f"The questions are asked by {speaker}.\n\nDIALOGUE TURNS CITED:\n" + "\n".join(ev)
            + f"\n\nCLAIM: {ch['attribute']} was '{ch['earlier_value']}' (first turn) and later changed to "
            f"'{ch['later_value']}' (second turn), which replaces it.\n"
            f"Q1: {ch['current_question']} -> {ch['current_answer']}\n"
            f"Q2: {ch['history_question']} -> {ch['history_answer']}\n\n"
            "Valid only if both turns explicitly state those values, the second is later and replaces the "
            "first (not a separate event), and both answers follow from the turns.")


def to_lme(c: dict, speaker: str, ch: dict, kind: str, i: int) -> dict:
    other = c["conversation"]["speaker_b" if c["conversation"]["speaker_a"] == speaker else "speaker_a"]
    ss = sessions(c)
    ev = {ch["earlier_turn"].strip("() "), ch["later_turn"].strip("() ")}
    hs = [[{"role": "user" if t["speaker"] == speaker else "assistant", "content": t["text"],
            **({"has_answer": True} if t["dia_id"] in ev else {})} for t in turns] for _, _, turns in ss]
    # Session ids name the speaker so extraction (which reads the "user" turns) is cached per speaker.
    ids = [f"{c['sample_id']}_{speaker}_s{n}" for n, _, _ in ss]
    q, a = (ch["current_question"], ch["current_answer"]) if kind == "cur" else \
        (ch["history_question"], ch["history_answer"])
    x = {"question_id": f"{c['sample_id']}_{speaker}_{i}_{kind}", "question_type": "knowledge-update",
         "question": q, "answer": a,
         "question_date": (ss[-1][1].replace(hour=23, minute=59)).strftime("%Y/%m/%d (%a) %H:%M"),
         "haystack_session_ids": ids,
         "haystack_dates": [dt.strftime("%Y/%m/%d (%a) %H:%M") for _, dt, _ in ss],
         "haystack_sessions": hs,
         "answer_session_ids": [sid for sid, s in zip(ids, hs) if any(t.get("has_answer") for t in s)]}
    if kind == "hist":
        x["derived_from"] = x["question_id"][:-5] + "_cur"
    return x


def main():
    load_env()
    data = json.load(open(SRC))
    jobs = [(c, c["conversation"][s]) for c in data for s in ("speaker_a", "speaker_b")]
    miner = LLMLinker(MODEL, "high", "results/locomo_mine_cache.json", workers=8)
    mined = miner.run([mine_prompt(c, sp) for c, sp in jobs], MINE_SYSTEM, MINE_SCHEMA)
    cands = [(c, sp, ch) for (c, sp), r in zip(jobs, mined) for ch in r.get("changes", [])]
    print(f"mine: {miner.usage}; {len(cands)} candidate changes")

    turns = {c["sample_id"]: turn_text(c) for c in data}
    checker = LLMLinker(MODEL, "medium", "results/locomo_check_cache.json", workers=8)
    checks = checker.run([check_prompt(ch, turns[c["sample_id"]], sp) for c, sp, ch in cands],
                         CHECK_SYSTEM, CHECK_SCHEMA)
    print(f"check: {checker.usage}")

    out, rows = [], []
    for k, ((c, sp, ch), v) in enumerate(zip(cands, checks)):
        t = turns[c["sample_id"]]
        e, l = ch["earlier_turn"].strip("() "), ch["later_turn"].strip("() ")
        ok = v["valid"] and e in t and l in t and t[e][0] <= t[l][0] and e != l
        rows.append({"id": f"{c['sample_id']}_{sp}_{k}", "auto_valid": ok, "reason": v["reason"],
                     "earlier_turn": t.get(e, ("", ""))[1], "later_turn": t.get(l, ("", ""))[1],
                     "current_question": ch["current_question"], "current_answer": ch["current_answer"],
                     "history_question": ch["history_question"], "history_answer": ch["history_answer"],
                     "keep (yes/no)": ""})
        if ok:
            out += [to_lme(c, sp, ch, "cur", k), to_lme(c, sp, ch, "hist", k)]
    json.dump(out, open(OUT, "w"))
    pd.DataFrame(rows).to_csv("locomo_check.csv", index=False)
    print(f"{sum(r['auto_valid'] for r in rows)} of {len(rows)} changes confirmed -> {len(out)} questions in {OUT}")


if __name__ == "__main__":
    main()
