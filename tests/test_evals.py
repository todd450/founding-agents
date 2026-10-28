"""The eval tasks are sound: each builds a trial, its reference answer passes its grader, and its
known-bad answer fails it, so no grader passes everything or nothing. No model is called."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
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
                (checkout / "index.html").write_text(site.replace("No open red issue.", line))
                trial.git(checkout, "commit", "-q", "--allow-empty", "-am", "Reword the red line")
                trial.git(checkout, "push", "-q", "origin", "build/issue-12")
                checks = dict(trial.grade(task, folder))
                self.assertTrue(checks["the red line says none is open"])

    def regraded(self, name, branch, files):
        """Grade a task's reference answer after an agent's own wording of some files replaces it."""
        task = trial.load(name)
        folder = Path(self.folder.name) / f"{name}-{abs(hash(str(files)))}"
        trial.make(task, folder)
        trial.apply(task, folder, answer(task, "reference"))
        checkout = trial.Trial(task, folder).branch(branch)
        for path, edit in files.items():
            target = checkout / path
            target.write_text(edit(target.read_text() if target.exists() else ""))
        trial.git(checkout, "add", "-A")
        trial.git(checkout, "commit", "-q", "--allow-empty", "-m", "An agent's own wording")
        trial.git(checkout, "push", "-q", "origin", branch)
        return dict(trial.grade(task, folder))

    def test_a_step_with_extra_attributes_is_still_read(self):
        # An Opus builder added data-state to each step's state; the first grader read none of them.
        checks = self.regraded("12-status-from-the-repo", "build/issue-12", {
            "index.html": lambda page: page.replace('<span class="step-state done">', '<span class="step-state done" data-state="done">')})
        self.assertTrue(all(ok for name, ok in checks.items() if name.startswith("step ")), checks)

    def test_a_docstring_that_mentions_the_count_does_not_pin_it(self):
        # Two Opus builders parsed the count in their tests and named "four rounds" only in docstrings.
        test = '''"""The record's count of the shell's review rounds."""

import unittest


def count_before(text, noun):
    """The number a claim puts in front of `noun`, e.g. 'four rounds of review' -> 4."""
    return 4


class RecordTest(unittest.TestCase):
    def test_the_count_matches_the_prs_reviews(self):
        self.assertEqual(count_before("", "rounds"), 4)
'''
        checks = self.regraded("22-count-its-own-review-rounds", "build/issue-26", {"tests/test_count.py": lambda _: test})
        self.assertTrue(checks["no test pins the record's wording"])

    def test_some_tasks_want_a_stop_a_refusal_or_an_approval(self):
        # One-sided evals make one-sided agents: a role that sends everything back must not score well.
        wanted = [trial.load(n).get("right_answer") for n in trial.tasks()]
        self.assertGreaterEqual(sum(w in ("stop", "approve", "refuse") for w in wanted), 5)



class FindingsTest(unittest.TestCase):
    def test_a_grader_counts_must_fix_findings_the_way_build_does(self):
        trusted = {"must_fix": True, "reach": "trusted", "review_would_see": True, "where": "facts", "what": "a crafted link"}
        slip = {**trusted, "review_would_see": False, "what": "an empty fact"}
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "output.json").write_text(json.dumps({"findings": [trusted, slip]}))
            (Path(folder) / "github.json").write_text(json.dumps({"posted": []}))
            checks = trial.Trial({}, folder)
            self.assertEqual([f["what"] for f in checks.findings(must_fix=True)], ["an empty fact"])
            self.assertEqual([f["what"] for f in checks.findings(must_fix=False)], ["a crafted link"])

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
        self.assertEqual(env["ANTHROPIC_DEFAULT_OPUS_MODEL"], "claude-opus-5-5")

    def test_a_trial_can_reach_neither_github_nor_the_real_holdouts(self):
        # On 27 Oct 2026 trial QA pushed eval scenarios to the website's real holdouts repo.
        folder = Path(tempfile.mkdtemp())
        os.environ["GH_TOKEN"] = "ghp_test"
        try:
            env = run.environment(folder)
        finally:
            del os.environ["GH_TOKEN"]
        self.assertNotIn("GH_TOKEN", env)
        for remote in ("https://github.com/todd450/founding-agents-site-holdouts.git",
                       "git@github.com:todd450/founding-agents-site-holdouts.git"):
            with self.subTest(remote):
                done = subprocess.run(["git", "ls-remote", remote], env=env, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(done.returncode, 0)
                self.assertIn(str(folder / "no-github"), done.stderr)
        cmd = run.command(run.capture(trial.load("11-a-correct-page")), "opus")
        hook = json.loads(cmd[cmd.index("--settings") + 1])["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        for tool_input, blocked in (({"command": "cd ~/.founding-agents/holdouts/o/n && git pull"}, True),
                                    ({"command": "gh pr create --repo o/n-holdouts"}, True),
                                    ({"file_path": "/Users/x/.founding-agents/holdouts/o/n/README.md"}, True),
                                    ({"command": "python3 -m unittest discover -s tests"}, False)):
            with self.subTest(tool_input):
                event = {"agent_type": "founding-agents:qa", "tool_input": tool_input}
                done = subprocess.run(hook, shell=True, input=json.dumps(event), capture_output=True, text=True)
                self.assertEqual(done.returncode, 2 if blocked else 0)


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

    def test_flags_fixed_scratch_paths_and_ports_but_not_private_ones(self):
        used = "cp index.html /tmp/index.html.bak; d=$(mktemp -d); cd $TMPDIR/x; python3 -m http.server 8777; python3 -m http.server 0"
        self.assertEqual(run.FIXED.findall(used), ["/tmp/index.html.bak", "http.server 8777"])

    def test_flags_killing_by_a_pattern_but_not_by_its_own_pid(self):
        commands = ['python3 -u -m http.server 0 > /var/folders/x/tmp.Ab12Cd/server.log 2>&1 & echo $!',
                    'kill 48213', 'pkill -f "http.server 0"; ls', "killall python3",
                    "kill $(pgrep -f http.server)"]
        log = Path(tempfile.mkdtemp()) / "session.jsonl"
        log.write_text("\n".join(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": c}}]}}) for c in commands))
        self.assertEqual(run.shared(log), ['kill $(pgrep -f http.server)', 'killall python3', 'pkill -f "http.server 0"'])

    def test_pass_rate_counts_trials_and_pass_k_counts_tasks_whose_every_trial_passed(self):
        def result(name, passed):
            return {"task": name, "role": "qa", "model": "opus", "kind": "regression", "passed": passed,
                    "cost": 0.5, "new": 1, "cached": 2, "out": 3, "checks": []}
        results = [result("a", True), result("a", True), result("a", True),
                   result("b", True), result("b", False), result("b", True)]
        group = run.summary(results)[("qa", "opus")]
        self.assertEqual((group["passed"], group["trials"]), (5, 6))
        self.assertEqual((group["all_passed"], group["tasks"]), (1, 2))
        self.assertIn("| qa | opus | 2 | 3 | 83% | 50% |", run.markdown(results, 3))


class ScheduleTest(unittest.TestCase):
    def test_trials_that_share_an_issue_or_pr_number_never_run_at_once(self):
        def task(name, *numbers):
            return {"name": name, "github": {"issues": [{"number": n} for n in numbers], "prs": []}}
        a, b, c = task("a", 5, 8), task("b", 8), task("c", 12)
        running, clashes, lock = [], [], threading.Lock()

        def trial_of(task, i):
            with lock:
                clashes.extend((other["name"], task["name"]) for other in running if run.numbers(other) & run.numbers(task))
                running.append(task)
            time.sleep(0.05)
            with lock:
                running.remove(task)
            return task["name"], i

        done = list(run.schedule([(a, 1), (a, 2), (b, 1), (c, 1), (c, 2)], 4, trial_of))
        self.assertEqual(sorted(done), [("a", 1), ("a", 2), ("b", 1), ("c", 1), ("c", 2)])
        self.assertEqual(clashes, [])


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
