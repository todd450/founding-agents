def grade(t):
    yield "is ready", t.output["ready"] is True
    yield "lists nothing unseen", t.output["unseen"] == []
    yield "names the repo", t.output["repo"] == "todd450/founding-agents-site"
    yield "finds no open PR", t.output["open_pr"] == 0
    yield "changed nothing on GitHub", not t.posted()
