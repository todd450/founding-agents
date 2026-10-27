LI = r"<li>|\bli\b|literal|count|element|attribute"


def grade(t):
    yield "sends the change back", t.output["verdict"] == "changes"
    yield "marks the unfixed <li> finding as a repeat", t.findings(LI, must_fix=True, repeat=True)
    # The date finding was fixed: every finding marked a repeat must be the <li> one.
    yield "marks nothing else as a repeat", len(t.findings(LI, repeat=True)) == len(t.findings(repeat=True))
    yield "posted its review on PR #9", [e for e in t.posted("pr comment") if e["number"] == 9]
