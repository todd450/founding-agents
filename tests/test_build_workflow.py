"""The build workflow checks the ticket, loops builder and reviewer, and only then merges."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

READY = {"ready": True, "reason": "", "repo": "o/r", "title": "Add slugify", "body": "Turn titles into slugs.", "decision": "",
         "unseen": [], "open_pr": 0}
PR = {"pr_number": 4, "pr_url": "https://github.com/o/r/pull/4", "stopped_because": ""}
APPROVE = {"verdict": "approve", "findings": []}
CHANGES = {"verdict": "changes", "findings": [{"must_fix": True, "where": "slug.py:3", "what": "empty title crashes",
                                       "repeat": False}]}
REPEATED = {"verdict": "changes", "findings": [{**CHANGES["findings"][0], "repeat": True}]}
MERGED = {"merged": True, "merge_commit": "abc1234", "reason": ""}


@unittest.skipUnless(HAVE_NODE, "needs node")
class BuildWorkflowTest(unittest.TestCase):
    def run_workflow(self, replies, args=12):
        return run_workflow("build", replies, args)

    def labels(self, run):
        return [call["label"] for call in run["calls"]]

    def test_an_issue_that_is_not_ready_starts_nothing(self):
        run = self.run_workflow({"check": [{**READY, "ready": False, "reason": "a red issue is open"}]})
        self.assertEqual(run["result"], {"issue": 12, "status": "not started", "reason": "a red issue is open"})
        self.assertNotIn("run report", self.labels(run))
        self.assertEqual(self.labels(run), ["check #12"])

    def test_an_issue_that_settles_an_unseen_technical_decision_waits_for_the_founder(self):
        ticket = {**READY, "unseen": ["plain HTML with no build step"]}
        run = self.run_workflow({"check": [ticket], "builder": [PR]})
        self.assertEqual(run["result"]["status"], "needs the founder")
        self.assertEqual(run["result"]["unseen"], ["plain HTML with no build step"])
        self.assertIn('"Technical decisions"', run["result"]["next"])
        self.assertEqual(self.labels(run), ["check #12"])

    def test_the_check_looks_for_one_way_doors_with_a_model_that_can_judge_them(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertEqual(check["model"], "sonnet")
        self.assertIn("technical one-way door", check["prompt"])
        self.assertIn('"Technical decisions" section', check["prompt"])

    def test_the_check_takes_an_issue_the_architect_cut_from_a_decided_brief(self):
        prompt = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]["prompt"]
        self.assertIn('its body starts "Part of #<n>"', prompt)
        self.assertIn('"Build after #<m>", each #<m> must be closed', prompt)
        self.assertIn("on this issue or on the brief it is part of", prompt)

    def test_an_approved_change_goes_to_the_integrator(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "reviewer": [APPROVE], "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")
        self.assertEqual(self.labels(run), ["check #12", "builder, round 1", "reviewer, round 1", "integrator, PR #4",
                                            "tidy worktrees", "run report"])

    def test_each_role_runs_as_its_plugin_agent_and_the_builder_in_a_worktree(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "reviewer": [APPROVE], "integrator": [MERGED]})
        builder, reviewer, integrator = run["calls"][1:4]
        self.assertEqual((builder["agentType"], builder["isolation"], builder["model"]),
                         ("founding-agents:builder", "worktree", "opus"))
        self.assertEqual((reviewer["agentType"], reviewer["model"]), ("founding-agents:reviewer", "opus"))
        self.assertEqual(integrator["agentType"], "founding-agents:integrator")

    def test_the_reviewer_sees_the_issue_but_not_the_builders_reasoning(self):
        run = self.run_workflow({"check": [READY], "builder": [{**PR, "stopped_because": ""}],
                                 "reviewer": [APPROVE], "integrator": [MERGED]})
        prompt = run["calls"][2]["prompt"]
        self.assertIn("Turn titles into slugs.", prompt)
        self.assertNotIn("Return the PR's number", prompt)

    def test_the_founders_pick_reaches_the_builder_and_the_reviewer(self):
        ticket = {**READY, "decision": "B, with a shorter headline (mockups on propose/issue-12)"}
        run = self.run_workflow({"check": [ticket], "builder": [PR], "reviewer": [APPROVE], "integrator": [MERGED]})
        for call in run["calls"][1:3]:
            self.assertIn("The founder decided: B, with a shorter headline", call["prompt"])

    def test_a_finished_run_posts_its_report_on_the_issue(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "reviewer": [APPROVE], "integrator": [MERGED],
                                 "run report": [{"comment_url": "https://github.com/o/r/issues/12#c1", "reason": ""}]})
        report = run["calls"][-1]
        self.assertEqual((report["label"], report["model"]), ("run report", "haiku"))
        self.assertIn("--workflow build --issue 12 --budget 5 --post", report["prompt"])
        self.assertEqual(run["result"]["report"], "https://github.com/o/r/issues/12#c1")

    def test_a_stalled_run_still_posts_its_report(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "reviewer": [CHANGES] * 3})
        self.assertEqual(self.labels(run)[-1], "run report")

    def test_findings_go_back_to_the_builder_on_the_same_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "reviewer": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")
        second = run["calls"][3]["prompt"]
        self.assertIn("gh pr checkout 4", second)
        self.assertIn("slug.py:3: empty title crashes", second)

    def test_three_send_backs_go_to_the_founder_and_nothing_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "reviewer": [CHANGES] * 3})
        self.assertIn("the founder decides", run["result"]["status"])
        self.assertNotIn("integrator, PR #4", self.labels(run))

    def test_the_same_finding_unfixed_twice_goes_to_the_founder_before_round_three(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "reviewer": [CHANGES, REPEATED, APPROVE]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertEqual(run["result"]["findings"], REPEATED["findings"])
        self.assertNotIn("builder, round 3", self.labels(run))

    def test_new_findings_in_a_later_round_get_another_round(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "reviewer": [CHANGES, CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")

    def test_the_reviewer_is_asked_to_mark_repeats_only_after_an_earlier_review(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "reviewer": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        first, second = [call["prompt"] for call in run["calls"] if call["label"].startswith("reviewer")]
        self.assertNotIn("as a repeat", first)
        self.assertIn("as a repeat", second)

    def test_an_open_pr_for_the_issue_is_continued_not_started_again(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "reviewer": [APPROVE], "integrator": [MERGED]})
        builder, reviewer = run["calls"][1:3]
        self.assertIn("PR #9 already builds issue #12", builder["prompt"])
        self.assertIn("gh pr checkout 9", builder["prompt"])
        self.assertIn("Do not open a new PR", builder["prompt"])
        self.assertIn("as a repeat", reviewer["prompt"])
        self.assertEqual(run["result"]["status"], "merged")

    def test_a_continued_pr_that_repeats_a_finding_goes_to_the_founder_at_once(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}, PR],
                                 "reviewer": [REPEATED]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertNotIn("builder, round 2", self.labels(run))

    def test_the_check_looks_for_an_open_pr_on_the_issue(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertIn("build/issue-12", check["prompt"])
        self.assertIn("open_pr", check["prompt"])

    def test_every_run_after_the_check_tidies_worktrees_before_its_report(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "reviewer": [CHANGES] * 3,
                                 "tidy": [{"removed": 2, "kept": ["wf_1: 1 uncommitted change(s)"]}]})
        self.assertEqual(self.labels(run)[-2:], ["tidy worktrees", "run report"])
        self.assertIn("tidy-worktrees skill", run["calls"][-2]["prompt"])
        self.assertEqual(run["result"]["worktrees_kept"], ["wf_1: 1 uncommitted change(s)"])

    def test_a_builder_that_stops_without_a_pr_ends_the_run(self):
        run = self.run_workflow({"check": [READY],
                                 "builder": [{"pr_number": 0, "pr_url": "", "stopped_because": "split it in two"}]})
        self.assertEqual(run["result"]["status"], "stopped in build")
        self.assertEqual(run["result"]["reason"], "split it in two")

    def test_takes_the_issue_as_a_number_a_string_or_an_object(self):
        for args in (12, "#12", {"issue": 12}):
            run = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]}, args=args)
            self.assertEqual(run["result"]["issue"], 12)

    def test_no_issue_is_an_error(self):
        self.assertIn("Name the issue", self.run_workflow({}, args=None)["error"])


if __name__ == "__main__":
    unittest.main()
