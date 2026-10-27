"""The propose workflow ends in one queue item: the brief's recommendation, the options and how to decide."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

GO = {"repo": "o/site", "issue": 7, "recommend": "go", "reason": "two founders asked for it", "overruled": False,
      "screens": True, "decisions": []}
NO_GO = {**GO, "recommend": "no-go", "reason": "no evidence anyone wants it yet"}


def option(letter, stars):
    base = f"mockups/issue-7/{letter.lower()}"
    return {"letter": letter, "name": f"Option {letter}", "stars": stars, "what": f"{letter} at the key moment.",
            "cost": f"{stars} days", "html": f"{base}.html", "phone": f"{base}-phone.png",
            "desktop": f"{base}-desktop.png"}


DESIGN = {"branch": "propose/issue-7", "stopped_because": "", "recommended": "B", "options": [option("A", 3), option("B", 6)]}
POSTED = {"comment_url": "https://github.com/o/site/issues/7#issuecomment-1"}


DOOR = {"decision": "How the site deploys", "options": ["GitHub Pages", "Netlify"], "recommend": "GitHub Pages",
        "why": "It already serves the site.", "reverse": "an hour while it is one page"}
BUILT = {**GO, "screens": False, "decisions": [DOOR]}


@unittest.skipUnless(HAVE_NODE, "needs node")
class ProposeWorkflowTest(unittest.TestCase):
    def queue_item(self, run):
        [call] = [call for call in run["calls"] if call["label"] == "queue item"]
        return call["prompt"]

    def test_an_issue_number_is_shaped_in_place(self):
        run = run_workflow("propose", {"product lead": [GO], "designer": [DESIGN], "queue": [POSTED]}, 7)
        self.assertIn("Shape issue #7", run["calls"][0]["prompt"])
        self.assertEqual(run["result"]["queue_item"], POSTED["comment_url"])

    def test_an_idea_in_words_becomes_a_new_issue(self):
        run = run_workflow("propose", {"product lead": [GO], "designer": [DESIGN], "queue": [POSTED]},
                           "a pricing page")
        prompt = run["calls"][0]["prompt"]
        self.assertIn("open it as a new issue", prompt)
        self.assertIn("a pricing page", prompt)

    def test_each_role_runs_as_its_plugin_agent_and_the_designer_in_a_worktree(self):
        run = run_workflow("propose", {"product lead": [GO], "designer": [DESIGN], "queue": [POSTED]}, 7)
        lead, designer, queue = run["calls"][:3]
        self.assertEqual((lead["agentType"], lead["model"]), ("founding-agents:product-lead", "opus"))
        self.assertEqual((designer["agentType"], designer["isolation"]), ("founding-agents:designer", "worktree"))
        self.assertEqual(queue["model"], "haiku")

    def test_the_queue_item_shows_every_option_with_screenshots_cost_and_the_pick(self):
        item = self.queue_item(run_workflow("propose", {"product lead": [GO], "designer": [DESIGN], "queue": [POSTED]}, 7))
        self.assertIn("recommends **go**: two founders asked for it", item)
        self.assertIn("### A. Option A: 3 stars", item)
        self.assertIn("### B. Option B (recommended): 6 stars", item)
        self.assertIn("https://github.com/o/site/blob/propose/issue-7/mockups/issue-7/b-phone.png?raw=true", item)
        self.assertIn("**Cost:** 6 days", item)
        self.assertIn("add the `decided` label", item)
        self.assertIn("/founding-agents:build 7", item)

    def test_a_no_go_skips_the_designer_and_still_reaches_the_founder(self):
        run = run_workflow("propose", {"product lead": [NO_GO], "queue": [POSTED]}, 7)
        self.assertEqual([call["label"] for call in run["calls"]], ["product lead", "queue item", "tidy worktrees", "run report"])
        item = self.queue_item(run)
        self.assertIn("recommends **no-go**", item)
        self.assertIn("close the issue", item)
        self.assertEqual(run["result"]["options"], [])

    def test_an_overruled_no_go_gets_mockups_and_keeps_the_honest_recommendation(self):
        run = run_workflow("propose", {"product lead": [{**NO_GO, "overruled": True}], "designer": [DESIGN],
                                       "queue": [POSTED]}, 7)
        self.assertEqual([call["label"] for call in run["calls"]], ["product lead", "designer", "queue item", "tidy worktrees", "run report"])
        item = self.queue_item(run)
        self.assertIn("recommends **no-go**", item)
        self.assertIn("You overruled the no-go", item)
        self.assertIn("### B. Option B (recommended)", item)

    def test_a_designer_that_stops_posts_no_queue_item(self):
        stopped = {**DESIGN, "stopped_because": "Chrome is missing", "options": []}
        run = run_workflow("propose", {"product lead": [GO], "designer": [stopped], "queue": [POSTED]}, 7)
        self.assertEqual(run["result"]["status"], "stopped in design")
        self.assertEqual(run["result"]["reason"], "Chrome is missing")
        self.assertNotIn("queue item", [call["label"] for call in run["calls"]])

    def test_the_report_goes_on_the_issue_the_product_lead_shaped(self):
        run = run_workflow("propose", {"product lead": [GO], "designer": [DESIGN], "queue": [POSTED]}, "a pricing page")
        self.assertIn("--workflow propose --issue 7 --budget 5 --post", run["calls"][-1]["prompt"])

    def test_the_queue_item_lists_each_technical_decision_for_the_founder(self):
        door = {"decision": "How the site is built", "options": ["plain HTML", "a static site generator"],
                "recommend": "plain HTML", "why": "One page needs nothing more.", "reverse": "half a day while it is one page"}
        item = self.queue_item(run_workflow("propose", {"product lead": [{**GO, "decisions": [door]}], "designer": [DESIGN],
                                                        "queue": [POSTED]}, 7))
        self.assertIn("### Technical decisions", item)
        self.assertIn("**D1. How the site is built:** plain HTML / a static site generator. Recommended: **plain HTML**", item)
        self.assertIn("Reversing it later: half a day while it is one page", item)
        self.assertIn("your choice for each technical decision (D1)", item)

    def test_a_brief_that_settles_no_technical_decision_says_so(self):
        item = self.queue_item(run_workflow("propose", {"product lead": [GO], "designer": [DESIGN], "queue": [POSTED]}, 7))
        self.assertIn("**Technical decisions:** none.", item)
        self.assertNotIn("each technical decision", item)

    def test_the_product_lead_is_asked_to_name_decisions_including_ones_taken_for_granted(self):
        prompt = run_workflow("propose", {"product lead": [NO_GO], "queue": [POSTED]}, 7)["calls"][0]["prompt"]
        self.assertIn('"Technical decisions"', prompt)
        self.assertIn('"a static site"', prompt)

    def test_a_brief_with_nothing_on_screen_skips_the_designer_and_asks_only_the_decisions(self):
        run = run_workflow("propose", {"product lead": [BUILT], "queue": [POSTED]}, 7)
        self.assertEqual([call["label"] for call in run["calls"]], ["product lead", "queue item", "tidy worktrees", "run report"])
        item = self.queue_item(run)
        self.assertIn("**D1. How the site deploys:** GitHub Pages / Netlify", item)
        self.assertIn("reply with your choice for each technical decision (D1) and any notes, then add the `decided` label", item)
        self.assertNotIn("which option", item)
        self.assertNotIn("again for mockups", item)

    def test_an_overruled_no_go_with_nothing_on_screen_is_decided_without_mockups(self):
        run = run_workflow("propose", {"product lead": [{**BUILT, "recommend": "no-go", "overruled": True}],
                                       "queue": [POSTED]}, 7)
        self.assertNotIn("designer", [call["label"] for call in run["calls"]])
        item = self.queue_item(run)
        self.assertIn("say so in a reply with your choice for each technical decision (D1), then add the `decided` label", item)

    def test_the_queue_item_adds_the_needs_founder_label(self):
        item = self.queue_item(run_workflow("propose", {"product lead": [NO_GO], "queue": [POSTED]}, 7))
        self.assertIn("--add-label needs-founder", item)

    def test_nothing_to_propose_is_an_error(self):
        self.assertIn("Name an issue", run_workflow("propose", {}, None)["error"])


if __name__ == "__main__":
    unittest.main()
