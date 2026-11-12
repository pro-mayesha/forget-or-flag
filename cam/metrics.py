"""Session-level metrics, pooled aggregation and scenario-level bootstrap CIs.

Definitions follow thesis Section 3.3.3, with two clarifications:
  * Contradiction rate is computed over sessions where at least one gold
    superseded pair exists in memory (otherwise no contradiction is possible).
  * Stale rate = fraction of selected items that are gold-superseded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import Scenario, Session

SUMS = ["csr_hit", "csr_n", "mi_hit", "mi_n", "dl_hit", "dl_n", "rel_hit", "rel_n",
        "stale", "n_sel", "contra", "contra_n", "tokens", "sessions"]


def session_row(sc: Scenario, s: Session, selected: list[str], tokens: int) -> dict:
    C = set(selected)
    events = sc.events_in(s)
    pairs = sc.gold_links(s)
    sup = sc.gold_superseded(s)
    mi, dl, rel = sc.gold_must_include(s), sc.gold_imminent_deadlines(s), sc.gold_relevant(s)
    return {
        "scenario": sc.id, "domain": sc.domain, "session": s.session_id, "query": s.query,
        "selected_ids": " ".join(selected), "tokens": tokens, "n_sel": len(C),
        "csr_hit": sum(n in C and o not in C for n, o, _ in events), "csr_n": len(events),
        "event_kinds": " ".join(k for *_, k in events),
        "event_hits": " ".join(str(int(n in C and o not in C)) for n, o, _ in events),
        "mi_hit": len(C & mi), "mi_n": len(mi),
        "dl_hit": len(C & dl), "dl_n": len(dl),
        "rel_hit": len(C & rel), "rel_n": len(rel),
        "stale": len(C & sup),
        "contra": int(any(n in C and o in C for n, o in pairs)), "contra_n": int(bool(pairs)),
        "sessions": 1,
    }


def _ratios(t: pd.Series | dict) -> dict:
    r = lambda a, b: t[a] / t[b] if t[b] else np.nan
    return {"CSR": r("csr_hit", "csr_n"), "MustInclude": r("mi_hit", "mi_n"),
            "DeadlineRecall": r("dl_hit", "dl_n"), "RelevantRecall": r("rel_hit", "rel_n"),
            "StaleRate": r("stale", "n_sel"), "Contradiction": r("contra", "contra_n"),
            "Tokens": r("tokens", "sessions")}


def aggregate(df: pd.DataFrame, n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Pooled metrics per (method, budget) with 95% bootstrap CIs over scenarios."""
    rng = np.random.default_rng(seed)
    out = []
    for (method, budget), g in df.groupby(["method", "budget"], sort=False):
        per_sc = g.groupby("scenario")[SUMS].sum()
        point = _ratios(per_sc.sum())
        mats = per_sc.to_numpy()
        boots = []
        for _ in range(n_boot):
            idx = rng.integers(0, len(mats), len(mats))
            boots.append(_ratios(dict(zip(SUMS, mats[idx].sum(0)))))
        b = pd.DataFrame(boots)
        row = {"method": method, "budget": budget}
        for k, v in point.items():
            row[k] = v
            row[k + "_lo"], row[k + "_hi"] = np.nanpercentile(b[k], [2.5, 97.5]) if b[k].notna().any() else (np.nan, np.nan)
        out.append(row)
    return pd.DataFrame(out)


def csr_by_kind(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        if r["event_kinds"]:
            for k, h in zip(r["event_kinds"].split(), r["event_hits"].split()):
                rows.append({"method": r["method"], "budget": r["budget"], "kind": k, "hit": int(h)})
    return pd.DataFrame(rows).groupby(["method", "budget", "kind"])["hit"].mean().unstack("kind")


def closure(links: set) -> set:
    """Transitive closure of (new, old) pairs; tuples may carry a scenario-id prefix."""
    out = set(links)
    while True:
        by_new = {}
        for l in out:
            by_new.setdefault(l[:-1], set()).add(l[-1])
        extra = {(*l[:-2], l[-2], o2) for l in out for o2 in by_new.get((*l[:-2], l[-1]), ())}
        if extra <= out:
            return out
        out |= extra


def link_prf(pred: set, gold: set) -> dict:
    tp = len(pred & gold)
    # A predicted link is correct if it is in the transitive closure of the gold
    # links (in a chain A -> B -> C, "C replaces A" is also true).
    p = len(pred & closure(gold)) / len(pred) if pred else 0.0
    r = tp / len(gold) if gold else 0.0
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "n_pred": len(pred), "n_gold": len(gold)}
