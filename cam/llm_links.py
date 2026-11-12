"""LLM-based supersedes-link detection with Claude.

Runs incrementally, as a deployed assistant would: after each session the model
sees the memory stored so far plus the items stated in that session, and says
which earlier items each new item replaces. Gold labels are never shown.

Responses are cached on disk (keyed by model, effort and prompt), so re-running
is free and results are reproducible.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from .schema import MemoryItem, Scenario

SYSTEM = """You maintain the long-term memory of an AI assistant that helps a user with a multi-week plan.
Memory items are facts the user stated: constraints, deadlines, decisions, progress and preferences.

When the user states something new, decide whether it REPLACES an earlier item, meaning the earlier
item is no longer true and must not be used any more. Examples: a changed decision, a corrected or
rescheduled deadline, an updated rule or limit, or going back to an earlier choice (which replaces the
choice made in between).

An item does NOT replace another just because it is on a similar topic. Two deadlines for different
institutions, or two different preferences, are both still true. Only link items when the new one
makes the old one obsolete."""

SCHEMA = {
    "type": "object",
    "properties": {
        "replacements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "new_id": {"type": "string"},
                    "replaced_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["new_id", "replaced_ids"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["replacements"],
    "additionalProperties": False,
}


def _line(m: MemoryItem) -> str:
    return f"- {m.id} | session {m.session} ({m.created.isoformat()}) | {m.render()}"


def session_prompts(sc: Scenario) -> list[tuple[int, str, list[str], list[str]]]:
    """(session, prompt, new ids, allowed earlier ids) for every session that adds items."""
    out = []
    for s in sc.sessions:
        earlier = [m for m in sc.items if m.session < s.session_id]
        new = [m for m in sc.items if m.session == s.session_id]
        if not new:
            continue
        prompt = ("EXISTING MEMORY (stated in earlier sessions):\n"
                  + ("\n".join(_line(m) for m in earlier) or "(empty)")
                  + f"\n\nNEW ITEMS stated in session {s.session_id}, in the order the user said them:\n"
                  + "\n".join(_line(m) for m in new)
                  + "\n\nFor each new item that replaces one or more earlier items (existing memory, or a new "
                    "item listed before it), return its id and the ids it replaces. Omit new items that replace "
                    "nothing. Return an empty list if nothing is replaced.")
        out.append((s.session_id, prompt, [m.id for m in new], [m.id for m in earlier + new]))
    return out


class LLMLinker:
    def __init__(self, model: str = "claude-opus-5-5", effort: str = "medium",
                 cache_path: str = "results/llm_cache.json", workers: int = 8):
        self.model, self.effort, self.cache_path, self.workers = model, effort, cache_path, workers
        self.cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
        self.lock = threading.Lock()
        self.client = None
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0, "refusals": 0}

    def _key(self, prompt: str, system: str = SYSTEM) -> str:
        return hashlib.sha256(f"{self.model}|{self.effort}|{system}|{prompt}".encode()).hexdigest()

    def _call(self, prompt: str, system: str = SYSTEM, schema: dict = SCHEMA) -> dict:
        key = self._key(prompt, system)
        if key in self.cache:
            return self.cache[key]
        import anthropic
        if self.client is None:
            # User-scoped keys (sk-ant-usr-...) must name a workspace on every request.
            ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
            self.client = anthropic.Anthropic(
                max_retries=5, default_headers={"anthropic-workspace-id": ws} if ws else None)
        # Server-side refusal fallback where the model supports it (not Haiku).
        fb = {} if "haiku" in self.model else {"betas": ["server-side-fallback-2026-07-01"],
                                                "fallbacks": "default"}
        resp = self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
            **fb,
        )
        with self.lock:
            self.usage["calls"] += 1
            self.usage["input_tokens"] += resp.usage.input_tokens
            self.usage["output_tokens"] += resp.usage.output_tokens
        if resp.stop_reason == "refusal":
            with self.lock:
                self.usage["refusals"] += 1
            result = {"refused": True}
        else:
            text = next(b.text for b in resp.content if b.type == "text")
            result = json.loads(text)
        with self.lock:
            self.cache[key] = result
            dirty = self.usage["calls"] % 25 == 0
        if dirty:  # save progress so a crash or billing stop never loses paid-for calls
            self.save()
        return result

    def save(self):
        """Merge into the file on disk, so processes sharing a cache never erase each other's entries."""
        if not self.usage["calls"]:
            return
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        with self.lock:
            disk = json.load(open(self.cache_path)) if os.path.exists(self.cache_path) else {}
            disk.update(self.cache)
            tmp = f"{self.cache_path}.{os.getpid()}.tmp"
            json.dump(disk, open(tmp, "w"))
            os.replace(tmp, self.cache_path)

    def run(self, prompts: list[str], system: str, schema: dict) -> list[dict]:
        """Call the model on many prompts in parallel (cached; duplicates sent once)."""
        uniq = list(dict.fromkeys(prompts))
        try:
            with ThreadPoolExecutor(self.workers) as ex:
                res = dict(zip(uniq, ex.map(lambda p: self._call(p, system, schema), uniq)))
        finally:
            self.save()
        return [res[p] for p in prompts]

    def predict(self, scenarios: list[Scenario]) -> dict[str, list[tuple[str, str]]]:
        jobs = [(sc.id, p) for sc in scenarios for p in session_prompts(sc)]
        try:
            with ThreadPoolExecutor(self.workers) as ex:
                results = list(ex.map(lambda j: self._call(j[1][1]), jobs))
        finally:
            self.save()
        links: dict[str, list[tuple[str, str]]] = {sc.id: [] for sc in scenarios}
        for (sid, (_, _, new_ids, allowed)), res in zip(jobs, results):
            order = {i: k for k, i in enumerate(allowed)}
            for r in res.get("replacements", []):
                n = r["new_id"]
                if n not in new_ids:
                    continue  # ignore hallucinated ids
                for o in r["replaced_ids"]:
                    if o in order and order[o] < order[n]:
                        links[sid].append((n, o))
        return links


def estimate_cost(scenarios: list[Scenario], price_in: float, price_out: float,
                  out_tokens_per_call: int = 60) -> dict:
    """Rough pre-run estimate. Uses tiktoken as a proxy, so treat it as approximate."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    prompts = [p for sc in scenarios for _, p, _, _ in session_prompts(sc)]
    tin = sum(len(enc.encode(SYSTEM + p)) for p in prompts) * 1.3  # newer Claude tokenizers count more
    tout = len(prompts) * out_tokens_per_call
    return {"calls": len(prompts), "input_tokens": int(tin), "output_tokens": tout,
            "usd": round(tin / 1e6 * price_in + tout / 1e6 * price_out, 2)}
