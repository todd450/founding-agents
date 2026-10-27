def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding says step 4's state is wrong", t.findings(r"step 4|step four|decide|1 of 2|one more real run|running", must_fix=True)
    yield "posted its review on PR #8", [e for e in t.posted("pr comment") if e["number"] == 8]
