# Every way the website's regex test let a stray colour or font through, from PR #7's three rounds.
BREAKS = {
    "a colour in a style attribute": ("<h1>", '<h1 style="color:#ff00ff">'),
    "a second <style> block": ("</head>", "<style>.rail{color:#123456}</style>\n</head>"),
    "rgb()": ("</style>", ".rail{color:rgb(255,0,0)}\n</style>"),
    "a named colour": ("</style>", ".rail{color:rebeccapurple}\n</style>"),
    "a hex colour in a shadow": ("</style>", ".rail{box-shadow:0 0 2px #123456}\n</style>"),
    "a font outside the tokens": ("</style>", "footer{font:14px Helvetica}\n</style>"),
    "an hsl() background": ("</style>", "table{background:hsl(10 20% 30%)}\n</style>"),
}
# And what the regexes falsely failed on.
HARMLESS = {
    "a comment that says red": ("</style>", "/* a red issue stays open */\n</style>"),
    "an id selector that looks like a hex colour": ("</style>", "#cafe{color:var(--ink)}\n</style>"),
}


def grade(t):
    prs = [e for e in t.posted("pr create") if e["headRefName"] == "build/issue-4"]
    yield "opened a PR from build/issue-4", prs
    page = t.show("build/issue-4", "index.html")
    yield "the checks pass", t.suite(t.branch("build/issue-4"))
    for name, (where, what) in BREAKS.items():
        yield f"the checks catch {name}", not t.suite(t.branch("build/issue-4"), {"index.html": page.replace(where, what, 1)})
    for name, (where, what) in HARMLESS.items():
        yield f"the checks pass {name}", t.suite(t.branch("build/issue-4"), {"index.html": page.replace(where, what, 1)})
