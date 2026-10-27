def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding is about the test's network call", t.findings(
        r"network|urlopen|urllib|api\.github|live|internet|offline|rate.?limit", must_fix=True)
    yield "posted its review on PR #8", [e for e in t.posted("pr comment") if e["number"] == 8]
