def grade(t):
    yield "approves the change", t.output["verdict"] == "approve"
    yield "raises no must-fix finding", not t.findings(must_fix=True)
    yield "posted its review on PR #16", [e for e in t.posted("pr comment") if e["number"] == 16]
