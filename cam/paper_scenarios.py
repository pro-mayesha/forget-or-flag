"""Hand-written re-creations of thesis scenarios s01-s03 (Appendix A).

The original JSON files were lost, so these follow the descriptions and traces in
the thesis text. They are not byte-identical to the originals.
"""
from __future__ import annotations

from datetime import date, timedelta

from .schema import MemoryItem, Scenario, Session


def _sc(sid, start, queries, spec):
    days = [start + timedelta(days=3 * i) for i in range(6)]
    items = [MemoryItem(i, t, c, s, days[s - 1], topic,
                        (start + timedelta(days=due)) if due is not None else None, list(sup), kind)
             for (i, t, c, s, topic, due, sup, kind) in spec]
    sessions = [Session(k + 1, days[k], q, t) for k, (q, t) in enumerate(queries)]
    return Scenario(sid, "study_abroad_paper", items, sessions)


def _filler(prefix, n, session_span=(1, 6)):
    texts = ["I watched a vlog about student life abroad.", "My friend said winters can be long.",
             "I bought a new laptop.", "I read a forum thread about dorm food.",
             "I joined an online group for international students.", "I like quiet cafés.",
             "I'm curious about hiking trails.", "I prefer trains over flights.",
             "I saw a documentary about the city.", "I'm comparing phone plans for abroad.",
             "I enjoy museums on weekends.", "I'm learning a few local phrases."]
    lo, hi = session_span
    return [(f"{prefix}{k}", "preference", texts[k % len(texts)], lo + k % (hi - lo + 1), "misc", None, (), None)
            for k in range(n)]


def paper_scenarios() -> list[Scenario]:
    s01 = _sc("s01", date(2025, 9, 1), [
        ("What should I prioritise this week?", "constraint1"),
        ("What deadlines are coming up?", "deadline:A"),
        ("What decisions do I need to make?", "country"),
        ("How much money do I need to show for the visa?", "constraint1"),
        ("Which program should I commit to?", "program"),
        ("Summarise my current plan.", "country"),
    ], [
        ("constraint1", "constraint", "Visa rule: show proof of funds of 11,200 EUR per year.", 1, "constraint1", None, (), None),
        ("constraint2", "constraint", "My yearly budget is capped at $25,000.", 1, "budget", None, (), None),
        ("deadline1", "deadline", "Application deadline for University A.", 2, "deadline:A", 30, (), None),
        ("deadline2", "deadline", "Scholarship deadline for the DAAD award.", 2, "deadline:S", 40, (), None),
        ("deadline3", "deadline", "Application deadline for University B.", 1, "deadline:B", 100, (), None),
        ("decision1", "decision", "I've decided to apply mainly to the UK.", 1, "country", None, (), None),
        ("decision2", "decision", "Change of plan: I'm targeting Canada instead of the UK.", 3, "country", None, ("decision1",), "correction"),
        ("decision3", "decision", "I'll commit to the MSc Computer Science program.", 5, "program", None, (), None),
    ] + _filler("f01_", 8))

    s02 = _sc("s02", date(2025, 8, 9), [
        ("Which programs fit my interests?", "program_fit"),
        ("What are the costs in Canada and Germany?", "cost"),
        ("Compare program fit between Canada and Germany for engineering", "program_fit"),
        ("What scholarships can I get?", "scholarship"),
        ("What are the admission requirements?", "requirements"),
        ("Which career paths are open after graduation?", "career"),
    ], [
        ("deadline1", "deadline", "Application deadline for University of Toronto.", 1, "deadline:toronto", 90, (), None),
        ("deadline2", "deadline", "Application deadline for TU Munich.", 1, "deadline:munich", 120, (), None),
        ("deadline3", "deadline", "Submit the language test score to the scholarship office.", 2, "deadline:lang", 40, (), None),
        ("deadline4", "deadline", "Housing application closes.", 4, "deadline:housing", 80, (), None),
        ("item_canada", "preference", "I like Canada for its post-study work options.", 1, "program_fit", None, (), None),
        ("item_germany", "preference", "Germany has low tuition for engineering.", 1, "program_fit", None, (), None),
        ("item_engineering", "preference", "I want an engineering master's with a lab focus.", 1, "program_fit", None, (), None),
        ("item_fit", "preference", "Program fit matters more to me than university ranking.", 2, "program_fit", None, (), None),
        ("item_program1", "preference", "Toronto's MEng program looks strong in robotics.", 2, "program_fit", None, (), None),
        ("item_program2", "preference", "TU Munich's MSc offers a thesis track.", 2, "program_fit", None, (), None),
        ("item_career1", "preference", "I want industry internships during my studies.", 1, "career", None, (), None),
        ("item_career2", "preference", "Long term I want to work in robotics R&D.", 2, "career", None, (), None),
        ("item_scholarship1", "preference", "I need scholarships that cover tuition.", 1, "scholarship", None, (), None),
        ("item_cost1", "preference", "Living costs in Toronto are high.", 2, "cost", None, (), None),
        ("item_cost2", "preference", "Munich rent is expensive but tuition is low.", 2, "cost", None, (), None),
        ("item_requirements1", "preference", "Toronto requires IELTS 7.0.", 3, "requirements", None, (), None),
        ("item_requirements2", "preference", "TU Munich requires a GRE score.", 3, "requirements", None, (), None),
        ("item_location1", "preference", "I'd prefer a big city.", 1, "program_fit", None, (), None),
    ] + _filler("f02_", 14))

    s03 = _sc("s03", date(2025, 6, 1), [
        ("What do I need for the visa?", "visa_rule"),
        ("When should I start the visa process?", "visa_rule"),
        ("Make me a visa timeline.", "visa_rule"),
        ("What documents do I need?", "visa_docs"),
        ("How much money do I need to show?", "funds"),
        ("When should I apply for the visa before departure?", "visa_rule"),
    ], [
        ("visa_rule_old", "constraint", "Visa rule: apply at least 6 months before departure.", 1, "visa_rule", None, (), None),
        ("visa_rule_new", "constraint", "Visa guidance changed: apply at least 3 months before departure.", 6, "visa_rule", None, ("visa_rule_old",), "policy_update"),
        ("funds", "constraint", "Proof of funds: 20,635 CAD per year.", 1, "funds", None, (), None),
    ] + [(f"visa_doc{k}", "progress", t, 1 + k % 5, "visa_docs", None, (), None) for k, t in enumerate([
        "I booked a biometrics appointment.", "I need a police clearance certificate.",
        "I scanned my passport for the visa form.", "I need a medical exam for the visa.",
        "My bank statement must cover six months.", "I got a letter of acceptance for the visa file.",
        "I need passport photos in visa format.", "I translated my birth certificate for the visa.",
        "I paid the visa application fee.", "I need a study plan letter for the visa.",
        "I created an account on the visa portal.", "I checked visa processing times online.",
        "I need travel insurance for the visa.", "I asked the embassy about visa interviews.",
        "I saved copies of all visa documents."])] + _filler("f03_", 6))

    return [s01, s02, s03]
