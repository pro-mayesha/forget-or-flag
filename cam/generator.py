"""Template-based generator for multi-session scenarios with gold supersedes labels.

Each scenario has 6 sessions. It mixes stable items, distractors and several
update events of different kinds:

  correction      explicit change of a decision ("I'm now targeting B instead of A")
  implicit        decision change with little lexical overlap
  reversal        A -> B, then later B -> A again
  deadline_shift  a deadline moves to a new date
  policy_update   a constraint value changes
  chain           a constraint changes twice (A -> B -> C)

The data is synthetic: it tests specific failure modes under control, not the
distribution of real user conversations.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from .schema import MemoryItem, Scenario, Session

UPDATE_KINDS = ["correction", "implicit", "reversal", "deadline_shift", "policy_update", "chain"]

DOMAINS = {
    "study_abroad": {
        "decisions": [
            {"topic": "country", "values": ["Canada", "Germany", "the UK", "the Netherlands", "Japan", "Australia", "Sweden"],
             "state": "I've decided to focus my applications on {v}.",
             "explicit": "Change of plan: I'm now targeting {v} instead of {old}.",
             "implicit": "Honestly {old} isn't working out for me, so let's put everything into {v} from now on.",
             "back": "Actually, I'm going back to {v} after all.",
             "query": "Which country should I focus my applications on?"},
            {"topic": "program", "values": ["MSc Computer Science", "MSc Data Science", "MEng Robotics", "MSc Electrical Engineering"],
             "state": "My chosen program is {v}.",
             "explicit": "I've switched my program choice to {v} instead of {old}.",
             "implicit": "After the info session I think {v} suits my goals much better than {old}.",
             "back": "On reflection I'm returning to {v}.",
             "query": "Which program am I applying to?"},
        ],
        "constraints": [
            {"topic": "visa_funds", "values": ["10,000 EUR", "11,200 EUR", "12,500 CAD", "20,635 CAD", "15,000 EUR"],
             "state": "Visa rule: I must show proof of funds of {v} per year.",
             "update": "Visa rule update: the required proof of funds is now {v} per year.",
             "query": "How much money do I need to show for the visa?"},
            {"topic": "visa_timing", "values": ["6 months", "3 months", "4 months", "8 weeks"],
             "state": "Visa rule: apply for the student visa at least {v} before departure.",
             "update": "Visa guidance changed: apply for the student visa at least {v} before departure.",
             "query": "When should I apply for the visa before departure?"},
            {"topic": "budget", "values": ["$25,000", "$30,000", "$20,000", "$35,000"],
             "state": "My total yearly budget is capped at {v}.",
             "update": "My yearly budget cap is now {v}.",
             "query": "What is my yearly budget limit?"},
            {"topic": "language", "values": ["IELTS 6.5", "IELTS 7.0", "TOEFL 90", "TOEFL 100"],
             "state": "Language requirement: I need at least {v}.",
             "update": "The language requirement is now {v}.",
             "query": "What language test score do I need?"},
        ],
        "deadline_entities": ["University of Toronto", "TU Munich", "University of Edinburgh", "TU Delft",
                              "KTH Stockholm", "University of Melbourne", "UBC", "Tohoku University"],
        "deadline": "Application deadline for {e}.",
        "deadline_shift": "Update: {e} moved its application deadline.",
        "deadline_query": "When is the {e} application due?",
        "preferences": [
            ("program_fit", "I prefer programs with a strong robotics lab."),
            ("program_fit", "I want a thesis-based master's rather than coursework only."),
            ("program_fit", "Small class sizes matter to me."),
            ("career", "I want good industry internship options after graduation."),
            ("career", "Post-study work visa availability is important to me."),
            ("housing", "I'd like university housing for the first year."),
            ("scholarship", "I'm looking for scholarships that cover tuition fully."),
            ("cost", "Cities with lower living costs are better for me."),
        ],
        "progress": [
            ("documents", "I finished the first draft of my statement of purpose."),
            ("documents", "I requested two recommendation letters."),
            ("documents", "My transcripts have been officially translated."),
        ],
        "pref_queries": [
            ("program_fit", "Compare program fit for engineering across my options."),
            ("career", "Which options give me the best career prospects?"),
            ("scholarship", "What scholarships should I look into?"),
            ("housing", "What should I know about housing?"),
        ],
        "distractors": [
            "I watched a vlog about student life abroad.", "My friend said winters can be really long.",
            "I bought a new laptop for my studies.", "I'm thinking about learning to cook more dishes.",
            "My cousin studied abroad a few years ago.", "I read a forum thread about dorm food.",
            "I joined an online group for international students.", "I need to renew my passport photo soon, maybe.",
            "I like cafés with quiet study spaces.", "I've been practising small talk in English.",
            "A senior told me the campus library is huge.", "I'm curious about local hiking trails.",
            "I might take a gap month before starting.", "I prefer trains over flights when possible.",
            "My parents asked about the time difference.", "I saw a documentary about the city.",
            "I'm comparing phone plans for abroad.", "I started a budgeting spreadsheet for fun.",
            "I want to try joining a sports club.", "I enjoy museums on weekends.",
            "A friend recommended a packing checklist app.", "I was reading about public transport passes.",
            "I'm considering bringing my bicycle.", "I watched a webinar about culture shock.",
            "I asked about student discounts for software.", "I'm learning a few phrases of the local language.",
            "I organised my email folders for applications.", "I prefer morning classes if possible.",
            "I found a podcast about studying overseas.", "My roommate wants to visit me someday.",
        ],
    },
    "project_planning": {
        "decisions": [
            {"topic": "framework", "values": ["React", "Vue", "Svelte", "Angular"],
             "state": "We decided to build the frontend in {v}.",
             "explicit": "Change of plan: the frontend will use {v} instead of {old}.",
             "implicit": "The team struggled with {old}, so we're moving everything over to {v}.",
             "back": "We're reverting to {v} for the frontend.",
             "query": "Which frontend framework are we using?"},
            {"topic": "database", "values": ["PostgreSQL", "MySQL", "MongoDB", "SQLite"],
             "state": "Our primary database is {v}.",
             "explicit": "We switched the primary database to {v} instead of {old}.",
             "implicit": "Benchmarks on {old} were disappointing; {v} is what we'll run on.",
             "back": "We're going back to {v} as the primary database.",
             "query": "Which database are we using?"},
        ],
        "constraints": [
            {"topic": "budget", "values": ["$50,000", "$40,000", "$65,000", "$30,000"],
             "state": "The project budget is capped at {v}.",
             "update": "The project budget cap is now {v}.",
             "query": "What is the project budget?"},
            {"topic": "compliance", "values": ["GDPR", "HIPAA", "SOC 2", "ISO 27001"],
             "state": "Compliance requirement: the system must meet {v}.",
             "update": "Compliance requirement changed: the system must now meet {v}.",
             "query": "Which compliance standard must we meet?"},
            {"topic": "team_size", "values": ["4 engineers", "6 engineers", "3 engineers", "8 engineers"],
             "state": "Staffing constraint: we have {v} available.",
             "update": "Staffing changed: we now have {v} available.",
             "query": "How many engineers do we have?"},
            {"topic": "uptime", "values": ["99.5%", "99.9%", "99%", "99.95%"],
             "state": "SLA constraint: uptime must be at least {v}.",
             "update": "The SLA was renegotiated: uptime must be at least {v}.",
             "query": "What uptime do we have to guarantee?"},
        ],
        "deadline_entities": ["the beta release", "the security audit", "the design review", "the client demo",
                              "the data migration", "the load test", "the public launch", "the API freeze"],
        "deadline": "Milestone deadline for {e}.",
        "deadline_shift": "Update: {e} was rescheduled.",
        "deadline_query": "When is {e} due?",
        "preferences": [
            ("process", "The team prefers two-week sprints."),
            ("process", "We like written design docs before big changes."),
            ("tooling", "We want CI to run on every pull request."),
            ("tooling", "The team prefers TypeScript over plain JavaScript."),
            ("communication", "Stakeholders want a weekly status email."),
            ("communication", "We keep meetings under 30 minutes."),
            ("quality", "We aim for 80% test coverage."),
            ("hosting", "We'd rather use a managed cloud service than self-host."),
        ],
        "progress": [
            ("status", "The login flow is implemented."),
            ("status", "The staging environment is set up."),
            ("status", "We finished the first round of user interviews."),
        ],
        "pref_queries": [
            ("process", "How should we organise our sprints?"),
            ("tooling", "What tooling choices have we made?"),
            ("quality", "What are our quality targets?"),
            ("communication", "How do we keep stakeholders updated?"),
        ],
        "distractors": [
            "Someone brought donuts to stand-up.", "The office Wi-Fi was slow today.",
            "A teammate is going on holiday next month, maybe.", "We tried a new retro format.",
            "I read an article about remote work.", "The designer likes dark mode.",
            "We discussed lunch options for the offsite.", "A colleague recommended a new keyboard.",
            "The team watched a conference talk together.", "We renamed the Slack channel.",
            "Someone suggested a team hackathon.", "The intern asked about git rebasing.",
            "We joked about naming the project after a planet.", "The meeting room projector broke.",
            "A friend's startup uses a similar stack.", "We talked about a book club.",
            "I updated my IDE theme.", "The manager shared a productivity podcast.",
            "We might order team hoodies.", "Someone posted a funny meme in chat.",
            "The coffee machine was fixed.", "We discussed time zones for a future hire.",
            "A teammate is learning Rust on the side.", "We tried pair programming on Friday.",
            "The calendar invite had the wrong room.", "I archived old tickets.",
            "We talked about conference travel next year.", "Someone asked about standing desks.",
            "We celebrated a teammate's birthday.", "The wiki page got a new layout.",
        ],
    },
}


def generate_scenario(idx: int, domain: str, rng: random.Random, n_distractors: int = 30,
                      n_updates: int = 3) -> Scenario:
    spec = DOMAINS[domain]
    sid = f"{domain[:2]}{idx:04d}"
    start = date(2025, 1, 1) + timedelta(days=rng.randrange(300))
    n_sessions = 6
    days = [start]
    for _ in range(n_sessions - 1):
        days.append(days[-1] + timedelta(days=rng.randint(2, 4)))

    items: list[MemoryItem] = []
    counter = iter(range(10_000))

    def add(type_, content, session, topic, due=None, sup=(), kind=None):
        m = MemoryItem(f"{sid}_{type_[:3]}{next(counter)}", type_, content, session,
                       days[session - 1], topic, due, list(sup), kind)
        items.append(m)
        return m

    # stable state stated in sessions 1-2
    decisions = rng.sample(spec["decisions"], 2)
    constraints = rng.sample(spec["constraints"], 3)
    entities = rng.sample(spec["deadline_entities"], 4)
    dec_state, con_state, dl_state = {}, {}, {}
    for d in decisions:
        v = rng.choice(d["values"])
        dec_state[d["topic"]] = (add("decision", d["state"].format(v=v), rng.randint(1, 2), d["topic"]), v, d)
    for c in constraints:
        v = rng.choice(c["values"])
        con_state[c["topic"]] = (add("constraint", c["state"].format(v=v), rng.randint(1, 2), c["topic"]), v, c)
    for e in entities:
        due = start + timedelta(days=rng.randint(10, 120))
        dl_state[e] = add("deadline", spec["deadline"].format(e=e), rng.randint(1, 2), f"deadline:{e}", due)
    for topic, text in rng.sample(spec["preferences"], 6):
        add("preference", text, rng.randint(1, 3), topic)
    for topic, text in spec["progress"]:
        add("progress", text, rng.randint(2, 5), topic)
    for text in rng.sample(spec["distractors"], min(n_distractors, len(spec["distractors"]))):
        add(rng.choice(["preference", "progress"]), text, rng.randint(1, 6), "misc")

    # update events
    kinds = rng.sample(UPDATE_KINDS, n_updates)
    event_topic: dict[int, str] = {}
    used_dec, used_con = set(), set()
    for kind in kinds:
        s = rng.randint(2, 4) if kind in ("reversal", "chain") else rng.randint(2, 6)
        while s in event_topic:
            s = s % n_sessions + 1 if s < n_sessions else 2
        if kind in ("correction", "implicit", "reversal"):
            free = [t for t in dec_state if t not in used_dec]
            if not free:
                kind = "policy_update"
            else:
                t = rng.choice(free); used_dec.add(t)
                old, v0, d = dec_state[t]
                v1 = rng.choice([v for v in d["values"] if v != v0])
                tmpl = d["implicit"] if kind == "implicit" else d["explicit"]
                new = add("decision", tmpl.format(v=v1, old=v0), s, t, sup=[old.id],
                          kind="correction" if kind == "reversal" else kind)
                event_topic[s] = t
                if kind == "reversal":
                    s2 = min(s + 2, n_sessions)
                    back = add("decision", d["back"].format(v=v0), s2, t, sup=[new.id], kind="reversal")
                    event_topic[s2] = t
                continue
        if kind == "deadline_shift":
            e = rng.choice(entities)
            old = dl_state[e]
            new_due = old.due_date + timedelta(days=rng.choice([-21, -14, 14, 30]))
            add("deadline", spec["deadline_shift"].format(e=e), s, f"deadline:{e}", new_due, [old.id], kind)
            event_topic[s] = f"deadline:{e}"
            continue
        free = [t for t in con_state if t not in used_con]
        t = rng.choice(free); used_con.add(t)
        old, v0, c = con_state[t]
        v1 = rng.choice([v for v in c["values"] if v != v0])
        new = add("constraint", c["update"].format(v=v1), s, t, sup=[old.id], kind="policy_update" if kind != "chain" else "chain")
        event_topic[s] = t
        if kind == "chain":
            v2 = rng.choice([v for v in c["values"] if v not in (v0, v1)])
            s2 = min(s + 2, n_sessions)
            add("constraint", c["update"].format(v=v2), s2, t, sup=[new.id], kind="chain")
            event_topic[s2] = t

    # one query per session: about the update if there is one, otherwise a random topic
    sessions = []
    for k in range(1, n_sessions + 1):
        if k in event_topic:
            t = event_topic[k]
        elif rng.random() < 0.5:
            t = rng.choice(spec["pref_queries"])[0]
        else:
            t = rng.choice(list(dec_state) + list(con_state) + [f"deadline:{e}" for e in entities])
        if t.startswith("deadline:"):
            q = spec["deadline_query"].format(e=t.split(":", 1)[1])
        elif t in dec_state:
            q = dec_state[t][2]["query"]
        elif t in con_state:
            q = con_state[t][2]["query"]
        else:
            q = dict(spec["pref_queries"])[t]
        sessions.append(Session(k, days[k - 1], q, t))

    return Scenario(sid, domain, items, sessions)


def generate_benchmark(n_per_domain: int = 100, seed: int = 42, n_distractors: int = 30) -> list[Scenario]:
    rng = random.Random(seed)
    return [generate_scenario(i, d, rng, n_distractors)
            for d in DOMAINS for i in range(n_per_domain)]
