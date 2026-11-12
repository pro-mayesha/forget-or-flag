"""Mem0 (open-source, v2.x) as an external memory-system baseline on LongMemEval.

For each question, Mem0 builds memory from the haystack sessions in order (its own LLM
extraction, Claude Haiku 5.5), then its own search retrieves memories for the question. The top
results are packed into the same token budget and answered and judged with the same reader and
judge as run_longmemeval.py, so only the memory layer differs.

    python run_mem0.py --n 1            # smoke test
    python run_mem0.py                  # all knowledge-update questions
    .venv-mem0v1/bin/python run_mem0.py --v1   # Mem0 1.x, which updates and deletes memories
    python run_mem0.py --history                # earlier-value questions (make_history_questions.py)

Mem0 2.x extracts memories additively: updates and deletions happen only through explicit API
calls, so it keeps superseded facts. The OSS version does not accept timestamps, so memories are
shown oldest first without dates.
Mem0 1.x instead runs an LLM update step after each extraction (ADD / UPDATE / DELETE / NONE
against similar existing memories), which overwrites or removes superseded facts; --v1 runs that
version (installed in its own environment) with separate output files. Retrieved memories are saved to results/mem0_memories.json, so
memory is built only once per question.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

os.environ["MEM0_TELEMETRY"] = "False"     # never send usage data to Mem0's servers
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import anthropic
import pandas as pd

from cam import longmemeval as lme
from cam.env import load_env
from cam.llm_links import LLMLinker
from cam.memory import Tokens

DATA = "data/longmemeval/longmemeval_s_cleaned.json"
HISTORY_DATA = "data/lme_history_questions.json"
V1 = "--v1" in sys.argv
SUFFIX = "_v1" if V1 else ""
OUT = f"results/mem0{SUFFIX}_memories.json"
STORE = os.path.expanduser(f"~/.cache/cam_mem0{SUFFIX}")   # per-question Qdrant + history DBs
MODEL = "claude-haiku-5-5"
usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
lock = threading.Lock()


def counted(client: anthropic.Anthropic) -> anthropic.Anthropic:
    create = client.messages.create

    def wrapped(**kw):
        r = create(**kw)
        # Mem0 1.x reads content[0].text, but Haiku 5.5 may put a thinking block first.
        r.content = [b for b in r.content if b.type == "text"] or r.content
        with lock:
            usage["calls"] += 1
            usage["input_tokens"] += r.usage.input_tokens
            usage["output_tokens"] += r.usage.output_tokens
        return r
    client.messages.create = wrapped
    return client


def build_memory(x: dict) -> list[dict]:
    from mem0 import Memory
    from qdrant_client import QdrantClient
    # Derived questions share their source question's haystack, so Mem0 2.x reuses its on-disk store.
    path = os.path.join(STORE, x.get("derived_from", x["question_id"]))
    reuse = not V1 and os.path.exists(os.path.join(path, "collection"))
    os.makedirs(path, exist_ok=True)
    llm = {"model": MODEL, "max_tokens": 8000}
    # Claude Haiku 5.5 takes no sampling parameters; each Mem0 version turns them off differently.
    llm.update({"temperature": None, "top_k": None} if V1 else {"enable_sampling_parameters": False})
    m = Memory.from_config({
        "llm": {"provider": "anthropic", "config": llm},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"}},
        # Mem0 1.x writes from a worker thread, which local on-disk Qdrant rejects, so it gets an
        # in-memory store; retrieved memories are saved to OUT either way.
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": "m", "embedding_model_dims": 384,
            **({"client": QdrantClient(location=":memory:")} if V1 else {"path": path, "on_disk": True})}},
        "history_db_path": os.path.join(path, "history.db"),
    })
    # User-scoped keys need the workspace header, which Mem0's own client does not send.
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
    m.llm.client = counted(anthropic.Anthropic(
        max_retries=8, default_headers={"anthropic-workspace-id": ws} if ws else None))
    for _, _, turns in ([] if reuse else lme.sessions_in_order(x)):
        msgs = [{"role": t["role"], "content": t["content"][:lme.TURN_CHARS]} for t in turns]
        m.add(msgs, user_id="u")
    res = (m.search(x["question"], user_id="u", limit=50) if V1 else
           m.search(x["question"], filters={"user_id": "u"}, top_k=50))
    return [{"memory": r["memory"], "score": r.get("score"), "created_at": r.get("created_at")}
            for r in res["results"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--budgets", type=int, nargs="+", default=[300, 1000])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--v1", action="store_true", help="Mem0 1.x, with its update/delete step")
    ap.add_argument("--history", action="store_true", help="earlier-value questions only")
    args = ap.parse_args()
    load_env()
    tag = SUFFIX + ("_hist" if args.history else "")

    qs = lme.load(DATA)
    if args.history:
        hist = r"\b(previous|previously|before|initially|originally|first|used to|when I (just )?started)\b"
        qs = [x for x in qs if re.search(hist, x["question"], re.I) and not x["question_id"].endswith("_abs")]
        qs += lme.load_history(HISTORY_DATA)
    qs = qs[: args.n]
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [x for x in qs if x["question_id"] not in done]
    print(f"{len(qs)} questions, {len(todo)} need memory built")

    def job(x):
        mems = build_memory(x)
        with lock:
            done[x["question_id"]] = mems
            json.dump(done, open(OUT + ".tmp", "w"))
            os.replace(OUT + ".tmp", OUT)
        print(f"  {x['question_id']}: {len(mems)} memories retrieved; usage so far {usage}", flush=True)

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(job, todo))
    print("mem0 build usage:", usage)

    # Pack the top-ranked memories into each budget, show them oldest first, then read and judge.
    tok = Tokens()
    plan = []
    for x in qs:
        mems = done[x["question_id"]]
        for b in args.budgets:
            chosen, used = [], 0
            for r in mems:
                c = tok.count(r["memory"])
                if used + c <= b:
                    chosen.append(r)
                    used += c
            chosen.sort(key=lambda r: r["created_at"] or "")
            body = "\n".join(f"- {r['memory']}" for r in chosen) or "(no memory)"
            prompt = (f"MEMORY (one item per line, oldest first):\n{body}\n\n"
                      f"Current date: {x['question_date']}\nQuestion: {x['question']}")
            plan.append((x, b, used, prompt))

    reader = LLMLinker(MODEL, "medium", "results/lme_read_cache.json", workers=16)
    answers = [r.get("answer", "") for r in reader.run([p[3] for p in plan], lme.READ_SYSTEM, lme.READ_SCHEMA)]
    judge = LLMLinker(MODEL, "low", "results/lme_judge_cache.json", workers=16)
    verdicts = judge.run([lme.judge_prompt(p[0], a) for p, a in zip(plan, answers)],
                         lme.JUDGE_SYSTEM, lme.JUDGE_SCHEMA)
    df = pd.DataFrame([{"question_id": p[0]["question_id"], "abstention": p[0]["question_id"].endswith("_abs"),
                        "condition": "mem0" + SUFFIX, "budget": p[1], "context_tokens": p[2], "answer": a,
                        "correct": bool(v.get("correct", False))}
                       for p, a, v in zip(plan, answers, verdicts)])
    df.to_csv(f"results/lme_mem0{tag}_rows.csv", index=False)
    print(df.groupby("budget")[["correct", "context_tokens"]].mean().round(3))
    json.dump({"build_usage": usage, "read": reader.usage, "judge": judge.usage},
              open(f"results/lme_mem0{tag}_run.json", "w"), indent=1)


if __name__ == "__main__":
    main()
