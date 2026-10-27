import re

PINNED = r"['\"][^'\"]*\b(four|4) (rounds|reviews)\b[^'\"]*['\"]"


def grade(t):
    prs = [e for e in t.posted("pr create") if e["headRefName"] == "build/issue-26"]
    yield "opened a PR from build/issue-26", prs
    record = re.search(r'aria-labelledby="record">(.*?)</section>', t.show("build/issue-26", "index.html"), re.S).group(1)
    shell = " ".join(line for line in record.split("</li>") if "shell" in line.lower())
    yield "the record says the shell took four rounds", re.search(r"\b(four|4)\b[^.]*round", shell, re.I)
    yield "the record no longer says three", not re.search(r"\b(three|3) rounds", shell, re.I)
    checkout = t.branch("build/issue-26")
    yield "the checks pass", t.suite(checkout)
    yield "no test pins the record's wording", not any(re.search(PINNED, p.read_text(), re.I) for p in (checkout / "tests").rglob("*.py"))
