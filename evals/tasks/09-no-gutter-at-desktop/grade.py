def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding is about the missing gutter at desktop width", t.findings(
        r"gutter|first column|step 1|touch|no (space|gap)|zero gap|flush|abut|butt|collid|overlap|cramped|run(s)? into|padding", must_fix=True)
    yield "posted its review on PR #8", [e for e in t.posted("pr comment") if e["number"] == 8]
