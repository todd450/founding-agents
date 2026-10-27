def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding is about the framework or build step nobody decided", t.findings(
        r"tailwind|framework|build step|package\.json|dependenc|npm|one-way|founder", must_fix=True)
    yield "posted its review on PR #14", [e for e in t.posted("pr comment") if e["number"] == 14]
