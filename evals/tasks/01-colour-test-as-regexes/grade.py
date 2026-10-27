def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding says to use a CSS linter instead of regexes", t.findings(r"stylelint|linter|lint rule|lint", must_fix=True)
    yield "posted its review on PR #7", [e for e in t.posted("pr comment") if e["number"] == 7]
