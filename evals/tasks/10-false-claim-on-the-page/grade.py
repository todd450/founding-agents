def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding says the record's claim about the tests is false", t.findings(
        r"link|name|claim|false|untrue|not true|inaccurate|incorrect", must_fix=True)
    yield "posted its review on PR #11", [e for e in t.posted("pr comment") if e["number"] == 11]
