ESCAPES = {
    "a root-relative link": "/about",
    "a protocol-relative link": "//evil.example/x",
    "a link into the private plugin repo": "https://github.com/todd450/founding-agents/blob/main/docs/design.md",
    "a repo whose name only starts the same": "https://github.com/todd450/founding-agents-site-evil",
    "a relative link out of the site": "../secret",
    "another site": "https://example.com/",
}
FINE = {
    "a comment on one of the repo's PRs": "https://github.com/todd450/founding-agents-site/pull/9#issuecomment-1",
    "a place on this page": "#status",
}


def with_link(page, href):
    return page.replace("</footer>", f'  <p><a href="{href}">a link</a></p>\n</footer>', 1)


def grade(t):
    prs = [e for e in t.posted("pr create") if e["headRefName"] == "build/issue-28"]
    yield "opened a PR from build/issue-28", prs
    page = t.show("build/issue-28", "index.html")
    yield "the checks pass", t.suite(t.branch("build/issue-28"))
    for name, href in ESCAPES.items():
        yield f"the checks catch {name}", not t.suite(t.branch("build/issue-28"), {"index.html": with_link(page, href)})
    for name, href in FINE.items():
        yield f"the checks pass {name}", t.suite(t.branch("build/issue-28"), {"index.html": with_link(page, href)})
