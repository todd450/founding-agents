"""Tidying removes an agent's worktree only when everything in it is on GitHub."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "tidy-worktrees"))
from tidy import plan, tidy  # noqa: E402


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                   capture_output=True)


class TidyTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        top = Path(self.folder.name).resolve()
        git("init", "--bare", "-b", "main", "origin.git", cwd=top)
        self.root = top / "product"
        git("clone", str(top / "origin.git"), "product", cwd=top)
        git("commit", "--allow-empty", "-m", "start", cwd=self.root)
        git("push", "origin", "main", cwd=self.root)

    def tearDown(self):
        self.folder.cleanup()

    def worktree(self, name, push=True):
        path = self.root / ".claude" / "worktrees" / name
        git("worktree", "add", "-b", name, str(path), cwd=self.root)
        git("commit", "--allow-empty", "-m", name, cwd=path)
        if push:
            git("push", "origin", name, cwd=path)
        return path

    def outcome(self):
        return {path.name: kept for path, _, kept in plan(self.root)}

    def test_a_clean_pushed_worktree_goes_and_its_branch_with_it(self):
        self.worktree("wf_pushed")
        tidy(self.root, plan(self.root))
        self.assertFalse((self.root / ".claude" / "worktrees" / "wf_pushed").exists())
        branches = subprocess.run(["git", "branch"], cwd=self.root, capture_output=True, text=True).stdout
        self.assertNotIn("wf_pushed", branches)

    def test_unpushed_commits_and_uncommitted_changes_are_kept(self):
        self.worktree("wf_unpushed", push=False)
        (self.worktree("wf_dirty") / "work.py").write_text("x = 1\n")
        tidy(self.root, plan(self.root))
        self.assertEqual(self.outcome(), {"wf_unpushed": "its commit is on no branch at origin",
                                          "wf_dirty": "1 uncommitted change(s)"})

    def test_caches_left_by_a_run_do_not_keep_a_worktree(self):
        cache = self.worktree("wf_cached") / "tests" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "test_x.pyc").write_bytes(b"")
        self.assertEqual(self.outcome(), {"wf_cached": ""})

    def test_a_sessions_own_worktree_and_any_outside_the_folder_are_never_touched(self):
        self.worktree("architect")
        other = Path(self.folder.name).resolve() / "elsewhere"
        git("worktree", "add", "-b", "elsewhere", str(other), cwd=self.root)
        self.assertEqual(self.outcome(), {})


if __name__ == "__main__":
    unittest.main()
