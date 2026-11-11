"""The build workflow checks the ticket, loops builder and reviewers, then leaves the PR for the founder's merge."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

READY = {"ready": True, "reason": "", "repo": "o/r", "title": "Add slugify", "body": "Turn titles into slugs.", "decision": "",
         "unseen": [], "open_pr": 0, "awaiting_merge": False, "risk": "medium"}
PR = {"pr_number": 4, "pr_url": "https://github.com/o/r/pull/4", "head": "aaa1111", "stopped_because": ""}
APPROVE = {"verdict": "approve", "findings": []}
CHANGES = {"verdict": "changes", "findings": [{"must_fix": True, "reach": "anyone", "review_would_see": False,
                                               "where": "slug.py:3", "what": "empty title crashes", "repeat": False}]}
REPEATED = {"verdict": "changes", "findings": [{**CHANGES["findings"][0], "repeat": True}]}
READIED = {"ready": True, "comment_url": "https://github.com/o/r/pull/4#c1", "reason": ""}
CODE_OK = APPROVE
INSECURE = {"verdict": "changes", "findings": [{"must_fix": True, "reach": "user", "review_would_see": False,
                                                "where": "api.py:9", "what": "any user reads any draft", "repeat": False}]}
HIGH = {**READY, "risk": "high"}


def with_code_review(replies):
    """Tests about QA's verdicts get a code reviewer that approves every round."""
    return {"code review": [CODE_OK] * 12, **replies}


@unittest.skipUnless(HAVE_NODE, "needs node")
class BuildWorkflowTest(unittest.TestCase):
    def run_workflow(self, replies, args=12, slow=None):
        return run_workflow("build", with_code_review(replies), args, slow)

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
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "ready for your merge": [READIED]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        self.assertEqual(run["result"]["queue_item"], "https://github.com/o/r/pull/4#c1")
        self.assertEqual(self.labels(run), ["check #12", "builder #12, round 1", "qa #12, round 1", "code review #12, round 1",
                                            "ready for your merge, PR #4", "tidy worktrees"])

    def test_the_ready_step_tests_the_merge_and_never_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "ready for your merge": [READIED]})
        item = run["calls"][-2]
        self.assertEqual(item["model"], "haiku")
        self.assertIn("Never merge it, and never push to `main`", item["prompt"])
        self.assertIn("gh pr update-branch 4 --repo o/r", item["prompt"])
        self.assertIn("gh pr checks 4 --repo o/r --required --watch", item["prompt"])
        self.assertIn("--label red --state open", item["prompt"])
        self.assertIn("**Ready for your merge:** PR #4 builds #12, Add slugify. QA, Code review approved it", item["prompt"])
        self.assertIn("No security review ran", item["prompt"])
        self.assertIn('"The founder checks"', item["prompt"])
        self.assertIn("gh pr edit 4 --repo o/r --add-label needs-founder", item["prompt"])

    def test_a_pr_whose_checks_fail_is_not_ready(self):
        failed = {"ready": False, "comment_url": "", "reason": "check failed on the merge"}
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "ready for your merge": [failed]})
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
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "ready for your merge": [READIED]})
        for call in run["calls"]:
            if call["label"].startswith(("qa", "code review")):
                self.assertIn('Pass marks under "The founder checks" in the issue are the founder\'s: never send the change back for one', call["prompt"])

    def test_each_role_runs_as_its_plugin_agent_and_the_builder_in_a_worktree(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "ready for your merge": [READIED]})
        builder, qa, code = run["calls"][1:4]
        self.assertEqual((builder["agentType"], builder["isolation"], builder["model"]),
                         ("founding-agents:builder", "worktree", "opus"))
        self.assertEqual((qa["agentType"], qa["model"]), ("founding-agents:qa", "opus"))
        self.assertEqual((code["agentType"], code["model"]), ("founding-agents:code-reviewer", "opus"))

    def test_the_builder_tries_harder_on_a_change_the_reviewers_sent_back(self):
        # Effort goes up before the model does: round one at medium, a sent-back change at high.
        run = self.run_workflow(with_code_review({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                                  "ready for your merge": [READIED]}))
        efforts = [c["effort"] for c in run["calls"] if c["label"].startswith("builder")]
        self.assertEqual(efforts, ["medium", "high"])

    def test_every_step_names_its_effort_and_the_security_review_the_most(self):
        run = self.run_workflow(with_code_review({"check": [{**READY, "risk": "high"}], "builder": [PR], "qa": [APPROVE],
                                                  "security review": [APPROVE], "ready for your merge": [READIED]}))
        for call in run["calls"]:
            self.assertIn(call["effort"], ("low", "medium", "high"), call["label"])
        efforts = {c["label"].split(" #")[0]: c["effort"] for c in run["calls"]}
        self.assertEqual((efforts["qa"], efforts["code review"], efforts["security review"]), ("medium", "medium", "high"))

    def test_reviewers_see_the_issue_but_not_the_builders_reasoning(self):
        run = self.run_workflow({"check": [READY], "builder": [{**PR, "stopped_because": ""}],
                                 "qa": [APPROVE], "ready for your merge": [READIED]})
        prompt = run["calls"][2]["prompt"]
        self.assertIn("Turn titles into slugs.", prompt)
        self.assertNotIn("Return the PR's number", prompt)

    def test_the_founders_pick_reaches_the_builder_and_qa(self):
        ticket = {**READY, "decision": "B, with a shorter headline (mockups on propose/issue-12)"}
        run = self.run_workflow({"check": [ticket], "builder": [PR], "qa": [APPROVE], "ready for your merge": [READIED]})
        for call in run["calls"][1:3]:
            self.assertIn("The founder decided: B, with a shorter headline", call["prompt"])

    def test_a_stalled_run_still_tidies_its_worktrees(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3})
        self.assertEqual(self.labels(run)[-1], "tidy worktrees")

    def test_findings_go_back_to_the_builder_on_the_same_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("gh pr checkout 4", second)
        self.assertIn("- QA: slug.py:3: empty title crashes", second)

    def test_a_builder_fixing_a_pr_is_asked_to_keep_its_screenshots_current(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        prompts = [call["prompt"] for call in run["calls"] if call["label"].startswith("builder")]
        self.assertEqual(len(prompts), 2)
        for prompt in prompts:
            self.assertIn("retake the after screenshots", prompt)

    def test_three_send_backs_go_to_the_founder_and_nothing_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3})
        self.assertIn("the founder decides", run["result"]["status"])
        self.assertNotIn("ready for your merge, PR #4", self.labels(run))

    def test_the_same_finding_unfixed_twice_goes_to_the_founder_before_round_three(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES, REPEATED, APPROVE]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertEqual(run["result"]["findings"], [{**REPEATED["findings"][0], "where": "QA: slug.py:3"}])
        self.assertNotIn("builder #12, round 3", self.labels(run))

    def test_the_same_finding_unfixed_twice_goes_to_the_librarian_as_an_issue(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, REPEATED],
                                 "lesson": [{"issue_url": "https://github.com/o/r/issues/30", "reason": ""}]})
        lesson = next(call for call in run["calls"] if call["label"] == "lesson, PR #4")
        self.assertEqual(lesson["model"], "haiku")
        self.assertIn("--label librarian", lesson["prompt"])
        self.assertIn('--title "Repeated finding on PR #4"', lesson["prompt"])
        self.assertIn("- QA: slug.py:3: empty title crashes", lesson["prompt"])
        self.assertIn("https://github.com/o/r/pull/4", lesson["prompt"])
        self.assertIn("a test, a lint rule, a hook or a skill", lesson["prompt"])
        self.assertIn("say how to fix the problem, not only what failed", lesson["prompt"])
        self.assertEqual(run["result"]["lesson"], "https://github.com/o/r/issues/30")
        self.assertEqual(self.labels(run)[-1], "tidy worktrees")

    def test_the_librarian_issue_is_not_opened_twice_for_one_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, REPEATED]})
        prompt = next(call["prompt"] for call in run["calls"] if call["label"].startswith("lesson"))
        self.assertIn("--label librarian --state open", prompt)
        self.assertIn("instead of opening another", prompt)

    def test_findings_that_are_new_each_round_file_no_lesson(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3})
        self.assertFalse([label for label in self.labels(run) if label.startswith("lesson")])

    def test_the_librarian_label_is_created_as_setup_creates_it(self):
        build = (Path(__file__).resolve().parent.parent / "workflows" / "build.js").read_text()
        setup = (Path(__file__).resolve().parent.parent / "skills" / "setup" / "SKILL.md").read_text()
        command = re.search(r"gh label create librarian [^'\n]+", build).group(0)
        self.assertIn(command, setup)

    def test_the_check_and_the_code_reviewer_flag_the_same_changes_for_security(self):
        root = Path(__file__).resolve().parent.parent
        words = re.search(r"high: it touches ([^.]+)\.", (root / "workflows" / "build.js").read_text()).group(1)
        code = " ".join((root / "agents" / "code-reviewer.md").read_text().split())
        security = " ".join((root / "agents" / "security-reviewer.md").read_text().split())
        self.assertIn(f"high when it touches {words}.", code)
        self.assertIn(f"You look at changes that touch {words}.", security)

    def test_the_builder_leaves_ci_to_the_code_reviewer_and_the_ready_step(self):
        agents = Path(__file__).resolve().parent.parent / "agents"
        builder = " ".join((agents / "builder.md").read_text().split())
        code = " ".join((agents / "code-reviewer.md").read_text().split())
        self.assertIn("Run `check.sh` before you push, then return the PR without waiting for CI", builder)
        self.assertIn("`gh pr checks <number> --watch`", code)
        self.assertIn("A failing check is a finding that must be fixed", code)

    def test_new_findings_in_a_later_round_get_another_round(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES, CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_reviewers_are_asked_to_mark_repeats_only_after_an_earlier_review(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        first, second = [call["prompt"] for call in run["calls"] if call["label"].startswith("qa")]
        self.assertNotIn("as a repeat", first)
        self.assertIn("as a repeat", second)

    def test_a_repeat_is_only_a_finding_from_an_earlier_round(self):
        # On the website's #27, a reviewer counted a finding the other reviewers had raised minutes
        # earlier in the same round as a repeat, and the run stopped a round early.
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "ready for your merge": [READIED]})
        qa, code = [call["prompt"] for call in run["calls"] if call["label"].startswith(("qa", "code review"))][2:]
        for prompt in (qa, code):
            self.assertIn("a finding only they raised is not a repeat", prompt)
            self.assertIn("Nor is one an earlier round marked as a Nit", prompt)
        # Each reviewer is given its own findings from last time, not the other reviewers'.
        self.assertIn("Your findings last time:\n- slug.py:3: empty title crashes", qa)
        self.assertIn("You raised nothing last time.", code)

    def test_a_continued_pr_gets_the_rule_but_no_list_it_cannot_know(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "qa": [APPROVE], "ready for your merge": [READIED]})
        qa = next(call["prompt"] for call in run["calls"] if call["label"].startswith("qa"))
        self.assertIn("a finding only they raised is not a repeat", qa)
        self.assertNotIn("Your findings last time", qa)
        self.assertIn("If you reviewed this PR before", qa)
        self.assertIn("gh pr view <number> --json commits", qa)

    def test_qa_and_code_review_run_side_by_side_and_both_must_approve(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [APPROVE, APPROVE],
                                    "code review": [CHANGES, CODE_OK],
                                    "ready for your merge": [READIED]})
        labels = self.labels(run)
        self.assertEqual(labels.index("code review #12, round 1"), labels.index("qa #12, round 1") + 1)
        self.assertIn("builder #12, round 2", labels)
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("- Code review: slug.py:3: empty title crashes", second)

    def test_the_check_reads_the_issues_risk_or_rates_it(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertIn('Take the tier its "Risk" section names', check["prompt"])
        self.assertIn("return your rating when it is higher than the section's", check["prompt"])
        self.assertIn("high: it touches routes, sign-in", check["prompt"])
        self.assertEqual(check["schema"]["properties"]["risk"]["enum"], ["low", "medium", "high"])
        self.assertIn("risk", check["schema"]["required"])

    def test_an_issue_that_needs_it_gets_its_security_review_beside_qa_and_code_review(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE],
                                 "security review": [APPROVE], "ready for your merge": [READIED]},
                                slow={"qa": 30, "code review": 30, "security review": 30})
        reviews = [e for e in run["events"] if " #12, round 1" in e and not e.endswith("builder #12, round 1")]
        self.assertEqual([e.split()[0] for e in reviews], ["start"] * 3 + ["end"] * 3)
        security = next(call for call in run["calls"] if call["label"] == "security review #12, round 1")
        self.assertEqual((security["agentType"], security["model"]), ("founding-agents:security-reviewer", "opus"))
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_a_security_review_the_issue_asked_for_runs_once_even_when_code_review_flags_the_diff(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE],
                                 "code review": [{**CODE_OK, "risk": "high"}], "security review": [APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual([label for label in self.labels(run) if label.startswith("security")], ["security review #12, round 1"])

    def test_findings_from_the_early_security_review_go_back_to_the_builder(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR, PR], "qa": [APPROVE, APPROVE],
                                 "security review": [INSECURE, APPROVE], "ready for your merge": [READIED]})
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("- Security: api.py:9: any user reads any draft", second)
        self.assertIn("security review #12, round 2", self.labels(run))
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_a_late_security_review_that_returns_nothing_stops_the_run(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE],
                                 "code review": [{**CODE_OK, "risk": "high"}]})
        self.assertEqual(run["result"]["status"], "stopped in review")

    def test_an_early_security_review_that_returns_nothing_stops_the_run(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE]})
        self.assertEqual(run["result"]["status"], "stopped in review")
        self.assertNotIn("ready for your merge, PR #4", self.labels(run))

    def test_a_diff_the_issue_did_not_flag_gets_a_security_review_as_soon_as_code_review_flags_it(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE],
                                 "code review": [{**CODE_OK, "risk": "high"}], "security review": [INSECURE]},
                                slow={"code review": 10, "qa": 80})
        events = run["events"]
        self.assertLess(events.index("end code review #12, round 1"), events.index("start security review #12, round 1"))
        self.assertLess(events.index("start security review #12, round 1"), events.index("end qa #12, round 1"))
        security = next(call for call in run["calls"] if call["label"] == "security review #12, round 1")
        self.assertEqual((security["agentType"], security["model"]), ("founding-agents:security-reviewer", "opus"))
        self.assertIn("builder #12, round 2", self.labels(run))

    def test_a_change_that_does_not_need_it_gets_no_security_review(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "ready for your merge": [READIED]})
        self.assertFalse([label for label in self.labels(run) if label.startswith("security")])

    def test_the_check_is_told_an_open_pr_never_makes_the_issue_unready(self):
        # On the website's #27 the check read an open PR as "already being built" and skipped it, so
        # the six issues that build after it never started.
        prompt = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]["prompt"]
        self.assertIn("An open PR is never a reason to stop", prompt)

    def test_an_open_pr_for_the_issue_is_continued_not_started_again(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "qa": [APPROVE], "ready for your merge": [READIED]})
        builder, reviewer = run["calls"][1:3]
        self.assertIn("PR #9 already builds issue #12", builder["prompt"])
        self.assertIn("gh pr checkout 9", builder["prompt"])
        self.assertIn("Do not open a new PR", builder["prompt"])
        self.assertIn("as a repeat", reviewer["prompt"])
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_a_continued_pr_that_repeats_a_finding_goes_to_the_founder_at_once(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}, PR],
                                 "qa": [REPEATED]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertNotIn("builder #12, round 2", self.labels(run))

    def test_the_check_looks_for_an_open_pr_on_the_issue(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertIn("build/issue-12", check["prompt"])
        self.assertIn("open_pr", check["prompt"])

    def test_every_run_after_the_check_tidies_worktrees(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3,
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


def reviewers(run, round_=1):
    """Each review of a round, as (label prefix, model)."""
    return [(c["label"].split(" #")[0], c["model"]) for c in run["calls"]
            if c["label"].endswith(f"round {round_}") and not c["label"].startswith("builder")]


TRUSTED = {"must_fix": True, "reach": "trusted", "review_would_see": True, "where": "facts.json",
           "what": "a fact written with a javascript: link renders as a link", "repeat": False}


@unittest.skipUnless(HAVE_NODE, "needs node")
class RiskTierTest(unittest.TestCase):
    """Each issue's risk decides which reviewers it gets and on which model; reviewers only raise it."""

    def run_workflow(self, replies, args=12, slow=None):
        return run_workflow("build", replies, args, slow)

    def test_a_low_risk_issue_gets_code_review_alone_on_sonnet(self):
        run = self.run_workflow({"check": [{**READY, "risk": "low"}], "builder": [PR], "code review": [APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(reviewers(run), [("code review", "sonnet")])
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_a_medium_risk_issue_gets_qa_and_code_review_on_opus(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "code review": [APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(reviewers(run), [("qa", "opus"), ("code review", "opus")])

    def test_a_high_risk_issue_gets_all_three_on_opus(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE], "code review": [APPROVE],
                                 "security review": [APPROVE], "ready for your merge": [READIED]})
        self.assertEqual(reviewers(run), [("qa", "opus"), ("code review", "opus"), ("security review", "opus")])

    def test_an_issue_with_no_known_risk_gets_the_most_review(self):
        run = self.run_workflow({"check": [{**READY, "risk": "unsure"}], "builder": [PR], "qa": [APPROVE],
                                 "code review": [APPROVE], "security review": [APPROVE], "ready for your merge": [READIED]})
        self.assertEqual([r for r, _ in reviewers(run)], ["qa", "code review", "security review"])

    def test_a_reviewer_that_raises_the_tier_brings_in_its_reviewers_at_once(self):
        run = self.run_workflow({"check": [{**READY, "risk": "low"}], "builder": [PR],
                                 "code review": [{**APPROVE, "risk": "high"}], "qa": [APPROVE],
                                 "security review": [APPROVE], "ready for your merge": [READIED]})
        self.assertEqual(reviewers(run), [("code review", "sonnet"), ("qa", "opus"), ("security review", "opus")])
        self.assertEqual(run["result"]["status"], "ready for your merge")

    def test_the_raised_tier_holds_for_the_next_round(self):
        run = self.run_workflow({"check": [{**READY, "risk": "low"}], "builder": [PR, PR],
                                 "code review": [{**CHANGES, "risk": "medium"}, APPROVE], "qa": [APPROVE, APPROVE],
                                 "ready for your merge": [READIED]})
        self.assertEqual(reviewers(run, 2), [("qa", "opus"), ("code review", "opus")])

    def test_a_reviewer_cannot_lower_the_tier(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR, PR], "qa": [{**CHANGES, "risk": "low"}, APPROVE],
                                 "code review": [{**APPROVE, "risk": "low"}] * 2, "security review": [APPROVE] * 2,
                                 "ready for your merge": [READIED]})
        self.assertEqual(reviewers(run, 2), [("qa", "opus"), ("code review", "opus"), ("security review", "opus")])

    def test_build_names_what_each_risk_tier_covers(self):
        source = (Path(__file__).resolve().parent.parent / "workflows" / "build.js").read_text()
        risk = re.search(r"^const RISK = '(.+)'$", source, re.M)
        self.assertIn("medium: styling, layout or ordinary logic", risk.group(1))


@unittest.skipUnless(HAVE_NODE, "needs node")
class ReReviewTest(unittest.TestCase):
    """From the second round each reviewer checks what changed and its own findings, not the whole PR."""

    def second_round(self):
        return run_workflow("build", {"check": [HIGH], "builder": [PR, {**PR, "head": "bbb2222"}],
                                      "qa": [CHANGES, APPROVE], "code review": [APPROVE] * 2,
                                      "security review": [APPROVE] * 2, "ready for your merge": [READIED]}, 12)

    def prompt(self, run, label):
        return next(c["prompt"] for c in run["calls"] if c["label"] == label)

    def test_a_reviewer_reviews_only_the_diff_since_its_last_review(self):
        qa = self.prompt(self.second_round(), "qa #12, round 2")
        self.assertIn("`git diff aaa1111..bbb2222`", qa)
        self.assertIn("Review only what changed since then", qa)
        self.assertIn("Leave alone what has not changed since your last review", qa)

    def test_a_reviewer_is_given_its_own_earlier_findings(self):
        run = self.second_round()
        self.assertIn("Your findings last time:\n- slug.py:3: empty title crashes", self.prompt(run, "qa #12, round 2"))
        self.assertIn("You raised nothing last time.", self.prompt(run, "security review #12, round 2"))

    def test_the_first_round_reviews_the_whole_pr(self):
        qa = self.prompt(self.second_round(), "qa #12, round 1")
        self.assertNotIn("Review only what changed", qa)

    def test_a_reviewer_that_joins_later_reviews_the_whole_pr(self):
        run = run_workflow("build", {"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                     "code review": [APPROVE, {**APPROVE, "risk": "high"}], "security review": [APPROVE],
                                     "ready for your merge": [READIED]}, 12)
        security = self.prompt(run, "security review #12, round 2")
        self.assertNotIn("Review only what changed", security)
        self.assertIn("Review only what changed", self.prompt(run, "code review #12, round 2"))

    def test_the_builder_returns_the_commit_its_branch_ends_at(self):
        builder = self.second_round()["calls"][1]
        self.assertIn("head", builder["schema"]["required"])


@unittest.skipUnless(HAVE_NODE, "needs node")
class ReachTest(unittest.TestCase):
    """Every finding says who can reach it, and the workflow holds the severity rule itself."""

    def run_workflow(self, replies):
        return run_workflow("build", {"check": [READY], "builder": [PR, PR], "code review": [APPROVE] * 2,
                                      "ready for your merge": [READIED], **replies}, 12)

    def test_every_finding_must_say_who_can_reach_it(self):
        qa = next(c for c in self.run_workflow({"qa": [APPROVE]})["calls"] if c["label"].startswith("qa"))
        finding = qa["schema"]["properties"]["findings"]["items"]
        self.assertIn("reach", finding["required"])
        self.assertIn("review_would_see", finding["required"])
        self.assertEqual(finding["properties"]["reach"]["enum"], ["anyone", "user", "outside", "trusted", "none"])

    def test_a_must_fix_only_a_trusted_writer_reaches_where_review_sees_it_is_a_nit(self):
        # On the website's #35, QA held a PR for a link only the founder's own facts could carry.
        run = self.run_workflow({"qa": [{"verdict": "changes", "findings": [TRUSTED]}]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        self.assertNotIn("builder #12, round 2", [c["label"] for c in run["calls"]])
        item = next(c["prompt"] for c in run["calls"] if c["label"].startswith("ready for your merge"))
        self.assertIn("**Left for you:** a review on the PR asks for changes the workflow rated as Nits", item)
        self.assertIn("- QA: facts.json: a fact written with a javascript: link", item)

    def test_a_loud_refusal_counts_as_caught(self):
        qa = next(c for c in self.run_workflow({"qa": [APPROVE]})["calls"] if c["label"].startswith("qa"))
        caught = qa["schema"]["properties"]["findings"]["items"]["properties"]["review_would_see"]["description"]
        self.assertIn("the product refuses the value loudly", caught)
        self.assertIn("gets past the product to readers", caught)

    def test_a_failure_only_a_trusted_writer_meets_and_the_build_refuses_is_a_nit(self):
        # On the website's #39 the build refused the founder's own file, with a stack trace.
        refused = {**TRUSTED, "where": "scripts/generate.js",
                   "what": "data-and-account-shapes: a wrong-shaped file is refused with a stack trace"}
        run = self.run_workflow({"qa": [{"verdict": "changes", "findings": [refused]}]})
        self.assertEqual(run["result"]["status"], "ready for your merge")
        self.assertNotIn("builder #12, round 2", [c["label"] for c in run["calls"]])

    def test_an_ordinary_slip_by_a_trusted_writer_stays_must_fix(self):
        slip = {**TRUSTED, "review_would_see": False, "what": "an empty fact breaks the page"}
        run = self.run_workflow({"qa": [{"verdict": "changes", "findings": [slip]}, APPROVE]})
        self.assertIn("builder #12, round 2", [c["label"] for c in run["calls"]])

    def test_what_anyone_can_reach_stays_must_fix(self):
        run = self.run_workflow({"qa": [{"verdict": "changes", "findings": [{**TRUSTED, "reach": "anyone"}]}, APPROVE]})
        self.assertIn("builder #12, round 2", [c["label"] for c in run["calls"]])

    def test_the_builder_sees_a_trusted_only_finding_as_a_nit_beside_real_ones(self):
        both = {"verdict": "changes", "findings": [TRUSTED, CHANGES["findings"][0]]}
        run = self.run_workflow({"qa": [both, APPROVE]})
        builder = next(c["prompt"] for c in run["calls"] if c["label"] == "builder #12, round 2")
        self.assertIn("- Nit: QA: facts.json:", builder)
        self.assertIn("\n- QA: slug.py:3: empty title crashes", builder)

    def test_a_trusted_only_repeat_does_not_stop_the_run(self):
        run = self.run_workflow({"qa": [CHANGES, {"verdict": "changes", "findings": [{**TRUSTED, "repeat": True}]}]})
        self.assertEqual(run["result"]["status"], "ready for your merge")


if __name__ == "__main__":
    unittest.main()
