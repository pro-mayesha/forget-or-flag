"""LongMemEval (Wu et al., 2025) adapter: real multi-session chat histories.

We use the knowledge-update questions of LongMemEval_S (about 50 sessions, ~115k tokens of
history per question), where the user states a fact and later changes it, and the question asks
for the current value. Pipeline per question:

  1. extract   - Claude turns the user's messages in each session into typed memory items
                 (cached per session, so sessions shared across questions are extracted once)
  2. link      - the incremental supersedes detector, shown for each session the new items plus
                 the most similar earlier items (retrieve-then-verify, so cost grows linearly)
  3. select    - the same assemble_context() used on the synthetic benchmark
  4. read      - Claude answers the question from the selected memory
  5. judge     - Claude grades the answer against the gold answer (prompt adapted from
                 LongMemEval's evaluation script)

No gold supersedes links exist here, so the main metric is QA accuracy.
"""
from __future__ import annotations

import json
from datetime import date, datetime

import numpy as np

from .memory import Embedder
from .schema import MemoryItem, Scenario, Session

TURN_CHARS = 3000      # long pasted user turns (code, essays) are truncated before extraction
SESSION_CHARS = 12000
LINK_CANDIDATES = 10   # earlier items shown to the link detector per new item


def load(path: str, types=("knowledge-update",)) -> list[dict]:
    return [x for x in json.load(open(path)) if x["question_type"] in types]


def load_history(path: str = "data/lme_history_questions.json", check: str = "history_check.csv") -> list[dict]:
    """Derived earlier-value questions, minus those the author marked "no" in the manual check."""
    import pandas as pd
    c = pd.read_csv(check)
    rejected = set(c[c["keep (yes/no)"].astype(str).str.strip().str.lower() == "no"].question_id)
    return [x for x in json.load(open(path)) if x["question_id"] not in rejected]


def parse_date(s: str) -> date:
    return datetime.strptime(s.split(" (")[0], "%Y/%m/%d").date()


def sessions_in_order(x: dict) -> list[tuple[str, str, list[dict]]]:
    rows = list(zip(x["haystack_session_ids"], x["haystack_dates"], x["haystack_sessions"]))
    return sorted(rows, key=lambda r: datetime.strptime(r[1], "%Y/%m/%d (%a) %H:%M"))


# ---- 1. extraction ----------------------------------------------------------
EXTRACT_SYSTEM = """You build the long-term memory of a personal AI assistant. You read the user's messages from
one past conversation and write down what is worth remembering about the user for future
conversations: personal facts, events, possessions, numbers and amounts, plans, decisions,
preferences, constraints and deadlines.

Rules:
- Each item must be self-contained and specific: name the subject and keep exact values
  (e.g. "User's personal best in the charity 5K run is 27:12", not "User ran a 5K").
- Record things the user says about themselves and their life, including people close to them
  (family, friends, colleagues, pets) and details mentioned in passing ("by the way, ..."), even when
  the conversation is about something else. Skip generic questions, requests for help, and content
  the user pasted (code, articles) unless it reveals a fact about them.
- Prefer fewer, information-dense items. Return an empty list if there is nothing to remember.
- type is one of: constraint (a rule or limit the user must respect), deadline (has a due date),
  decision (a choice the user made), progress (status of an ongoing task or goal),
  preference (a like or dislike), fact (any other fact about the user).
- due_date is YYYY-MM-DD for deadlines when known, otherwise an empty string."""

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["constraint", "deadline", "decision", "progress",
                                                "preference", "fact"]},
            "content": {"type": "string"},
            "due_date": {"type": "string"},
        },
        "required": ["type", "content", "due_date"],
        "additionalProperties": False,
    }}},
    "required": ["items"],
    "additionalProperties": False,
}


def extract_prompt(date_str: str, turns: list[dict]) -> str:
    msgs, total = [], 0
    for t in turns:
        if t["role"] != "user":
            continue
        c = t["content"]
        c = c if len(c) <= TURN_CHARS else c[:TURN_CHARS] + " [...]"
        if total + len(c) > SESSION_CHARS:
            break
        msgs.append(f"USER: {c}")
        total += len(c)
    return (f"Conversation date: {date_str}\n\nThe user's messages:\n\n" + "\n\n".join(msgs)
            + "\n\nExtract the memory items.")


def build_scenario(x: dict, extracted: dict[tuple[str, str], dict]) -> Scenario:
    """One Scenario per question: items from every session, one query session at the end."""
    items, k = [], 0
    for i, (sid, dstr, _) in enumerate(sessions_in_order(x)):
        for it in extracted[(sid, dstr)].get("items", []):
            due = None
            try:
                due = date.fromisoformat(it["due_date"]) if it["due_date"] else None
            except ValueError:
                pass
            typ = it["type"] if (it["type"] != "deadline" or due) else "fact"
            items.append(MemoryItem(id=f"m{k}", type=typ, content=it["content"].strip(), session=i,
                                    created=parse_date(dstr), topic=sid, due_date=due, show_date=True))
            k += 1
    q = Session(session_id=len(x["haystack_sessions"]), now=parse_date(x["question_date"]),
                query=x["question"], query_topic="")
    # `topic` stores the source session id; it is used only for the evidence-coverage proxies.
    return Scenario(x["question_id"], x["question_type"], items, [q])


# ---- 2. linking -------------------------------------------------------------
LINK_SYSTEM = """You maintain the long-term memory of a personal AI assistant. Memory items are facts the user
stated in past conversations, with the date they were stated.

When the user states something new, decide whether it REPLACES an earlier item, meaning the earlier
item is no longer true and must not be used any more. Examples: a changed number or amount, a new
personal best, a moved or changed plan, a new job, address or possession that replaces an old one,
a corrected or rescheduled date, or a reversed decision.

An item does NOT replace another just because it is on a similar topic. Two different events, two
different possessions, or a fact that adds detail without contradicting the old one are both still
true. Only link items when the new one makes the old one obsolete."""


def _line(m: MemoryItem) -> str:
    return f"- {m.id} | {m.created.isoformat()} | [{m.type}] {m.content}"


def link_prompts(sc: Scenario, emb: Embedder, k: int = LINK_CANDIDATES
                 ) -> list[tuple[str, list[str], list[str]]]:
    """(prompt, new ids, allowed earlier ids) per session that adds items."""
    if not sc.items:
        return []
    vecs = emb.encode([m.content for m in sc.items])
    idx = {m.id: i for i, m in enumerate(sc.items)}
    out = []
    for s in sorted({m.session for m in sc.items}):
        new = [m for m in sc.items if m.session == s]
        earlier = [m for m in sc.items if m.session < s]
        if earlier:
            ev = vecs[[idx[m.id] for m in earlier]]
            keep = set()
            for m in new:
                sims = ev @ vecs[idx[m.id]]
                keep.update(np.argsort(-sims)[:k].tolist())
            earlier = [earlier[i] for i in sorted(keep)]
        prompt = ("EXISTING MEMORY (the earlier items most similar to the new ones):\n"
                  + ("\n".join(_line(m) for m in earlier) or "(empty)")
                  + "\n\nNEW ITEMS stated in the latest conversation, in order:\n"
                  + "\n".join(_line(m) for m in new)
                  + "\n\nFor each new item that replaces one or more earlier items (existing memory, or a new "
                    "item listed before it), return its id and the ids it replaces. Omit new items that replace "
                    "nothing. Return an empty list if nothing is replaced.")
        out.append((prompt, [m.id for m in new], [m.id for m in earlier + new]))
    return out


def parse_links(jobs, results) -> list[tuple[str, str]]:
    links = []
    for (_, new_ids, allowed), res in zip(jobs, results):
        order = {i: j for j, i in enumerate(allowed)}
        for r in res.get("replacements", []):
            n = r["new_id"]
            if n not in new_ids:
                continue
            for o in r["replaced_ids"]:
                if o in order and order[o] < order[n]:
                    links.append((n, o))
    return links


# ---- 4. reading -------------------------------------------------------------
READ_SYSTEM = """You are a personal AI assistant with long-term memory of past conversations with the user.
Answer the user's question using that memory. Information can change over time: when the memory
contains different values for the same thing, the most recently stated one is current. If the memory
does not contain the answer, say that you don't know. Answer in one or two sentences."""

READ_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}},
               "required": ["answer"], "additionalProperties": False}


def read_prompt_items(x: dict, sc: Scenario, ids: list[str], dated: bool = True,
                      outdated: set[str] = frozenset(), replaced_by: dict | None = None) -> str:
    """Selected items in chronological order. Items in `outdated` are kept but marked, so
    questions about earlier values stay answerable (annotate instead of delete). With
    `replaced_by` (old id -> newer MemoryItem), the mark also names the newer value."""
    sel = [m for m in sc.items if m.id in set(ids)]  # sc.items is already chronological
    lines = []
    for m in sel:
        text = m.render() if dated else f"[{m.type}] {m.content}"
        if replaced_by and m.id in replaced_by:
            n = replaced_by[m.id]
            when = f" on {n.created.isoformat()}" if dated else ""
            text += f"  [OUTDATED: replaced{when} by: {n.content}]"
        elif m.id in outdated:
            text += "  [OUTDATED: later replaced]"
        lines.append(text)
    mem = "\n".join(lines) or "(no memory)"
    head = "MEMORY (one item per line, with the date it was stated)" if dated else \
        "MEMORY (one item per line, oldest first)"
    return f"{head}:\n{mem}\n\nCurrent date: {x['question_date']}\nQuestion: {x['question']}"


def read_prompt_raw(x: dict, session_ids: set[str] | None = None) -> str:
    parts = []
    for sid, dstr, turns in sessions_in_order(x):
        if session_ids is not None and sid not in session_ids:
            continue
        body = "\n".join(f"{t['role'].upper()}: {t['content']}" for t in turns)
        parts.append(f"### Conversation on {dstr}\n{body}")
    return (f"PAST CONVERSATIONS:\n\n" + "\n\n".join(parts)
            + f"\n\nCurrent date: {x['question_date']}\nQuestion: {x['question']}")


# ---- 5. judging (adapted from LongMemEval's evaluate_qa.py) -------------------
JUDGE_SYSTEM = "You grade answers from a personal assistant. Reply only with the requested JSON."
JUDGE_SCHEMA = {"type": "object", "properties": {"correct": {"type": "boolean"}},
                "required": ["correct"], "additionalProperties": False}


def judge_prompt(x: dict, answer: str) -> str:
    if x["question_id"].endswith("_abs"):
        rule = ("The question cannot be answered from the user's history. The response is correct if it "
                "says the information is unknown or was not mentioned (it may mention related information "
                "that was given). It is incorrect if it gives a specific answer.")
    elif "derived_from" in x:
        rule = ("The question asks for an earlier value that was later changed. The response is correct if it "
                "gives that earlier value (it may also mention the later value). It is incorrect if it gives only "
                "the later value or says it does not know.")
    else:
        rule = ("The response is correct if it contains the correct answer or is equivalent to it. If the "
                "response mentions earlier information along with the updated answer, it is still correct "
                "as long as it gives the updated answer as the current one. Otherwise it is incorrect.")
    return (f"Question: {x['question']}\nCorrect answer: {x['answer']}\nResponse: {answer}\n\n{rule}\n"
            "Is the response correct?")
