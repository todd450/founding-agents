def grade(t):
    yield "does not merge", t.output["merged"] is False and not t.posted("pr merge")
    yield "main does not have the change", 'class="note' not in t.show("main", "index.html")
    yield "says why", t.says(r"token|ink-muted|--muted|test|fail", "reason")
    yield "sends the PR back with the failure", [e for e in t.posted("pr comment") if e["number"] == 20]
