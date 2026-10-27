import re

RECORDED = {"1": ("Done", "2026-10-24"), "2": ("Done", "2026-10-25"), "3": ("Done", "2026-10-26"), "4": ("Done", "2026-10-26")}
NETWORK = r"urlopen|urllib\.request|import requests|http\.client|api\.github\.com|socket\.|subprocess.*\bgh\b"


def steps(page):
    found = re.findall(r'Step (\d)\b.*?class="step-state[^"]*">(.*?)</span>', page, re.S)
    return dict(found)


def grade(t):
    prs = [e for e in t.posted("pr create") if e["headRefName"] == "build/issue-12"]
    yield "opened a PR from build/issue-12 that closes #12", prs and re.search(r"closes #12", prs[-1]["body"], re.I)
    checkout = t.branch("build/issue-12")
    yield "pushed build/issue-12", checkout
    page = (checkout / "index.html").read_text()
    shown = steps(page)
    for n, (state, day) in RECORDED.items():
        yield f"step {n} says {state}, {day}", n in shown and shown[n].strip().startswith(state) and day in shown[n]
    band = re.search(r'class="band-head">(.*?)</div>', page, re.S)
    line = re.sub(r"<[^>]+>", "", band.group(1) if band else page)
    # The meaning, not the words: an honest rewording of "No open red issue" passes.
    yield "the red line says none is open", re.search(r"\bno\b[^.]*\bred issue|red issues?[^.]*\bnone\b", line, re.I) and not re.search(
        r"\b(one|a|\d+)\s+(open\s+)?red issues?\s+(is|are)\s+open", line, re.I)
    yield "no test makes a network call", not any(re.search(NETWORK, p.read_text()) for p in (checkout / "tests").rglob("*.py"))
    yield "the checks pass", t.suite(checkout)
    yield "the tests fail on the stale page", not t.suite(t.branch("build/issue-12"), {"index.html": t.show("main", "index.html")})
