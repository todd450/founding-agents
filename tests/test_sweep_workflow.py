"""The sweep workflow runs one finder, files its findings as issues and puts them to the founder in one queue item."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

CHECKED = {"repo": "o/site", "public": False, "red": [], "open": []}
PUBLIC = {**CHECKED, "public": True}


def finding(title, severity="", decisions=()):
    return {"title": title, "problem": f"{title} costs every page load.", "evidence": "`du -k styles.css`: 120 KB",
            "fix": "Drop the unused rules.", "size": "an hour", "leave": "slower pages on phones",
            "severity": severity, "pass_marks": ["styles.css is under 40 KB with the same command"],
            "decisions": list(decisions)}


FOUND = {"findings": [finding("Unused CSS"), finding("Two colour lists")],
         "measured": "page weight and check.sh time", "not_reviewed": "the deploy script"}
FILED = {"issues": [{"number": 31, "advisory_url": "", "error": ""}, {"number": 32, "advisory_url": "", "error": ""}]}
QUEUE = {"number": 33, "url": "https://github.com/o/site/issues/33"}
DOOR = {"decision": "Add a CSS linter", "options": ["stylelint", "none"], "recommend": "stylelint",
        "why": "It catches unused rules on every PR.", "reverse": "an hour"}


def replies(**over):
    base = {"check": [CHECKED], "optimiser": [FOUND], "test-auditor": [FOUND], "security-reviewer": [FOUND],
            "file findings": [FILED], "queue item": [QUEUE]}
    return {**base, **over}


@unittest.skipUnless(HAVE_NODE, "needs node")
class SweepWorkflowTest(unittest.TestCase):
    def call(self, run, label):
        [call] = [call for call in run["calls"] if call["label"] == label]
        return call

    def test_each_kind_runs_its_own_finder_read_only_in_a_worktree_on_opus(self):
        for kind, agent in (("codebase", "optimiser"), ("tests", "test-auditor"), ("security", "security-reviewer")):
            run = run_workflow("sweep", replies(), kind)
            finder = self.call(run, agent)
            self.assertEqual((finder["agentType"], finder["isolation"], finder["model"]),
                             (f"founding-agents:{agent}", "worktree", "opus"))
            self.assertIn("Post nothing and file nothing", finder["prompt"])

    def test_each_kind_asks_for_its_own_pass_marks(self):
        self.assertIn("no test changed to make it pass", self.call(run_workflow("sweep", replies(), "codebase"), "optimiser")["prompt"])
        self.assertIn("plants the kind of fault", self.call(run_workflow("sweep", replies(), "tests"), "test-auditor")["prompt"])
        self.assertIn("reproduces the exploit, fails before the fix",
                      self.call(run_workflow("sweep", replies(), "security"), "security-reviewer")["prompt"])

    def test_the_finder_is_told_most_fixes_settle_no_technical_decision(self):
        prompt = self.call(run_workflow("sweep", replies(), "codebase"), "optimiser")["prompt"]
        self.assertIn("Most fixes settle none", prompt)
        self.assertIn("an option you advise against does not make the choice a one-way door", prompt)

    def test_an_unknown_kind_is_an_error(self):
        self.assertIn("Name what to sweep", run_workflow("sweep", replies(), "speed")["error"])

    def test_an_open_red_issue_stops_the_sweep_before_the_finder(self):
        run = run_workflow("sweep", replies(check=[{**CHECKED, "red": ["#9 Site check failed"]}]), "codebase")
        self.assertEqual(run["result"]["status"], "not started")
        self.assertIn("#9 Site check failed", run["result"]["reason"])
        self.assertEqual([call["label"] for call in run["calls"]], ["check"])

    def test_the_finder_is_told_to_leave_out_what_open_sweep_issues_cover(self):
        run = run_workflow("sweep", replies(check=[{**CHECKED, "open": ["#20 Unused CSS"]}]), "codebase")
        self.assertIn("- #20 Unused CSS", self.call(run, "optimiser")["prompt"])

    def test_each_finding_is_filed_with_its_evidence_pass_marks_and_decisions(self):
        found = {**FOUND, "findings": [finding("Unused CSS", decisions=[DOOR]), finding("Two colour lists")]}
        prompt = self.call(run_workflow("sweep", replies(optimiser=[found]), "codebase"), "file findings")["prompt"]
        self.assertIn("gh label create sweep", prompt)
        self.assertIn("Title: Unused CSS", prompt)
        self.assertIn("**Evidence:** `du -k styles.css`: 120 KB", prompt)
        self.assertIn("### Pass marks\n\n- styles.css is under 40 KB with the same command", prompt)
        self.assertIn("**D1. Add a CSS linter:** stylelint / none. Recommended: **stylelint**", prompt)
        self.assertIn("None. The fix changes nothing", prompt)

    def test_the_queue_item_lists_each_filed_finding_and_how_to_decide(self):
        run = run_workflow("sweep", replies(), "codebase")
        item = self.call(run, "queue item")["prompt"]
        self.assertIn("--label needs-founder", item)
        self.assertIn("which of these 2 findings to fix", item)
        self.assertIn("### A. #31 Unused CSS", item)
        self.assertIn("### B. #32 Two colour lists", item)
        self.assertIn("**Not reviewed:** the deploy script", item)
        self.assertIn("add the `decided` label to each issue you want fixed, then run `/founding-agents:build <number>`", item)
        self.assertEqual(run["result"]["findings"], [31, 32])
        self.assertEqual(run["result"]["queue_item"], QUEUE["url"])

    def test_a_finding_with_a_decision_asks_for_the_founders_choice_first(self):
        found = {**FOUND, "findings": [finding("Unused CSS", decisions=[DOOR])]}
        filed = {"issues": [FILED["issues"][0]]}
        item = self.call(run_workflow("sweep", replies(optimiser=[found], **{"file findings": [filed]}), "codebase"),
                         "queue item")["prompt"]
        self.assertIn("Settles 1 technical decision, listed on #31", item)
        self.assertIn("after replying on it with your choice for each technical decision", item)

    def test_the_report_goes_on_the_queue_item(self):
        run = run_workflow("sweep", replies(), "codebase")
        self.assertEqual([call["label"] for call in run["calls"]][-2:], ["tidy worktrees", "run report"])
        self.assertIn("--workflow sweep --issue 33 --budget 5 --post", run["calls"][-1]["prompt"])

    def test_nothing_found_files_nothing(self):
        run = run_workflow("sweep", replies(optimiser=[{**FOUND, "findings": []}]), "codebase")
        self.assertEqual(run["result"]["status"], "nothing worth fixing")
        self.assertEqual([call["label"] for call in run["calls"]], ["check", "optimiser", "tidy worktrees"])

    def test_findings_that_could_not_be_filed_post_no_queue_item(self):
        failed = {"issues": [{"number": 0, "advisory_url": "", "error": "no admin rights"}] * 2}
        run = run_workflow("sweep", replies(**{"file findings": [failed]}), "codebase")
        self.assertEqual(run["result"]["status"], "not filed")
        self.assertNotIn("queue item", [call["label"] for call in run["calls"]])


@unittest.skipUnless(HAVE_NODE, "needs node")
class PublicSecuritySweepTest(unittest.TestCase):
    def setUp(self):
        found = {**FOUND, "findings": [finding("Notes readable by any signed-in user", severity="high")],
                 "measured": "tried GET /api/notes/2 as user 1"}
        filed = {"issues": [{"number": 31, "advisory_url": "https://github.com/o/site/security/advisories/GHSA-1", "error": ""}]}
        self.run_ = run_workflow("sweep", replies(check=[PUBLIC], **{"security-reviewer": [found], "file findings": [filed]}),
                                 "security")
        self.calls = {call["label"]: call["prompt"] for call in self.run_["calls"]}

    def test_details_go_in_a_draft_advisory_and_the_issue_carries_only_a_summary(self):
        prompt = self.calls["file findings"]
        self.assertIn("security-advisories --method POST", prompt)
        advisory = json.loads(prompt.split("giving it exactly this JSON:\n")[1].split("\n")[0])
        self.assertEqual((advisory["summary"], advisory["severity"]), ("Notes readable by any signed-in user", "high"))
        self.assertIn("do not file the issue", prompt)
        issue = prompt.split("Body:\n")[1]
        self.assertIn("Title: Security finding A: high severity, details in a private advisory", prompt)
        self.assertNotIn("Notes readable", issue)
        self.assertNotIn("api/notes", issue)
        self.assertIn("Keep the details out of this issue", issue)

    def test_the_queue_item_reveals_nothing_either(self):
        item = self.calls["queue item"]
        self.assertIn("### A. #31: high severity", item)
        self.assertIn("[the private advisory](https://github.com/o/site/security/advisories/GHSA-1)", item)
        self.assertNotIn("Notes readable", item)
        self.assertNotIn("api/notes", item)

    def test_a_private_repo_files_security_findings_in_the_open(self):
        run = run_workflow("sweep", replies(), "security")
        prompt = self.call_prompt(run, "file findings")
        self.assertNotIn("security-advisories", prompt)
        self.assertIn("Title: Unused CSS", prompt)

    def call_prompt(self, run, label):
        return next(call["prompt"] for call in run["calls"] if call["label"] == label)


if __name__ == "__main__":
    unittest.main()
