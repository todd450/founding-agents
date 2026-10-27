"""Ops watch's routine reaches GitHub only through REST, and the product keeps its own checks."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent.parent / "skills" / "setup"
sys.path.insert(0, str(SETUP))
from install_kit import install, plan  # noqa: E402

ROUTINE = (SETUP / "ops_watch" / "routine.md").read_text()


class RoutineTest(unittest.TestCase):
    def test_uses_no_graphql_command_since_the_cloud_proxy_blocks_them(self):
        # In a routine, `gh issue`, `gh pr` and `gh repo view` go through GraphQL and get a 403.
        # The routine names those three to warn against them; every command it runs is `gh api`.
        commands = [c for c in re.findall(r"`(gh [^`]+)`", ROUTINE) if c not in ("gh issue", "gh pr", "gh repo view")]
        self.assertTrue(commands)
        for command in commands:
            self.assertTrue(command.startswith("gh api"), command)

    def test_runs_its_checks_then_the_products_own(self):
        for check in ("Scheduled checks ran", "`main` passes", "Merged changes are live", "Spend",
                      ".github/ops-watch/watch.md", "disabled_inactivity"):
            self.assertIn(check, ROUTINE)

    def test_a_check_that_could_not_run_is_not_red(self):
        self.assertIn("A check you could not run is not red", ROUTINE)


class KitTest(unittest.TestCase):
    def test_keeps_the_routine_current_and_the_products_checks_its_own(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".github/ops-watch").mkdir(parents=True)
            (root / ".github/ops-watch/routine.md").write_text("old\n")
            (root / ".github/ops-watch/watch.md").write_text("- **Address:** https://o.github.io/site/\n")
            install(root, plan(root, "ops-routine"))
            self.assertEqual((root / ".github/ops-watch/routine.md").read_text(), ROUTINE)
            self.assertIn("o.github.io", (root / ".github/ops-watch/watch.md").read_text())


if __name__ == "__main__":
    unittest.main()
