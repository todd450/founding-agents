"""The merge guard blocks pushes to main and merges by every session and agent. One merge passes:
asking GitHub to merge once the required checks pass, and never from one of the team's roles."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "hooks" / "guard_main.py"


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class GuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.remote = root / "remote.git"
        cls.repo = root / "repo"
        run("git", "init", "--bare", "-b", "main", str(cls.remote), cwd=root)
        run("git", "clone", str(cls.remote), str(cls.repo), cwd=root)
        for args in (
            ("git", "config", "user.email", "test@example.com"),
            ("git", "config", "user.name", "Test"),
            ("git", "commit", "--allow-empty", "-m", "start"),
            ("git", "push", "-u", "origin", "main"),
            ("git", "remote", "set-head", "origin", "main"),
            ("git", "switch", "-c", "feat/x"),
            ("git", "push", "-u", "origin", "feat/x"),
        ):
            run(*args, cwd=cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, command, agent="founding-agents:builder", branch="feat/x", tool="Bash"):
        run("git", "switch", "-q", branch, cwd=self.repo)
        event = {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(self.repo)}
        if agent:
            event["agent_type"] = agent
        result = subprocess.run(
            [sys.executable, str(GUARD)], input=json.dumps(event), capture_output=True, text=True
        )
        return result.returncode

    def assertBlocked(self, command, **kwargs):
        self.assertEqual(self.check(command, **kwargs), 2, command)

    def assertAllowed(self, command, **kwargs):
        self.assertEqual(self.check(command, **kwargs), 0, command)

    def test_blocks_pushes_to_main(self):
        for command in (
            "git push origin main",
            "git push origin HEAD:main",
            "git push origin feat/x:refs/heads/main",
            "git push --force origin +main",
            "git push origin :main",
            "git push --all origin",
            "git -C . push origin main",
            "cd . && git push origin main",
            "GIT_TRACE=1 git push origin main",
            "git push origin master",
        ):
            self.assertBlocked(command)

    def test_blocks_bare_push_from_main(self):
        self.assertBlocked("git push", branch="main")
        self.assertBlocked("git push -u origin HEAD", branch="main")

    def test_allows_pushes_to_other_branches(self):
        for command in (
            "git push",
            "git push -u origin HEAD",
            "git push origin feat/x",
            "git push --force-with-lease origin feat/x",
            "git push origin main-docs",
        ):
            self.assertAllowed(command)

    def test_blocks_merges(self):
        for command in (
            "gh pr merge 12 --squash",
            "gh pr merge 12 --merge --delete-branch",
            "gh api -X PUT repos/o/r/pulls/3/merge",
        ):
            self.assertBlocked(command)
            self.assertBlocked(command, agent=None)

    def test_a_session_or_a_workflow_step_may_ask_github_to_merge_once_checks_pass(self):
        # Decided 11 Nov 2026: a click per PR was the founder's hassle, and GitHub's own auto-merge
        # needs no agent trusted to merge.
        for command in ("gh pr merge 12 --auto --squash", "gh pr merge --auto --squash 12 --repo o/r",
                        "cd . && gh pr merge 12 --auto --squash"):
            self.assertAllowed(command, agent=None)
            self.assertAllowed(command, agent="workflow-subagent")

    def test_no_merge_goes_around_the_checks(self):
        for command in ("gh pr merge 12 --auto --squash --admin", "gh pr merge 12 --admin"):
            self.assertBlocked(command, agent=None)

    def test_the_roles_that_build_and_review_a_change_never_ship_it(self):
        for agent in ("founding-agents:builder", "founding-agents:code-reviewer", "founding-agents:qa",
                      "founding-agents:security-reviewer", "other-plugin:builder", "designer"):
            self.assertBlocked("gh pr merge 12 --auto --squash", agent=agent)

    def test_blocks_a_session_that_is_not_an_agent(self):
        self.assertBlocked("gh pr merge 1", agent=None)

    def test_blocks_other_agents(self):
        self.assertBlocked("gh pr merge 1", agent="founding-agents:code-reviewer")
        self.assertBlocked("gh pr merge 1", agent="other-plugin:builder")

    def test_no_agent_name_is_exempt(self):
        # The integrator was exempt until 9 Nov 2026; no name has passed a plain merge since.
        for agent in ("founding-agents:integrator", "integrator", "other-plugin:integrator"):
            self.assertBlocked("gh pr merge 1 --merge", agent=agent)
            self.assertBlocked("git push origin main", agent=agent)

    def test_ignores_commands_that_only_mention_push_or_merge(self):
        for command in (
            "echo git push origin main",
            'git commit -m "push to main"',
            "gh pr view 12",
            "git merge-base main HEAD",
            "git log --merges",
        ):
            self.assertAllowed(command)

    def test_ignores_other_tools(self):
        self.assertAllowed("git push origin main", tool="Read")


if __name__ == "__main__":
    unittest.main()
