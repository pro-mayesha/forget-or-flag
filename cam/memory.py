"""Constraint-aware context assembly (the method) and baseline selectors.

All conditions go through `assemble_context`; variants differ only by `Config`.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

import numpy as np

from .schema import IMMINENT_DAYS, MemoryItem, Scenario, Session

# Paper weights (Section 3.2.3). They sum to 0.85; only relative size matters for ranking.
W_SIM, W_REC, W_SAL, W_DEC = 0.25, 0.20, 0.25, 0.15
SALIENCE = {"constraint": 1.0, "deadline": 0.9, "decision": 0.8, "progress": 0.5, "preference": 0.4,
            "fact": 0.6}
DECAY_DAYS = 14.0
LINK_THRESHOLD = 0.80   # cosine threshold for the heuristic supersedes predictor
SUMMARY_TOKENS = 8      # per-item truncation length for the lossy-summary baseline


@dataclass(frozen=True)
class Config:
    name: str
    selector: str = "ranked"          # ranked | recency | summary | full | none
    scoring: str = "full"             # full | similarity
    must_include: bool = True
    conflict_resolution: bool = True
    links: str = "gold"               # gold | heuristic  (source of supersedes links)


METHODS = [
    Config("no_memory", selector="none"),
    Config("full_history", selector="full"),
    Config("sliding_window", selector="recency"),
    Config("summary_truncated", selector="summary"),
    Config("similarity_rag", scoring="similarity", must_include=False, conflict_resolution=False),
    Config("method_full_gold"),
    Config("method_full_heuristic", links="heuristic"),
    Config("ablate_no_must_include", must_include=False),
    Config("ablate_no_conflict_res", conflict_resolution=False),
    Config("ablate_similarity_scoring", scoring="similarity"),
]


# ---------------------------------------------------------------------------
class Embedder:
    """Sentence embeddings (all-MiniLM-L6-v2, offline cache) with a TF-IDF fallback."""

    def __init__(self):
        self.cache: dict[str, np.ndarray] = {}
        try:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            self.kind = "all-MiniLM-L6-v2"
        except Exception:  # pragma: no cover
            self.model, self.kind = None, "tfidf"

    def encode(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if missing:
            if self.model is not None:
                vecs = self.model.encode(missing, normalize_embeddings=True, batch_size=128)
            else:
                from sklearn.feature_extraction.text import TfidfVectorizer
                vecs = TfidfVectorizer().fit_transform(missing).toarray()
                vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
            self.cache.update(zip(missing, vecs))
        return np.stack([self.cache[t] for t in texts])


class Tokens:
    def __init__(self):
        import tiktoken
        self.enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        self.cache: dict[str, int] = {}

    def count(self, text: str) -> int:
        if text not in self.cache:
            self.cache[text] = len(self.enc.encode(text))
        return self.cache[text]

    def truncate(self, text: str, n: int) -> str:
        ids = self.enc.encode(text)
        return text if len(ids) <= n else self.enc.decode(ids[:n]) + "…"


# ---------------------------------------------------------------------------
def predict_links(items: list[MemoryItem], emb: Embedder,
                  threshold: float = LINK_THRESHOLD) -> list[tuple[str, str]]:
    """Heuristic supersedes detection without gold labels: a later item of the same
    type whose text is highly similar to an earlier one is taken to replace it."""
    if not items:
        return []
    vecs = emb.encode([m.content for m in items])
    sims = vecs @ vecs.T
    links = []
    for j, new in enumerate(items):
        for i, old in enumerate(items):
            if i != j and old.type == new.type and (old.session, i) < (new.session, j) \
                    and sims[i, j] >= threshold:
                links.append((new.id, old.id))
    return links


def _priority(m: MemoryItem, now) -> tuple:
    # Must-include ordering when the protected set itself exceeds the budget.
    if m.type == "deadline":
        return (0, (m.due_date - now).days, m.id)
    return ({"constraint": 1, "decision": 2}[m.type], -m.session, m.id)


def assemble_context(sc: Scenario, s: Session, cfg: Config, budget: int,
                     emb: Embedder, tok: Tokens, links: list[tuple[str, str]] | None = None
                     ) -> tuple[list[str], int]:
    """Return (selected item ids, tokens used) for one session."""
    mem = sc.memory_at(s)
    if cfg.selector == "none" or not mem:
        return [], 0
    if cfg.selector == "full":
        return [m.id for m in mem], sum(tok.count(m.render()) for m in mem)

    newest_first = sorted(mem, key=lambda m: (m.session, sc.items.index(m)), reverse=True)
    if cfg.selector in ("recency", "summary"):
        chosen, used = [], 0
        for m in newest_first:
            text = tok.truncate(m.content, SUMMARY_TOKENS) if cfg.selector == "summary" else m.render()
            c = tok.count(text)
            if used + c <= budget:
                chosen.append(m.id)
                used += c
        return chosen, used

    # ---- ranked selection (similarity RAG and the proposed method) ----------
    if cfg.conflict_resolution:
        lk = links if links is not None else sc.gold_links(s)
        ids = {m.id for m in mem}
        superseded = {old for new, old in lk if new in ids}
        cands = [m for m in mem if m.id not in superseded]
    else:
        cands = list(mem)

    # Stage 1: must-include (active constraints, decisions, imminent deadlines)
    protected = []
    if cfg.must_include:
        protected = [m for m in cands if m.type in ("constraint", "decision")
                     or (m.type == "deadline" and m.due_date
                         and 0 <= (m.due_date - s.now).days <= IMMINENT_DAYS)]
        protected.sort(key=lambda m: _priority(m, s.now))
    pset = {m.id for m in protected}

    # Stage 2: score the rest
    rest = [m for m in cands if m.id not in pset]
    if rest:
        vecs = emb.encode([m.content for m in rest])
        q = emb.encode([s.query])[0]
        sim = (vecs @ q + 1) / 2
        if cfg.scoring == "similarity":
            score = sim
        else:
            rank = {m.id: r for r, m in enumerate(newest_first)}
            n = max(len(newest_first) - 1, 1)
            rec = np.array([1 - rank[m.id] / n for m in rest])
            dec = np.array([math.exp(-(s.now - m.created).days / DECAY_DAYS) for m in rest])
            sal = np.array([SALIENCE[m.type] for m in rest])
            score = W_SIM * sim + W_REC * rec + W_SAL * sal + W_DEC * dec
        order = sorted(range(len(rest)), key=lambda i: (-score[i], rest[i].id))
        rest = [rest[i] for i in order]

    # Stage 3: budget-aware greedy packing; protected items go first
    chosen, used = [], 0
    for m in protected + rest:
        c = tok.count(m.render())
        if used + c <= budget:
            chosen.append(m.id)
            used += c
    return chosen, used
