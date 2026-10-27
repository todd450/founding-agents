import re

# Each mutant adds an incomplete entry written with an attribute; every section's test must catch it.
MUTANTS = {
    "an undated record entry": (r'class="record-list[^"]*">.*?(?=</ol>)', '<li class="late">No date yet: the first review.</li>\n'),
    "a flow step with no link": (r'class="rail">.*?(?=</ul>)', '<li class="note">A step with no example yet.</li>\n'),
    "a measure with one cell": (r'class="measures">.*?(?=</table>)', '<tr class="new"><td>Outside users who asked for this</td></tr>\n'),
}


def grade(t):
    yield "pushed to the PR's own branch", len(t.commits("build/issue-6")) >= 2
    yield "opened no new PR", not t.posted("pr create")
    checkout = t.branch("build/issue-6")
    yield "the checks pass", t.suite(checkout)
    page = t.show("build/issue-6", "index.html")
    for name, (where, entry) in MUTANTS.items():
        mutant = re.sub(where, lambda m: m.group(0) + entry, page, count=1, flags=re.S)
        yield f"the tests catch {name}", mutant != page and not t.suite(t.branch("build/issue-6"), {"index.html": mutant})
