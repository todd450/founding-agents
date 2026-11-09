"""The build workflow checks the ticket, loops builder and reviewers, then leaves the PR for the founder's merge."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

READY = {"ready": True, "reason": "", "repo": "o/r", "title": "Add slugify", "body": "Turn titles into slugs.", "decision": "",
         "unseen": [], "open_pr": 0, "awaiting_merge": False, "security": False}
PR = {"pr_number": 4, "pr_url": "https://github.com/o/r/pull/4", "head": "aaa1111", "stopped_because": ""}
APPROVE = {"verdict": "approve", "security": False, "findings": []}
CHANGES = {"verdict": "changes", "security": False,
           "findings": [{"must_fix": True, "where": "slug.py:3", "what": "empty title crashes", "repeat": False}]}
REPEATED = {"verdict": "changes", "findings": [{**CHANGES["findings"][0], "repeat": True}]}
READIED = {"ready": True, "comment_url": "https://github.com/o/r/pull/4#c1", "reason": ""}
INSECURE = {"verdict": "changes", "findings": [{"must_fix": True, "where": "api.py:9", "what": "any user reads any draft",
                                                "repeat": False}]}
FLAGGED = {**APPROVE, "security": True}
SENSITIVE = {**READY, "security": True}


@unittest.skipUnless(HAVE_NODE, "needs node")
class BuildWorkflowTest(unittest.TestCase):
    def run_workflow(self, replies, args=12, slow=None):
        return run_workflow("build", replies, args, slow)

    def labels(self, run):
        return [call["label"] for call in run["calls"]]

    def test_an_issue_that_is_not_ready_starts_nothing(self):
        run = self.run_workflow({"check": [{**READY, "ready": False, "reason": "a red issue is open"}]})
        self.assertEqual(run["result"], {"issue": 12, "status": "not started", "reason": "a red issue is open"})
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

    def test_the_check_takes_one_decided_issue(self):
        prompt = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]["prompt"]
        self.assertIn("it must be open and labelled `decided`", prompt)
        self.assertNotIn("Part of", prompt)

    def test_an_approved_change_is_left_for_the_founders_merge(self):
        # The founder merges every PR; on Half Badger, auto mode refused an agent's merges that
        # deploy, and each approved PR waited for the whole run to end.
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        self.assertEqual(run["result"]["queue_item"], "https://github.com/o/r/pull/4#c1")
        self.assertEqual(self.labels(run), ["check #12", "builder #12, round 1", "review #12, round 1",
                                            "ready for your merge, PR #4", "tidy worktrees"])

    def test_the_ready_step_tests_the_merge_and_never_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        item = run["calls"][-2]
        self.assertEqual(item["model"], "haiku")
        self.assertIn("Never merge it, and never push to `main`", item["prompt"])
        self.assertIn("gh pr update-branch 4 --repo o/r", item["prompt"])
        self.assertIn("gh pr checks 4 --repo o/r --required --watch", item["prompt"])
        self.assertIn("--label red --state open", item["prompt"])
        self.assertIn("**Ready for your merge:** PR #4 builds #12, Add slugify. The reviewer approved it", item["prompt"])
        self.assertIn("No security review ran: neither the issue nor the diff touches routes, sign-in", item["prompt"])
        self.assertIn("`/founding-agents:build 12 security` before you merge", item["prompt"])
        self.assertIn('"The founder checks"', item["prompt"])
        self.assertIn("gh pr edit 4 --repo o/r --add-label needs-founder", item["prompt"])

    def test_a_pr_whose_checks_fail_is_not_ready(self):
        failed = {"ready": False, "comment_url": "", "reason": "check failed on the merge"}
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [failed]})
        self.assertEqual(run["result"]["status"], "not ready")
        self.assertEqual(run["result"]["reason"], "check failed on the merge")
        self.assertEqual(self.labels(run)[-1], "tidy worktrees")

    def test_a_pr_already_waiting_for_the_founders_merge_is_not_built_again(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9, "awaiting_merge": True}], "builder": [PR]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        self.assertEqual(self.labels(run), ["check #12"])

    def test_the_check_finds_a_pr_waiting_for_the_founders_merge(self):
        prompt = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]["prompt"]
        self.assertIn('starts "**Ready for your merge:**"', prompt)

    def test_reviewers_leave_the_founders_pass_marks_to_the_founder(self):
        # Half Badger's #2 went back three times on pass marks behind Vercel's dashboard and login.
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        for call in run["calls"]:
            if call["label"].startswith(("review", "security review")):
                self.assertIn('Pass marks under "The founder checks" in the issue are the founder\'s: never send the change back for one', call["prompt"])

    def test_each_role_runs_as_its_plugin_agent_and_the_builder_in_a_worktree(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        builder, review = run["calls"][1:3]
        self.assertEqual((builder["agentType"], builder["isolation"], builder["model"]),
                         ("founding-agents:builder", "worktree", "opus"))
        self.assertEqual((review["agentType"], review["model"]), ("founding-agents:reviewer", "opus"))

    def test_reviewers_see_the_issue_but_not_the_builders_reasoning(self):
        run = self.run_workflow({"check": [READY], "builder": [{**PR, "stopped_because": ""}],
                                 "review": [APPROVE], "ready for your merge": [READIED]})
        prompt = run["calls"][2]["prompt"]
        self.assertIn("Turn titles into slugs.", prompt)
        self.assertNotIn("Return the PR's number", prompt)

    def test_the_founders_pick_reaches_the_builder_and_the_reviewer(self):
        ticket = {**READY, "decision": "B, with a shorter headline (mockups on propose/issue-12)"}
        run = self.run_workflow({"check": [ticket], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        for call in run["calls"][1:3]:
            self.assertIn("The founder decided: B, with a shorter headline", call["prompt"])

    def test_a_stalled_run_still_tidies_its_worktrees(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "review": [CHANGES] * 3})
        self.assertEqual(self.labels(run)[-1], "tidy worktrees")

    def test_findings_go_back_to_the_builder_on_the_same_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "review": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("gh pr checkout 4", second)
        self.assertIn("- Reviewer: slug.py:3: empty title crashes", second)

    def test_a_builder_fixing_a_pr_is_asked_to_keep_its_screenshots_current(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [PR, PR], "review": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        prompts = [call["prompt"] for call in run["calls"] if call["label"].startswith("builder")]
        self.assertEqual(len(prompts), 2)
        for prompt in prompts:
            self.assertIn("retake the after screenshots", prompt)

    def test_three_send_backs_go_to_the_founder_and_nothing_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "review": [CHANGES] * 3})
        self.assertIn("the founder decides", run["result"]["status"])
        self.assertNotIn("ready for your merge, PR #4", self.labels(run))

    def test_the_same_finding_unfixed_twice_goes_to_the_founder_before_round_three(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "review": [CHANGES, REPEATED, APPROVE]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertEqual(run["result"]["findings"], [{**REPEATED["findings"][0], "where": "Reviewer: slug.py:3"}])
        self.assertNotIn("builder #12, round 3", self.labels(run))

    def test_the_same_finding_unfixed_twice_goes_to_the_librarian_as_an_issue(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "review": [CHANGES, REPEATED],
                                 "lesson": [{"issue_url": "https://github.com/o/r/issues/30", "reason": ""}]})
        lesson = next(call for call in run["calls"] if call["label"] == "lesson, PR #4")
        self.assertEqual(lesson["model"], "haiku")
        self.assertIn("--label librarian", lesson["prompt"])
        self.assertIn('--title "Repeated finding on PR #4"', lesson["prompt"])
        self.assertIn("- Reviewer: slug.py:3: empty title crashes", lesson["prompt"])
        self.assertIn("https://github.com/o/r/pull/4", lesson["prompt"])
        self.assertIn("a test, a lint rule, a hook or a skill", lesson["prompt"])
        self.assertIn("say how to fix the problem, not only what failed", lesson["prompt"])
        self.assertEqual(run["result"]["lesson"], "https://github.com/o/r/issues/30")
        self.assertEqual(self.labels(run)[-1], "tidy worktrees")

    def test_the_librarian_issue_is_not_opened_twice_for_one_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "review": [CHANGES, REPEATED]})
        prompt = next(call["prompt"] for call in run["calls"] if call["label"].startswith("lesson"))
        self.assertIn("--label librarian --state open", prompt)
        self.assertIn("instead of opening another", prompt)

    def test_findings_that_are_new_each_round_file_no_lesson(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "review": [CHANGES] * 3})
        self.assertFalse([label for label in self.labels(run) if label.startswith("lesson")])

    def test_the_librarian_label_is_created_as_setup_creates_it(self):
        build = (Path(__file__).resolve().parent.parent / "workflows" / "build.js").read_text()
        setup = (Path(__file__).resolve().parent.parent / "skills" / "setup" / "SKILL.md").read_text()
        command = re.search(r"gh label create librarian [^'\n]+", build).group(0)
        self.assertIn(command, setup)

    def test_the_check_the_reviewer_and_the_security_reviewer_name_the_same_changes(self):
        root = Path(__file__).resolve().parent.parent
        words = re.search(r"^const SENSITIVE = '(.+)'$", (root / "workflows" / "build.js").read_text(), re.M).group(1)
        review = " ".join((root / "agents" / "reviewer.md").read_text().split())
        security = " ".join((root / "agents" / "security-reviewer.md").read_text().split())
        self.assertIn(f"Say whether the diff touches {words};", review)
        self.assertIn(f"You look at changes that touch {words}.", security)

    def test_the_builder_leaves_ci_to_the_reviewer_and_the_ready_step(self):
        agents = Path(__file__).resolve().parent.parent / "agents"
        builder = " ".join((agents / "builder.md").read_text().split())
        code = " ".join((agents / "reviewer.md").read_text().split())
        self.assertIn("Run `check.sh` before you push, then return the PR without waiting for CI", builder)
        self.assertIn("`gh pr checks <number> --watch`", code)
        self.assertIn("A failing check is a finding that must be fixed", code)

    def test_new_findings_in_a_later_round_get_another_round(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "review": [CHANGES, CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_reviewers_are_asked_to_mark_repeats_only_after_an_earlier_review(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "review": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        first, second = [call["prompt"] for call in run["calls"] if call["label"].startswith("review")]
        self.assertNotIn("as a repeat", first)
        self.assertIn("as a repeat", second)

    def test_a_repeat_is_only_a_finding_from_an_earlier_round(self):
        # On the website's #27, a reviewer counted a finding the other reviewers had raised minutes
        # earlier in the same round as a repeat, and the run stopped a round early.
        run = self.run_workflow({"check": [SENSITIVE], "builder": [PR, PR], "review": [CHANGES, APPROVE],
                                 "security review": [APPROVE, APPROVE], "ready for your merge": [READIED]})
        review, security = [call["prompt"] for call in run["calls"] if call["label"].startswith(("review", "security review"))][2:]
        for prompt in (review, security):
            self.assertIn("a finding only they raised is not a repeat", prompt)
            self.assertIn("Nor is one an earlier round marked as a Nit", prompt)
        # Each reviewer is given its own findings from last time, not the other reviewer's.
        self.assertIn("Your findings last time:\n- slug.py:3: empty title crashes", review)
        self.assertIn("You raised nothing last time.", security)

    def test_a_continued_pr_gets_the_rule_but_no_list_it_cannot_know(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "review": [APPROVE], "ready for your merge": [READIED]})
        review = next(call["prompt"] for call in run["calls"] if call["label"].startswith("review"))
        self.assertIn("a finding only they raised is not a repeat", review)
        self.assertNotIn("Your findings last time", review)
        self.assertIn("If you reviewed this PR before", review)
        self.assertIn("gh pr view <number> --json commits", review)

    def test_the_check_says_whether_the_issue_needs_a_security_review(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertIn("Return security true when building it will touch routes, sign-in", check["prompt"])
        self.assertIn("security", check["schema"]["required"])
        self.assertNotIn("risk", check["schema"]["properties"])

    def test_every_change_gets_the_one_reviewer_on_opus(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        self.assertEqual([(c["label"], c["model"]) for c in run["calls"] if "review #" in c["label"]],
                         [("review #12, round 1", "opus")])
        self.assertEqual(run["result"]["security"], False)

    def test_an_issue_that_needs_it_gets_its_security_review_beside_the_reviewer(self):
        run = self.run_workflow({"check": [SENSITIVE], "builder": [PR], "review": [APPROVE],
                                 "security review": [APPROVE], "ready for your merge": [READIED]},
                                slow={"review": 30, "security review": 30})
        reviews = [e for e in run["events"] if " #12, round 1" in e and not e.endswith("builder #12, round 1")]
        self.assertEqual([e.split()[0] for e in reviews], ["start"] * 2 + ["end"] * 2)
        security = next(call for call in run["calls"] if call["label"] == "security review #12, round 1")
        self.assertEqual((security["agentType"], security["model"]), ("founding-agents:security-reviewer", "opus"))
        item = next(c["prompt"] for c in run["calls"] if c["label"].startswith("ready for your merge"))
        self.assertIn("The reviewer and the security reviewer approved it", item)
        self.assertNotIn("No security review ran", item)
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_the_founder_can_ask_for_a_security_review(self):
        for args in ("12 security", {"issue": 12, "security": True}):
            run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE],
                                     "security review": [APPROVE], "ready for your merge": [READIED]}, args=args)
            self.assertIn("security review #12, round 1", self.labels(run))

    def test_asking_for_a_security_review_continues_a_pr_waiting_for_the_merge(self):
        ticket = {**READY, "open_pr": 9, "awaiting_merge": True}
        run = self.run_workflow({"check": [ticket], "builder": [{**PR, "pr_number": 9}], "review": [APPROVE],
                                 "security review": [APPROVE], "ready for your merge": [READIED]}, args="12 security")
        self.assertIn("security review #12, round 1", self.labels(run))
        self.assertIn("PR #9 already builds issue #12", run["calls"][1]["prompt"])

    def test_a_security_review_the_issue_asked_for_runs_once_even_when_the_reviewer_flags_the_diff(self):
        run = self.run_workflow({"check": [SENSITIVE], "builder": [PR], "review": [FLAGGED], "security review": [APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual([label for label in self.labels(run) if label.startswith("security")], ["security review #12, round 1"])

    def test_a_diff_the_issue_did_not_flag_gets_a_security_review_once_the_reviewer_flags_it(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "review": [FLAGGED, APPROVE],
                                 "security review": [INSECURE, APPROVE], "ready for your merge": [READIED]})
        events = run["events"]
        self.assertLess(events.index("end review #12, round 1"), events.index("start security review #12, round 1"))
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("- Security: api.py:9: any user reads any draft", second)
        # Once on, the security reviewer stays on for the next round.
        self.assertIn("security review #12, round 2", self.labels(run))
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_a_security_review_that_returns_nothing_stops_the_run(self):
        for replies in ({"check": [SENSITIVE], "builder": [PR], "review": [APPROVE]},
                        {"check": [READY], "builder": [PR], "review": [FLAGGED]}):
            run = self.run_workflow(replies)
            self.assertEqual(run["result"]["status"], "stopped in review")
            self.assertNotIn("ready for your merge, PR #4", self.labels(run))

    def test_a_change_that_does_not_need_it_gets_no_security_review(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "review": [APPROVE], "ready for your merge": [READIED]})
        self.assertFalse([label for label in self.labels(run) if label.startswith("security")])

    def test_a_nit_reaches_the_builder_marked_as_one(self):
        nit = {"verdict": "changes", "security": False,
               "findings": [{"must_fix": False, "where": "facts.json", "what": "a crafted link", "repeat": False}]}
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "review": [nit, APPROVE], "ready for your merge": [READIED]})
        builder = next(c["prompt"] for c in run["calls"] if c["label"] == "builder #12, round 2")
        self.assertIn("- Nit: Reviewer: facts.json: a crafted link", builder)

    def test_the_check_is_told_an_open_pr_never_makes_the_issue_unready(self):
        # On the website's #27 the check read an open PR as "already being built" and skipped it, so
        # the six issues that build after it never started.
        prompt = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]["prompt"]
        self.assertIn("An open PR is never a reason to stop", prompt)

    def test_an_open_pr_for_the_issue_is_continued_not_started_again(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "review": [APPROVE], "ready for your merge": [READIED]})
        builder, reviewer = run["calls"][1:3]
        self.assertIn("PR #9 already builds issue #12", builder["prompt"])
        self.assertIn("gh pr checkout 9", builder["prompt"])
        self.assertIn("Do not open a new PR", builder["prompt"])
        self.assertIn("as a repeat", reviewer["prompt"])
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_a_continued_pr_that_repeats_a_finding_goes_to_the_founder_at_once(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}, PR],
                                 "review": [REPEATED]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertNotIn("builder #12, round 2", self.labels(run))

    def test_the_check_looks_for_an_open_pr_on_the_issue(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertIn("build/issue-12", check["prompt"])
        self.assertIn("open_pr", check["prompt"])

    def test_every_run_after_the_check_tidies_worktrees(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "review": [CHANGES] * 3,
                                 "tidy": [{"removed": 2, "kept": ["wf_1: 1 uncommitted change(s)"]}]})
        self.assertEqual(self.labels(run)[-1], "tidy worktrees")
        self.assertIn("tidy-worktrees skill", run["calls"][-1]["prompt"])
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


@unittest.skipUnless(HAVE_NODE, "needs node")
class ReReviewTest(unittest.TestCase):
    """From the second round each reviewer checks what changed and its own findings, not the whole PR."""

    def second_round(self):
        return run_workflow("build", {"check": [SENSITIVE], "builder": [PR, {**PR, "head": "bbb2222"}],
                                      "review": [CHANGES, APPROVE], "security review": [APPROVE] * 2,
                                      "ready for your merge": [READIED]}, 12)

    def prompt(self, run, label):
        return next(c["prompt"] for c in run["calls"] if c["label"] == label)

    def test_a_reviewer_reviews_only_the_diff_since_its_last_review(self):
        review = self.prompt(self.second_round(), "review #12, round 2")
        self.assertIn("`git diff aaa1111..bbb2222`", review)
        self.assertIn("Review only what changed since then", review)
        self.assertIn("Leave alone what has not changed since your last review", review)

    def test_a_reviewer_is_given_its_own_earlier_findings(self):
        run = self.second_round()
        self.assertIn("Your findings last time:\n- slug.py:3: empty title crashes", self.prompt(run, "review #12, round 2"))
        self.assertIn("You raised nothing last time.", self.prompt(run, "security review #12, round 2"))

    def test_the_first_round_reviews_the_whole_pr(self):
        review = self.prompt(self.second_round(), "review #12, round 1")
        self.assertNotIn("Review only what changed", review)

    def test_a_reviewer_that_joins_later_reviews_the_whole_pr(self):
        run = run_workflow("build", {"check": [READY], "builder": [PR, PR], "review": [CHANGES, FLAGGED],
                                     "security review": [APPROVE], "ready for your merge": [READIED]}, 12)
        security = self.prompt(run, "security review #12, round 2")
        self.assertNotIn("Review only what changed", security)
        self.assertIn("Review only what changed", self.prompt(run, "review #12, round 2"))

    def test_the_builder_returns_the_commit_its_branch_ends_at(self):
        builder = self.second_round()["calls"][1]
        self.assertIn("head", builder["schema"]["required"])


if __name__ == "__main__":
    unittest.main()
