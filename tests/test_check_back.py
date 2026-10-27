"""The check-back finds each shipped brief when it is due, posts one shape, and counts what worked."""

import io
import json
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SETUP = Path(__file__).resolve().parent.parent / "skills" / "setup"
sys.path.insert(0, str(SETUP / "ops_watch"))
from check_back import MARK, main, pages, promise, score, survey, window  # noqa: E402

REPO = "owner/product"
NOW = datetime(2026, 11, 20, 9, tzinfo=timezone.utc)


def stamp(days_ago):
    return (NOW - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def brief(number, *, know="Sign-ups from the home page rise from 2 to 10 a week.", extra="", **fields):
    body = f"## Decision\nGo.\n\n## How we'll know it worked\n{know}\n{extra}\n## Rabbit holes\nNone."
    return {"number": number, "title": f"Brief: idea {number}", "body": body, "state": "open",
            "state_reason": None, "closed_at": None, "labels": [{"name": "decided"}], **fields}


def part(number, of, closed_days_ago=None, reason="completed"):
    closed = closed_days_ago is not None
    return {"number": number, "title": f"Part {number}", "body": f"Part of #{of}\n\nBuild it.",
            "state": "closed" if closed else "open", "state_reason": reason if closed else None,
            "closed_at": stamp(closed_days_ago) if closed else None, "labels": []}


def check_back(days_ago, verdict):
    return {"created_at": stamp(days_ago), "body": f"{MARK} on this brief.\n\n**Verdict:** {verdict}\n"}


class FakeGh:
    """Answers `gh api` for a repo's issues, each issue's comments and the posts the script makes."""

    def __init__(self, issues, comments=None):
        self.issues = issues
        self.comments = comments or {}
        self.calls = []
        self.posted = []

    def __call__(self, *args, input=None):
        self.calls.append(args)
        path = next(a for a in args if a.startswith("repos/"))
        fields = dict(args[i + 1].split("=", 1) for i, a in enumerate(args) if a == "-f")
        if "POST" in args:
            self.posted.append((path, fields))
            return 0, json.dumps({"number": 99, "html_url": f"https://github.com/{path}/1"}), ""
        if path.startswith(f"repos/{REPO}/issues?"):
            # Two pages, as `gh api --paginate` prints them.
            half = len(self.issues) // 2
            return 0, json.dumps(self.issues[:half]) + "\n" + json.dumps(self.issues[half:]), ""
        number = int(path.split("/")[4])
        return 0, json.dumps(self.comments.get(number, [])), ""


def run(fake, *argv, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        code = main(["--repo", REPO, *argv], gh=fake, now=NOW, stdin=io.StringIO(stdin))
    finally:
        sys.stdout, sys.stderr = old
    return code, out.getvalue(), err.getvalue()


class BriefTest(unittest.TestCase):
    def test_reads_the_how_well_know_section_up_to_the_next_heading(self):
        section = promise(brief(1)["body"])
        self.assertTrue(section.startswith("## How we'll know it worked"))
        self.assertIn("rise from 2 to 10", section)
        self.assertNotIn("Rabbit holes", section)

    def test_an_issue_without_the_section_is_not_a_brief(self):
        self.assertIsNone(promise("Fix the footer link."))

    def test_waits_as_long_as_the_brief_says_and_two_weeks_when_it_says_nothing(self):
        self.assertEqual(window("Check back: 3 weeks after it ships"), timedelta(weeks=3))
        self.assertEqual(window("check back in 10 days"), timedelta(days=10))
        self.assertEqual(window("Sign-ups rise."), timedelta(days=14))

    def test_the_product_leads_example_is_one_the_script_reads(self):
        # The product lead writes when to check back; a wording the script cannot read falls back
        # to two weeks without a word, so the agent's example is held to the script's pattern.
        lead = (SETUP.parent.parent / "agents" / "product-lead.md").read_text()
        example = re.search(r'"(Check back: [^"]+)"', lead).group(1)
        self.assertEqual(window(example), timedelta(weeks=3))

    def test_reads_every_page_gh_prints(self):
        self.assertEqual(pages('[1, 2]\n[3]\n'), [1, 2, 3])


class DueTest(unittest.TestCase):
    def statuses(self, issues, comments=None):
        return {s["number"]: s for s in survey(REPO, NOW, FakeGh(issues, comments))}

    def test_a_brief_is_due_two_weeks_after_its_last_issue_closes(self):
        found = self.statuses([brief(1), part(2, 1, 20), part(3, 1, 15)])
        self.assertEqual(found[1]["shipped"], NOW - timedelta(days=15))
        self.assertTrue(found[1]["due"])
        self.assertEqual(found[1]["parts"], [2, 3])

    def test_not_due_before_the_window_the_brief_names(self):
        found = self.statuses([brief(1, extra="Check back: 3 weeks"), part(2, 1, 15)])
        self.assertFalse(found[1]["due"])

    def test_a_brief_with_an_issue_still_open_has_not_shipped(self):
        self.assertEqual(self.statuses([brief(1), part(2, 1, 30), part(3, 1)]), {})

    def test_an_issue_closed_as_not_planned_ships_nothing(self):
        found = self.statuses([brief(1), part(2, 1, 30), part(3, 1, 5, reason="not_planned")])
        self.assertEqual(found[1]["shipped"], NOW - timedelta(days=30))
        self.assertEqual(self.statuses([brief(1), part(2, 1, 30, reason="not_planned")]), {})

    def test_a_brief_built_on_its_own_ships_when_it_closes_with_decided(self):
        built = brief(1, state="closed", state_reason="completed", closed_at=stamp(20))
        self.assertTrue(self.statuses([built])[1]["due"])

    def test_a_brief_the_founder_said_no_to_never_ships(self):
        # The founder says no by closing the brief, which GitHub records as completed by default.
        refused = brief(1, state="closed", state_reason="completed", closed_at=stamp(20), labels=[])
        self.assertEqual(self.statuses([refused]), {})

    def test_a_verdict_settles_it_and_cant_tell_is_checked_again_a_window_later(self):
        issues = [brief(1), part(2, 1, 40), brief(3), part(4, 3, 40), brief(5), part(6, 5, 40)]
        found = self.statuses(issues, {1: [check_back(20, "worked")],
                                       3: [check_back(10, "can't tell yet")],
                                       5: [check_back(20, "can't tell yet")]})
        self.assertFalse(found[1]["due"])
        self.assertFalse(found[3]["due"])
        self.assertTrue(found[5]["due"])
        self.assertEqual(found[5]["checks"], 1)

    def test_stops_after_three_check_backs_that_could_not_tell(self):
        found = self.statuses([brief(1), part(2, 1, 90)], {1: [check_back(d, "can't tell yet") for d in (60, 40, 20)]})
        self.assertFalse(found[1]["due"])

    def test_every_call_is_rest_inside_the_repo(self):
        # A routine's cloud proxy blocks GraphQL and every path outside the routine's own repo.
        fake = FakeGh([brief(1), part(2, 1, 20)])
        run(fake, "post", "1", stdin=json.dumps({"verdict": "didnt", "happened": "No sign-ups.",
                                                  "recommend": "remove", "why": "Nobody used it."}))
        for call in fake.calls:
            self.assertEqual(call[0], "api")
            self.assertTrue(next(a for a in call if a.startswith("repos/")).startswith(f"repos/{REPO}/"), call)


class PostTest(unittest.TestCase):
    def test_worked_posts_what_we_said_what_happened_and_the_verdict(self):
        fake = FakeGh([brief(1), part(2, 1, 20)])
        code, out, _ = run(fake, "post", "1", stdin=json.dumps({"verdict": "worked", "happened": "12 a week (metrics.md, 18 Nov)."}))
        self.assertEqual(code, 0)
        [(path, fields)] = fake.posted
        self.assertEqual(path, f"repos/{REPO}/issues/1/comments")
        body = fields["body"]
        self.assertTrue(body.startswith(MARK))
        self.assertIn("> Sign-ups from the home page rise from 2 to 10 a week.", body)
        self.assertIn("**What happened:** 12 a week (metrics.md, 18 Nov).", body)
        self.assertIn("**Verdict:** worked", body)
        self.assertIn("1 of 1 with a verdict (100%)", body)

    def test_didnt_opens_a_needs_founder_item_asking_keep_change_or_remove(self):
        fake = FakeGh([brief(1), part(2, 1, 20)])
        run(fake, "post", "1", stdin=json.dumps({"verdict": "didnt", "happened": "Still 2 a week.",
                                                  "recommend": "remove", "why": "Nobody used it."}))
        (item_path, item), (comment_path, comment) = fake.posted
        self.assertEqual(item_path, f"repos/{REPO}/issues")
        self.assertEqual(item["labels[]"], "needs-founder")
        self.assertEqual(item["title"], "Check-back: #1 idea 1 did not do what it said")
        for words in ("keep, change or remove", "recommends **remove**: Nobody used it.", "Still 2 a week."):
            self.assertIn(words, item["body"])
        self.assertIn("**Verdict:** didn't", comment["body"])
        self.assertIn("#99", comment["body"])

    def test_didnt_needs_a_recommendation(self):
        fake = FakeGh([brief(1), part(2, 1, 20)])
        code, _, err = run(fake, "post", "1", stdin=json.dumps({"verdict": "didnt", "happened": "Still 2."}))
        self.assertEqual(code, 1)
        self.assertIn("recommendation", err)
        self.assertEqual(fake.posted, [])

    def test_cant_tell_says_when_it_looks_again_and_the_third_says_it_is_the_last(self):
        fake = FakeGh([brief(1), part(2, 1, 20)])
        run(fake, "post", "1", stdin=json.dumps({"verdict": "cant-tell", "happened": "No data."}))
        self.assertIn("Next check-back: 04 Dec 2026.", fake.posted[0][1]["body"])

        fake = FakeGh([brief(1), part(2, 1, 90)], {1: [check_back(d, "can't tell yet") for d in (60, 30)]})
        run(fake, "post", "1", stdin=json.dumps({"verdict": "cant-tell", "happened": "No data."}))
        body = fake.posted[0][1]["body"]
        self.assertIn("3 of at most 3", body)
        self.assertIn("This is the last check-back", body)
        self.assertNotIn("Next check-back", body)

    def test_refuses_a_brief_that_is_not_due(self):
        fake = FakeGh([brief(1), part(2, 1, 3)])
        code, _, err = run(fake, "post", "1", stdin=json.dumps({"verdict": "worked", "happened": "Up."}))
        self.assertEqual(code, 1)
        self.assertIn("no check-back due", err)
        self.assertEqual(fake.posted, [])


class ScoreTest(unittest.TestCase):
    def test_the_share_that_worked_counts_only_briefs_with_a_verdict(self):
        statuses = [{"verdict": v} for v in ("worked", "worked", "didn't", "can't tell yet", None)]
        self.assertEqual(score(statuses), "Shipped briefs that did what they said: 2 of 3 with a verdict "
                                          "(67%); 2 more can't tell yet or are not due.")

    def test_says_so_when_nothing_has_a_verdict(self):
        self.assertIn("none has a verdict yet", score([{"verdict": None}]))

    def test_due_lists_each_brief_with_what_it_said_then_the_score(self):
        code, out, _ = run(FakeGh([brief(1), part(2, 1, 20), brief(3), part(4, 3, 2)]), "due")
        self.assertEqual(code, 0)
        self.assertIn("## #1 Brief: idea 1", out)
        self.assertIn("issues cut from it: #2", out)
        self.assertNotIn("#3", out)
        self.assertTrue(out.strip().endswith("2 more can't tell yet or are not due."))


if __name__ == "__main__":
    unittest.main()
