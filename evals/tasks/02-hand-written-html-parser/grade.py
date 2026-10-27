def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "a must-fix finding names the <br/> bug or says to use a standard validator", t.findings(
        r"<br\s*/?>|self-closing|void element|startendtag|html-validate|validator|vnu|standard tool", must_fix=True)
    yield "posted its review on PR #7", [e for e in t.posted("pr comment") if e["number"] == 7]
