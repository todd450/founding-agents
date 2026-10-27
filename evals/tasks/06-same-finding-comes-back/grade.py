def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "marks the unfixed <li> finding as a repeat", t.findings(r"li|literal|count|element", must_fix=True, repeat=True)
    yield "does not mark the fixed date finding as a repeat", not t.findings(r"skip|pars|malformed|newest|order", repeat=True)
    yield "posted its review on PR #9", [e for e in t.posted("pr comment") if e["number"] == 9]
