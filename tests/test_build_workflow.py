"""The build workflow checks the ticket, loops builder and reviewers, and only then merges."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

READY = {"ready": True, "reason": "", "repo": "o/r", "title": "Add slugify", "body": "Turn titles into slugs.", "decision": "",
         "unseen": [], "open_pr": 0, "risk": "medium", "parts": []}
PR = {"pr_number": 4, "pr_url": "https://github.com/o/r/pull/4", "head": "aaa1111", "stopped_because": ""}
APPROVE = {"verdict": "approve", "findings": []}
CHANGES = {"verdict": "changes", "findings": [{"must_fix": True, "reach": "anyone", "review_would_see": False,
                                               "where": "slug.py:3", "what": "empty title crashes", "repeat": False}]}
REPEATED = {"verdict": "changes", "findings": [{**CHANGES["findings"][0], "repeat": True}]}
MERGED = {"merged": True, "merge_commit": "abc1234", "reason": ""}
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
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")
        self.assertEqual(self.labels(run), ["check #12", "builder #12, round 1", "qa #12, round 1", "code review #12, round 1",
                                            "integrator, PR #4", "tidy worktrees", "run report"])

    def test_the_integrator_is_told_not_to_rerun_checks_when_main_has_not_moved(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "integrator": [MERGED]})
        integrator = next(c for c in run["calls"] if c["label"].startswith("integrator"))
        self.assertIn("without rerunning them when `main` has not moved", integrator["prompt"])

    def test_each_role_runs_as_its_plugin_agent_and_the_builder_in_a_worktree(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "integrator": [MERGED]})
        builder, qa, code, integrator = run["calls"][1:5]
        self.assertEqual((builder["agentType"], builder["isolation"], builder["model"]),
                         ("founding-agents:builder", "worktree", "opus"))
        self.assertEqual((qa["agentType"], qa["model"]), ("founding-agents:qa", "opus"))
        self.assertEqual((code["agentType"], code["model"]), ("founding-agents:code-reviewer", "opus"))
        self.assertEqual(integrator["agentType"], "founding-agents:integrator")

    def test_reviewers_see_the_issue_but_not_the_builders_reasoning(self):
        run = self.run_workflow({"check": [READY], "builder": [{**PR, "stopped_because": ""}],
                                 "qa": [APPROVE], "integrator": [MERGED]})
        prompt = run["calls"][2]["prompt"]
        self.assertIn("Turn titles into slugs.", prompt)
        self.assertNotIn("Return the PR's number", prompt)

    def test_the_founders_pick_reaches_the_builder_and_qa(self):
        ticket = {**READY, "decision": "B, with a shorter headline (mockups on propose/issue-12)"}
        run = self.run_workflow({"check": [ticket], "builder": [PR], "qa": [APPROVE], "integrator": [MERGED]})
        for call in run["calls"][1:3]:
            self.assertIn("The founder decided: B, with a shorter headline", call["prompt"])

    def test_a_finished_run_posts_its_report_on_the_issue(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "integrator": [MERGED],
                                 "run report": [{"comment_url": "https://github.com/o/r/issues/12#c1", "reason": ""}]})
        report = run["calls"][-1]
        self.assertEqual((report["label"], report["model"]), ("run report", "haiku"))
        self.assertIn("--workflow build --issue 12 --budget 12 --outcome merged --post", report["prompt"])
        self.assertEqual(run["result"]["report"], "https://github.com/o/r/issues/12#c1")

    def test_a_stalled_run_still_posts_its_report_and_says_it_stopped(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3})
        self.assertEqual(self.labels(run)[-1], "run report")
        self.assertIn("--outcome stopped", run["calls"][-1]["prompt"])

    def test_findings_go_back_to_the_builder_on_the_same_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("gh pr checkout 4", second)
        self.assertIn("- QA: slug.py:3: empty title crashes", second)

    def test_a_builder_fixing_a_pr_is_asked_to_keep_its_screenshots_current(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        prompts = [call["prompt"] for call in run["calls"] if call["label"].startswith("builder")]
        self.assertEqual(len(prompts), 2)
        for prompt in prompts:
            self.assertIn("retake the after screenshots", prompt)

    def test_three_send_backs_go_to_the_founder_and_nothing_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3})
        self.assertIn("the founder decides", run["result"]["status"])
        self.assertNotIn("integrator, PR #4", self.labels(run))

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
        self.assertEqual(self.labels(run)[-2:], ["tidy worktrees", "run report"])

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

    def test_the_builder_leaves_ci_to_the_code_reviewer_and_the_integrator(self):
        agents = Path(__file__).resolve().parent.parent / "agents"
        builder = " ".join((agents / "builder.md").read_text().split())
        code = " ".join((agents / "code-reviewer.md").read_text().split())
        integrator = (agents / "integrator.md").read_text()
        self.assertIn("Run `check.sh` before you push, then return the PR without waiting for CI", builder)
        self.assertIn("`gh pr checks <number> --watch`", code)
        self.assertIn("A failing check is a finding that must be fixed", code)
        self.assertIn("whose required checks are green", integrator)

    def test_new_findings_in_a_later_round_get_another_round(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES, CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")

    def test_reviewers_are_asked_to_mark_repeats_only_after_an_earlier_review(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        first, second = [call["prompt"] for call in run["calls"] if call["label"].startswith("qa")]
        self.assertNotIn("as a repeat", first)
        self.assertIn("as a repeat", second)

    def test_a_repeat_is_only_a_finding_from_an_earlier_round(self):
        # On the website's #27, a reviewer counted a finding the other reviewers had raised minutes
        # earlier in the same round as a repeat, and the run stopped a round early.
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        qa, code = [call["prompt"] for call in run["calls"] if call["label"].startswith(("qa", "code review"))][2:]
        for prompt in (qa, code):
            self.assertIn("a finding only they raised is not a repeat", prompt)
            self.assertIn("Nor is one an earlier round marked as a Nit", prompt)
        # Each reviewer is given its own findings from last time, not the other reviewers'.
        self.assertIn("Your findings last time:\n- slug.py:3: empty title crashes", qa)
        self.assertIn("You raised nothing last time.", code)

    def test_a_continued_pr_gets_the_rule_but_no_list_it_cannot_know(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "qa": [APPROVE], "integrator": [MERGED]})
        qa = next(call["prompt"] for call in run["calls"] if call["label"].startswith("qa"))
        self.assertIn("a finding only they raised is not a repeat", qa)
        self.assertNotIn("Your findings last time", qa)
        self.assertIn("If you reviewed this PR before", qa)
        self.assertIn("gh pr view <number> --json commits", qa)

    def test_qa_and_code_review_run_side_by_side_and_both_must_approve(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "qa": [APPROVE, APPROVE],
                                    "code review": [CHANGES, CODE_OK],
                                    "integrator": [MERGED]})
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
                                 "security review": [APPROVE], "integrator": [MERGED]},
                                slow={"qa": 30, "code review": 30, "security review": 30})
        reviews = [e for e in run["events"] if " #12, round 1" in e and not e.endswith("builder #12, round 1")]
        self.assertEqual([e.split()[0] for e in reviews], ["start"] * 3 + ["end"] * 3)
        security = next(call for call in run["calls"] if call["label"] == "security review #12, round 1")
        self.assertEqual((security["agentType"], security["model"]), ("founding-agents:security-reviewer", "opus"))
        self.assertEqual(run["result"]["status"], "merged")

    def test_a_security_review_the_issue_asked_for_runs_once_even_when_code_review_flags_the_diff(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE],
                                 "code review": [{**CODE_OK, "risk": "high"}], "security review": [APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual([label for label in self.labels(run) if label.startswith("security")], ["security review #12, round 1"])

    def test_findings_from_the_early_security_review_go_back_to_the_builder(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR, PR], "qa": [APPROVE, APPROVE],
                                 "security review": [INSECURE, APPROVE], "integrator": [MERGED]})
        second = next(call["prompt"] for call in run["calls"] if call["label"] == "builder #12, round 2")
        self.assertIn("- Security: api.py:9: any user reads any draft", second)
        self.assertIn("security review #12, round 2", self.labels(run))
        self.assertEqual(run["result"]["status"], "merged")

    def test_a_late_security_review_that_returns_nothing_stops_the_run(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE],
                                 "code review": [{**CODE_OK, "risk": "high"}]})
        self.assertEqual(run["result"]["status"], "stopped in review")

    def test_an_early_security_review_that_returns_nothing_stops_the_run(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE]})
        self.assertEqual(run["result"]["status"], "stopped in review")
        self.assertNotIn("integrator, PR #4", self.labels(run))

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
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "integrator": [MERGED]})
        self.assertFalse([label for label in self.labels(run) if label.startswith("security")])

    def test_the_check_is_told_an_open_pr_never_makes_the_issue_unready(self):
        # On the website's #27 the check read an open PR as "already being built" and skipped it, so
        # the six issues that build after it never started.
        prompt = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]["prompt"]
        self.assertIn("An open PR is never a reason to stop", prompt)

    def test_an_open_pr_for_the_issue_is_continued_not_started_again(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}],
                                 "qa": [APPROVE], "integrator": [MERGED]})
        builder, reviewer = run["calls"][1:3]
        self.assertIn("PR #9 already builds issue #12", builder["prompt"])
        self.assertIn("gh pr checkout 9", builder["prompt"])
        self.assertIn("Do not open a new PR", builder["prompt"])
        self.assertIn("as a repeat", reviewer["prompt"])
        self.assertEqual(run["result"]["status"], "merged")

    def test_a_continued_pr_that_repeats_a_finding_goes_to_the_founder_at_once(self):
        run = self.run_workflow({"check": [{**READY, "open_pr": 9}], "builder": [{**PR, "pr_number": 9}, PR],
                                 "qa": [REPEATED]})
        self.assertIn("the same finding came back unfixed", run["result"]["status"])
        self.assertNotIn("builder #12, round 2", self.labels(run))

    def test_the_check_looks_for_an_open_pr_on_the_issue(self):
        check = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]})["calls"][0]
        self.assertIn("build/issue-12", check["prompt"])
        self.assertIn("open_pr", check["prompt"])

    def test_every_run_after_the_check_tidies_worktrees_before_its_report(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "qa": [CHANGES] * 3,
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
                                 "integrator": [MERGED]})
        self.assertEqual(reviewers(run), [("code review", "sonnet")])
        self.assertEqual(run["result"]["status"], "merged")
        self.assertIn("--budget 5 ", run["calls"][-1]["prompt"])

    def test_a_medium_risk_issue_gets_qa_and_code_review_on_opus(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "qa": [APPROVE], "code review": [APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(reviewers(run), [("qa", "opus"), ("code review", "opus")])

    def test_a_high_risk_issue_gets_all_three_on_opus(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR], "qa": [APPROVE], "code review": [APPROVE],
                                 "security review": [APPROVE], "integrator": [MERGED]})
        self.assertEqual(reviewers(run), [("qa", "opus"), ("code review", "opus"), ("security review", "opus")])
        self.assertIn("--budget 20 ", run["calls"][-1]["prompt"])

    def test_an_issue_with_no_known_risk_gets_the_most_review(self):
        run = self.run_workflow({"check": [{**READY, "risk": "unsure"}], "builder": [PR], "qa": [APPROVE],
                                 "code review": [APPROVE], "security review": [APPROVE], "integrator": [MERGED]})
        self.assertEqual([r for r, _ in reviewers(run)], ["qa", "code review", "security review"])

    def test_a_reviewer_that_raises_the_tier_brings_in_its_reviewers_at_once(self):
        run = self.run_workflow({"check": [{**READY, "risk": "low"}], "builder": [PR],
                                 "code review": [{**APPROVE, "risk": "high"}], "qa": [APPROVE],
                                 "security review": [APPROVE], "integrator": [MERGED]})
        self.assertEqual(reviewers(run), [("code review", "sonnet"), ("qa", "opus"), ("security review", "opus")])
        self.assertEqual(run["result"]["status"], "merged")
        self.assertIn("--budget 20 ", run["calls"][-1]["prompt"])

    def test_the_raised_tier_holds_for_the_next_round(self):
        run = self.run_workflow({"check": [{**READY, "risk": "low"}], "builder": [PR, PR],
                                 "code review": [{**CHANGES, "risk": "medium"}, APPROVE], "qa": [APPROVE, APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(reviewers(run, 2), [("qa", "opus"), ("code review", "opus")])

    def test_a_reviewer_cannot_lower_the_tier(self):
        run = self.run_workflow({"check": [HIGH], "builder": [PR, PR], "qa": [{**CHANGES, "risk": "low"}, APPROVE],
                                 "code review": [{**APPROVE, "risk": "low"}] * 2, "security review": [APPROVE] * 2,
                                 "integrator": [MERGED]})
        self.assertEqual(reviewers(run, 2), [("qa", "opus"), ("code review", "opus"), ("security review", "opus")])

    def test_build_and_plan_rate_risk_in_the_same_words(self):
        root = Path(__file__).resolve().parent.parent / "workflows"
        risk = [re.search(r"^const RISK = '(.+)'$", (root / name).read_text(), re.M) for name in ("build.js", "plan.js")]
        self.assertTrue(all(risk))
        self.assertEqual(risk[0].group(1), risk[1].group(1))
        self.assertIn("medium: styling, layout or ordinary logic", risk[0].group(1))


@unittest.skipUnless(HAVE_NODE, "needs node")
class ReReviewTest(unittest.TestCase):
    """From the second round each reviewer checks what changed and its own findings, not the whole PR."""

    def second_round(self):
        return run_workflow("build", {"check": [HIGH], "builder": [PR, {**PR, "head": "bbb2222"}],
                                      "qa": [CHANGES, APPROVE], "code review": [APPROVE] * 2,
                                      "security review": [APPROVE] * 2, "integrator": [MERGED]}, 12)

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
                                     "integrator": [MERGED]}, 12)
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
                                      "integrator": [MERGED], **replies}, 12)

    def test_every_finding_must_say_who_can_reach_it(self):
        qa = next(c for c in self.run_workflow({"qa": [APPROVE]})["calls"] if c["label"].startswith("qa"))
        finding = qa["schema"]["properties"]["findings"]["items"]
        self.assertIn("reach", finding["required"])
        self.assertIn("review_would_see", finding["required"])
        self.assertEqual(finding["properties"]["reach"]["enum"], ["anyone", "user", "outside", "trusted", "none"])

    def test_a_must_fix_only_a_trusted_writer_reaches_where_review_sees_it_is_a_nit(self):
        # On the website's #35, QA held a PR for a link only the founder's own facts could carry.
        run = self.run_workflow({"qa": [{"verdict": "changes", "findings": [TRUSTED]}]})
        self.assertEqual(run["result"]["status"], "merged")
        self.assertNotIn("builder #12, round 2", [c["label"] for c in run["calls"]])
        integrator = next(c["prompt"] for c in run["calls"] if c["label"].startswith("integrator"))
        self.assertIn("Count that review as an approval", integrator)
        self.assertIn("- QA: facts.json: a fact written with a javascript: link", integrator)
        self.assertIn("left for the founder", integrator)

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
        self.assertEqual(run["result"]["status"], "merged")


@unittest.skipUnless(HAVE_NODE, "needs node")
class BudgetTest(unittest.TestCase):
    """An issue that passes its tier's budget stops for the founder, the way three rounds do."""

    def run_workflow(self, spent, ticket=READY, rounds=3, **replies):
        base = {"check": [ticket], "builder": [PR] * rounds, "qa": [CHANGES] * (rounds - 1) + [APPROVE],
                "code review": [APPROVE] * rounds, "integrator": [MERGED], "spend": [{"dollars": d} for d in spent]}
        return run_workflow("build", {**base, **replies}, 12)

    def labels(self, run):
        return [c["label"] for c in run["calls"]]

    def test_an_issue_past_its_budget_stops_before_another_round(self):
        run = self.run_workflow([13.0])
        self.assertEqual(run["result"]["status"], "over its medium-risk budget, $13.00 against $12; the founder decides")
        self.assertEqual(run["result"]["pr"], PR["pr_url"])
        self.assertEqual(run["result"]["findings"][0]["what"], "empty title crashes")
        self.assertNotIn("builder #12, round 2", self.labels(run))
        self.assertIn("--outcome stopped", run["calls"][-1]["prompt"])

    def test_an_issue_within_its_budget_goes_on(self):
        run = self.run_workflow([6.0, 11.0])
        self.assertEqual(run["result"]["status"], "merged")

    def test_each_tier_has_its_own_budget(self):
        self.assertIn("over its low-risk budget",
                      self.run_workflow([6.0], ticket={**READY, "risk": "low"},
                                        **{"code review": [CHANGES, APPROVE]})["result"]["status"])
        self.assertEqual(self.run_workflow([19.0, 19.5], ticket=HIGH, **{"security review": [APPROVE] * 3})
                         ["result"]["status"], "merged")

    def test_the_spend_is_read_from_the_runs_logs_on_haiku(self):
        spend = next(c for c in self.run_workflow([1.0, 2.0])["calls"] if c["label"].startswith("spend"))
        self.assertEqual((spend["label"], spend["model"]), ("spend #12", "haiku"))
        self.assertIn("run-report skill", spend["prompt"])
        self.assertIn("--workflow build --issue 12 --spent-on 12", spend["prompt"])

    def test_a_spend_it_cannot_read_does_not_stop_the_run(self):
        self.assertEqual(self.run_workflow([])["result"]["status"], "merged")

    def test_spend_is_read_only_before_another_round(self):
        approved = self.run_workflow([], rounds=1)
        self.assertFalse([label for label in self.labels(approved) if label.startswith("spend")])
        third = self.run_workflow([1.0, 1.0], **{"qa": [CHANGES] * 3})
        self.assertEqual([label for label in self.labels(third) if label.startswith("spend")], ["spend #12", "spend #12"])


def part(n, *after):
    return {"number": n, "after": list(after)}


def built(n):
    return {"pr_number": 100 + n, "pr_url": f"https://github.com/o/r/pull/{100 + n}", "head": f"c{n}", "stopped_because": ""}


@unittest.skipUnless(HAVE_NODE, "needs node")
class BuildBriefTest(unittest.TestCase):
    """Given a brief the architect cut, build builds its issues in parallel and merges one at a time."""

    BRIEF = {**READY, "title": "Brief: pricing", "parts": [part(21), part(32, 21), part(43)]}

    def run_brief(self, args=7, slow=None, **overrides):
        replies = {"check #7": [self.BRIEF], "check #21": [READY], "check #32": [READY], "check #43": [READY],
                   "builder #21": [built(21)], "builder #32": [built(32)], "builder #43": [built(43)],
                   "qa": [APPROVE] * 3, "integrator": [MERGED] * 3}
        replies.update(overrides)
        return run_workflow("build", with_code_review(replies), args, slow)

    def labels(self, run):
        return [call["label"] for call in run["calls"]]

    def test_builds_every_issue_and_reports_once_on_the_brief(self):
        run = self.run_brief()
        self.assertEqual(run["result"]["status"], "3 of 3 issues merged")
        self.assertEqual(sorted(r["issue"] for r in run["result"]["issues"]), [21, 32, 43])
        self.assertEqual(self.labels(run).count("run report"), 1)
        self.assertIn("--workflow build --issue 7 ", run["calls"][-1]["prompt"])
        self.assertIn("--outcome merged", run["calls"][-1]["prompt"])

    def test_an_issue_waits_until_the_one_it_builds_after_has_merged(self):
        labels = self.labels(self.run_brief())
        self.assertLess(labels.index("integrator, PR #121"), labels.index("check #32"))

    def test_the_integrator_merges_one_pr_at_a_time(self):
        events = self.run_brief(slow={"integrator": 30})["events"]
        merges = [e for e in events if "integrator" in e]
        self.assertEqual([e.split()[0] for e in merges], ["start", "end"] * 3)

    def test_runs_two_builders_at_once_by_default_and_one_when_asked(self):
        two = self.labels(self.run_brief())
        self.assertLess(two.index("check #43"), two.index("builder #21, round 1"))
        one = self.labels(self.run_brief(args="7 1"))
        self.assertLess(one.index("integrator, PR #121"), one.index("check #43"))

    def test_the_number_of_builders_comes_from_the_founder_up_to_four(self):
        for args, builders in (("7", 2), ("#7 3", 3), ("7 9", 4), ({"issue": 7, "builders": 3}, 3)):
            self.assertEqual(self.run_brief(args=args)["result"]["builders"], builders, args)

    def test_an_issue_after_one_that_did_not_merge_is_not_started(self):
        stopped = {"pr_number": 0, "pr_url": "", "stopped_because": "split it in two"}
        run = self.run_brief(**{"builder #21": [stopped]})
        by_issue = {r["issue"]: r for r in run["result"]["issues"]}
        self.assertEqual(by_issue[21]["status"], "stopped in build")
        self.assertEqual(by_issue[32]["status"], "not started")
        self.assertIn("#21", by_issue[32]["reason"])
        self.assertEqual(by_issue[43]["status"], "merged")
        self.assertNotIn("check #32", self.labels(run))
        self.assertIn("--outcome stopped", run["calls"][-1]["prompt"])

    def test_each_issue_is_checked_on_its_own_before_it_is_built(self):
        run = self.run_brief(**{"check #43": [{**READY, "ready": False, "reason": "a red issue is open"}]})
        by_issue = {r["issue"]: r for r in run["result"]["issues"]}
        self.assertEqual(by_issue[43], {"issue": 43, "status": "not started", "reason": "a red issue is open"})
        self.assertNotIn("builder #43, round 1", self.labels(run))

    def test_a_briefs_report_budget_is_its_issues_budgets_added_up(self):
        run = self.run_brief(**{"check #43": [{**READY, "risk": "low"}]})
        self.assertIn("--budget 29 ", run["calls"][-1]["prompt"])

    def test_spend_on_a_briefs_issue_is_read_from_the_briefs_run(self):
        run = self.run_brief(**{"builder #21": [built(21), built(21)], "qa": [CHANGES] + [APPROVE] * 3})
        spend = next(c["prompt"] for c in run["calls"] if c["label"].startswith("spend"))
        self.assertIn("--workflow build --issue 7 --spent-on 21", spend)

    def test_the_check_recognises_a_brief_by_the_issues_cut_from_it(self):
        prompt = self.run_brief()["calls"][0]["prompt"]
        self.assertIn('"Part of #7" in:body', prompt.replace('\\"', '"'))
        self.assertIn("Return each open one as parts", prompt)


if __name__ == "__main__":
    unittest.main()
