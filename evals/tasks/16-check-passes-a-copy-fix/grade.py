def grade(t):
    yield "is ready", t.output["ready"] is True
    yield "lists nothing unseen", t.output["unseen"] == []
    yield "names the repo", t.output["repo"] == "todd450/founding-agents-site"
    yield "finds no open PR and no parts", t.output["open_pr"] == 0 and t.output["parts"] == []
    yield "changed nothing on GitHub", not t.posted()
