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
import trial  # noqa: E402

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

    def test_there_are_ten_to_twenty_tasks(self):
        self.assertTrue(10 <= len(trial.tasks()) <= 20, trial.tasks())

    def test_every_task_names_its_role_kind_and_origin(self):
        roles = {p.stem for p in (EVALS.parent / "agents").glob("*.md")} | {"build-check"}
        for name in trial.tasks():
            task = trial.load(name)
            with self.subTest(name):
                self.assertIn(task["role"], roles)
                self.assertIn(task["kind"], ("regression", "capability"))
                self.assertTrue(task["origin"] and task["class"] and task["summary"])
                self.assertIn(task["step"]["workflow"], ("build", "plan", "propose"))

    def test_each_reference_answer_passes_its_grader(self):
        for name in trial.tasks():
            with self.subTest(name):
                checks = self.graded(name, "reference")
                self.assertTrue(checks)
                self.assertEqual([c for c, ok in checks if not ok], [])

    def test_each_known_bad_answer_fails_its_grader(self):
        for name in trial.tasks():
            with self.subTest(name):
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

    def test_some_tasks_want_a_stop_a_refusal_or_an_approval(self):
        # One-sided evals make one-sided agents: a role that sends everything back must not score well.
        wanted = [trial.load(n).get("right_answer") for n in trial.tasks()]
        self.assertGreaterEqual(sum(w in ("stop", "approve", "refuse") for w in wanted), 5)


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
