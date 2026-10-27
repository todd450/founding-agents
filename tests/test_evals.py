"""The eval tasks are sound: each builds a trial, its reference answer passes its grader, and its
known-bad answer fails it, so no grader passes everything or nothing. No model is called."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "evals"
sys.path.insert(0, str(EVALS))
import run  # noqa: E402
import trial  # noqa: E402
from workflow_harness import HAVE_NODE  # noqa: E402

GH = [sys.executable, str(EVALS / "gh.py")]


def answer(task, kind):
    return json.loads((task["dir"] / kind / "answer.json").read_text())


class TaskTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def graded(self, name, kind):
        task = trial.load(name)
        folder = Path(self.folder.name) / f"{name}-{kind}"
        trial.make(task, folder)
        trial.apply(task, folder, answer(task, kind))
        return trial.grade(task, folder)

    def test_there_are_at_least_ten_tasks(self):
        self.assertGreaterEqual(len(trial.tasks()), 10, trial.tasks())

    def test_every_task_names_its_role_kind_and_origin(self):
        roles = {p.stem for p in (EVALS.parent / "agents").glob("*.md")} | {"build-check"}
        for name in trial.tasks():
            task = trial.load(name)
            with self.subTest(name):
                self.assertIn(task["role"], roles)
                self.assertIn(task["kind"], ("regression", "capability"))
                self.assertTrue(task["origin"] and task["class"] and task["summary"])
                self.assertIn(task["step"]["workflow"], ("build", "plan", "propose"))
                self.assertTrue(set(task.get("needs", [])) <= {"npm", "chrome"})

    def test_each_reference_answer_passes_its_grader(self):
        for name in trial.tasks():
            with self.subTest(name):
                if trial.missing(trial.load(name)):
                    self.skipTest(f"{name} needs {trial.missing(trial.load(name))}")
                checks = self.graded(name, "reference")
                self.assertTrue(checks)
                self.assertEqual([c for c, ok in checks if not ok], [])

    def test_each_known_bad_answer_fails_its_grader(self):
        for name in trial.tasks():
            with self.subTest(name):
                if trial.missing(trial.load(name)):
                    self.skipTest(f"{name} needs {trial.missing(trial.load(name))}")
                self.assertTrue([c for c, ok in self.graded(name, "bad") if not ok])

    def test_each_pr_under_review_passes_its_own_checks(self):
        # The flaw is one the reviewer has to find, not a red test it can read off.
        for name in trial.tasks():
            task = trial.load(name)
            if task["step"]["label"] not in ("qa", "code review"):
                continue
            with self.subTest(name):
                folder = Path(self.folder.name) / f"{name}-suite"
                trial.make(task, folder)
                checkout = trial.Trial(task, folder).branch(task["github"]["prs"][0]["headRefName"])
                self.assertTrue(trial.Trial(task, folder).suite(checkout))

    def test_the_integrator_task_fails_only_once_merged(self):
        task = trial.load("17-merge-that-breaks-main")
        folder = Path(self.folder.name) / "merge"
        work = trial.make(task, folder)
        checks = trial.Trial(task, folder)
        self.assertTrue(checks.suite(checks.branch("build/issue-19")))
        trial.git(work, "merge", "-q", "--no-edit", "build/issue-19")
        self.assertFalse(checks.suite(work))

    def test_the_red_line_is_graded_on_its_meaning_not_its_words(self):
        # Every phrasing here came from a real trial; the first run's grader failed all but the first.
        task = trial.load("12-status-from-the-repo")
        site = (EVALS / "fixtures" / "site" / "index.html").read_text()
        for line in ("No open red issue. Nothing is blocked.", "No red issue is open: nothing is holding merges.",
                     "No red issue is open.", 'Open <code>red</code> issues: <span class="red-count">none</span>.'):
            with self.subTest(line):
                folder = Path(self.folder.name) / str(abs(hash(line)))
                trial.make(task, folder)
                trial.apply(task, folder, answer(task, "reference"))
                checkout = trial.Trial(task, folder).branch("build/issue-12")
                (checkout / "index.html").write_text(site.replace("No open red issue. Nothing is blocked.", line))
                trial.git(checkout, "commit", "-q", "--allow-empty", "-am", "Reword the red line")
                trial.git(checkout, "push", "-q", "origin", "build/issue-12")
                checks = dict(trial.grade(task, folder))
                self.assertTrue(checks["the red line says none is open"])

    def test_some_tasks_want_a_stop_a_refusal_or_an_approval(self):
        # One-sided evals make one-sided agents: a role that sends everything back must not score well.
        wanted = [trial.load(n).get("right_answer") for n in trial.tasks()]
        self.assertGreaterEqual(sum(w in ("stop", "approve", "refuse") for w in wanted), 5)


@unittest.skipUnless(HAVE_NODE, "needs node")
class RunnerTest(unittest.TestCase):
    def test_each_task_runs_the_prompt_its_workflow_sends_as_that_steps_agent_and_model(self):
        expected = {"code-reviewer": "founding-agents:code-reviewer", "qa": "founding-agents:qa",
                    "builder": "founding-agents:builder", "integrator": "founding-agents:integrator",
                    "product-lead": "founding-agents:product-lead", "architect": "founding-agents:architect",
                    "build-check": None}
        for name in trial.tasks():
            task = trial.load(name)
            with self.subTest(name):
                call = run.capture(task)
                self.assertEqual(call["agentType"], expected[task["role"]])
                self.assertIn(call["model"], ("opus", "sonnet", "haiku"))
                self.assertTrue(call["schema"]["required"])

    def test_a_repeat_review_and_a_continued_pr_get_their_second_round_prompts(self):
        self.assertIn("as a repeat", run.capture(trial.load("06-same-finding-comes-back"))["prompt"])
        self.assertIn("Continue it rather than starting again", run.capture(trial.load("13-fix-the-pattern-not-the-instance"))["prompt"])

    def test_a_trial_never_bills_an_api_key_or_skips_the_plans_login(self):
        call = run.capture(trial.load("01-colour-test-as-regexes"))
        cmd = run.command(call, "opus")
        self.assertNotIn("--bare", cmd)
        self.assertEqual(cmd[cmd.index("--plugin-dir") + 1], str(EVALS.parent))
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
        try:
            env = run.environment(Path("/tmp/t"))
        finally:
            del os.environ["ANTHROPIC_API_KEY"]
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertTrue(env["PATH"].startswith(str(EVALS / "bin")))
        self.assertEqual(env["GH_CONFIG_DIR"], "/tmp/t/gh-config")


class ResultTest(unittest.TestCase):
    SCHEMA = {"required": ["verdict", "findings"]}

    def test_reads_the_last_complete_json_block_in_a_reply(self):
        reply = 'Draft:\n```json\n{"verdict": "x"}\n```\nFinal:\n```json\n{"verdict": "approve", "findings": []}\n```'
        self.assertEqual(run.returned(reply, self.SCHEMA), {"verdict": "approve", "findings": []})
        self.assertIsNone(run.returned('```json\n{"verdict": "approve"}\n```', self.SCHEMA))
        self.assertIsNone(run.returned("No JSON here.", self.SCHEMA))

    def test_only_an_agent_step_is_asked_for_json_in_its_reply(self):
        call = {"prompt": "Review.", "schema": self.SCHEMA}
        self.assertIn("```json", run.prompt({**call, "agentType": "founding-agents:qa"}))
        self.assertEqual(run.prompt({**call, "agentType": None}), "Review.")

    def test_pass_rate_counts_trials_and_pass_k_counts_tasks_whose_every_trial_passed(self):
        def result(name, passed):
            return {"task": name, "role": "qa", "model": "opus", "kind": "regression", "passed": passed,
                    "cost": 0.5, "new": 1, "cached": 2, "out": 3, "checks": []}
        results = [result("a", True), result("a", True), result("a", True),
                   result("b", True), result("b", False), result("b", True)]
        group = run.summary(results)[("qa", "opus")]
        self.assertEqual((group["passed"], group["trials"]), (5, 6))
        self.assertEqual((group["all_passed"], group["tasks"]), (1, 2))
        self.assertIn("| qa | opus | 2 | 83% | 50% |", run.markdown(results, 3))


class GhStandInTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.task = trial.load(trial.tasks()[0])
        self.work = trial.make(self.task, Path(self.folder.name) / "t")
        self.env = {**os.environ, "EVAL_GH_STATE": str(Path(self.folder.name) / "t" / "github.json")}

    def tearDown(self):
        self.folder.cleanup()

    def gh(self, *args, stdin=None):
        return subprocess.run([*GH, *args], cwd=self.work, env=self.env, input=stdin, capture_output=True, text=True)

    def test_serves_the_task_issue_as_json_and_through_jq(self):
        number = self.task["github"]["issues"][0]["number"]
        shown = json.loads(self.gh("issue", "view", str(number), "--json", "title,labels").stdout)
        self.assertEqual(set(shown), {"title", "labels"})
        self.assertEqual(self.gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").stdout.strip(),
                         self.task["github"]["repo"])

    def test_diffs_and_checks_out_the_pr_branch(self):
        number = self.task["github"]["prs"][0]["number"]
        self.assertIn("diff --git", self.gh("pr", "diff", str(number)).stdout)
        self.assertEqual(self.gh("pr", "checkout", str(number)).returncode, 0)
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=self.work, capture_output=True, text=True)
        self.assertEqual(branch.stdout.strip(), self.task["github"]["prs"][0]["headRefName"])

    def test_records_what_the_agent_posts(self):
        number = self.task["github"]["prs"][0]["number"]
        self.gh("pr", "comment", str(number), "--body-file", "-", stdin="**Code review: Approve**")
        posted = json.loads((Path(self.folder.name) / "t" / "github.json").read_text())["posted"]
        self.assertEqual(posted, [{"kind": "pr comment", "number": number, "body": "**Code review: Approve**"}])

    def test_refuses_what_it_does_not_serve(self):
        self.assertNotEqual(self.gh("api", "repos/o/r").returncode, 0)


if __name__ == "__main__":
    unittest.main()
