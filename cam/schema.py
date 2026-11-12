"""Data model for memory items, sessions and scenarios, plus gold-label helpers.

Gold labels (topic, supersedes) are used only by the evaluator and by the
`links="gold"` oracle setting. Methods never read `topic`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
import json

TYPES = ("constraint", "deadline", "decision", "progress", "preference", "fact")  # fact: LongMemEval only
IMMINENT_DAYS = 45


@dataclass
class MemoryItem:
    id: str
    type: str
    content: str
    session: int                 # session in which the user stated it
    created: date
    topic: str                   # gold topic label (evaluation only)
    due_date: date | None = None
    supersedes: list[str] = field(default_factory=list)  # gold links: this item -> older items
    update_kind: str | None = None                        # e.g. correction, reversal (gold)
    show_date: bool = False      # prefix the date it was stated (LongMemEval)

    def render(self) -> str:
        due = f" (due {self.due_date.isoformat()})" if self.due_date else ""
        when = f"({self.created.isoformat()}) " if self.show_date else ""
        return f"{when}[{self.type}] {self.content}{due}"


@dataclass
class Session:
    session_id: int
    now: date
    query: str
    query_topic: str


@dataclass
class Scenario:
    id: str
    domain: str
    items: list[MemoryItem]
    sessions: list[Session]

    # ---- gold views -------------------------------------------------------
    def memory_at(self, s: Session) -> list[MemoryItem]:
        return [m for m in self.items if m.session <= s.session_id]

    def gold_links(self, s: Session | None = None) -> list[tuple[str, str]]:
        items = self.items if s is None else self.memory_at(s)
        return [(m.id, old) for m in items for old in m.supersedes]

    def gold_superseded(self, s: Session) -> set[str]:
        return {old for _, old in self.gold_links(s)}

    def gold_valid(self, s: Session) -> list[MemoryItem]:
        sup = self.gold_superseded(s)
        return [m for m in self.memory_at(s) if m.id not in sup]

    def gold_imminent_deadlines(self, s: Session) -> set[str]:
        return {m.id for m in self.gold_valid(s)
                if m.type == "deadline" and m.due_date
                and 0 <= (m.due_date - s.now).days <= IMMINENT_DAYS}

    def gold_must_include(self, s: Session) -> set[str]:
        return {m.id for m in self.gold_valid(s) if m.type in ("constraint", "decision")} \
            | self.gold_imminent_deadlines(s)

    def gold_relevant(self, s: Session) -> set[str]:
        return {m.id for m in self.gold_valid(s) if m.topic == s.query_topic}

    def events_in(self, s: Session) -> list[tuple[str, str, str]]:
        """Superseding events introduced in this session: (new, old, kind)."""
        return [(m.id, old, m.update_kind or "update")
                for m in self.items if m.session == s.session_id for old in m.supersedes]

    # ---- io ---------------------------------------------------------------
    def to_json(self) -> dict:
        def enc(o):
            d = asdict(o)
            for k, v in d.items():
                if isinstance(v, date):
                    d[k] = v.isoformat()
            return d
        return {"id": self.id, "domain": self.domain,
                "items": [enc(m) for m in self.items],
                "sessions": [enc(s) for s in self.sessions]}

    @staticmethod
    def from_json(d: dict) -> "Scenario":
        pd = lambda x: date.fromisoformat(x) if x else None
        items = [MemoryItem(**{**m, "created": pd(m["created"]), "due_date": pd(m["due_date"])})
                 for m in d["items"]]
        sessions = [Session(**{**s, "now": pd(s["now"])}) for s in d["sessions"]]
        return Scenario(d["id"], d["domain"], items, sessions)


def save_scenarios(scenarios: list[Scenario], path: str) -> None:
    with open(path, "w") as f:
        json.dump([s.to_json() for s in scenarios], f, indent=1)


def load_scenarios(path: str) -> list[Scenario]:
    with open(path) as f:
        return [Scenario.from_json(d) for d in json.load(f)]
