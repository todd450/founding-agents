"""The routines reach GitHub only through REST, and the product keeps its own checks."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent.parent / "skills" / "setup"
sys.path.insert(0, str(SETUP))
from install_kit import install, plan  # noqa: E402

ROUTINE = (SETUP / "ops_watch" / "routine.md").read_text()
ROUTINES = sorted(SETUP.glob("*/routine.md"))


class RoutineTest(unittest.TestCase):
    def test_every_routine_uses_no_graphql_command_since_the_cloud_proxy_blocks_them(self):
        # In a routine, `gh issue`, `gh pr` and `gh repo view` go through GraphQL and get a 403.
        # A routine names those three to warn against them; every command it runs is `gh api`.
        self.assertEqual([p.parent.name for p in ROUTINES], ["librarian", "ops_watch", "optimiser"])
        for routine in ROUTINES:
            text = routine.read_text()
            commands = [c for c in re.findall(r"`(gh [^`]+)`", text) if c not in ("gh issue", "gh pr", "gh repo view")]
            self.assertTrue(commands, routine)
            for command in commands:
                self.assertTrue(command.startswith("gh api"), f"{routine.parent.name}: {command}")

    def test_every_routine_stays_inside_its_own_repo(self):
        # The cloud's GitHub proxy serves only the routine's own repo: on 27 Oct 2026 the first runs
        # got a 403 for `search/issues`, and for fetching the live site.
        for routine in ROUTINES:
            for command in re.findall(r"`(gh api [^`]+)`", routine.read_text()):
                self.assertIn("repos/<owner>/<repo>", command, f"{routine.parent.name}: {command}")

    def test_ops_watch_reads_what_pages_serves_instead_of_fetching_the_site(self):
        self.assertIn("pages/builds/latest", ROUTINE)
        self.assertNotIn("curl", ROUTINE)

    def test_the_weekly_routines_only_propose_and_leave_deciding_to_the_founder(self):
        for name in ("optimiser", "librarian"):
            text = (SETUP / name / "routine.md").read_text()
            self.assertIn("labels[]=needs-founder", text)
            self.assertIn("At most three", text)
            self.assertIn("Never push", text)

    def test_the_librarian_reads_the_findings_build_saw_come_back_first(self):
        text = (SETUP / "librarian" / "routine.md").read_text()
        self.assertIn("labels=librarian&state=open", text)
        self.assertLess(text.index("## Repeated findings, first"), text.index("## Incidents"))
        self.assertIn("Repeated finding on PR #<n>", text)

    def test_the_librarian_asks_for_failure_messages_that_say_how_to_fix(self):
        self.assertIn("failure message says how to fix the problem",
                      (SETUP / "librarian" / "routine.md").read_text())

    def test_runs_its_checks_then_the_products_own(self):
        for check in ("Scheduled checks ran", "`main` passes", "Merged changes are live", "Spend",
                      ".github/ops-watch/watch.md", "disabled_inactivity"):
            self.assertIn(check, ROUTINE)

    def test_a_check_that_could_not_run_is_not_red(self):
        self.assertIn("A check you could not run is not red", ROUTINE)


class KitTest(unittest.TestCase):
    def test_installs_the_weekly_routines_where_their_prompts_point(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for kit in ("optimiser", "librarian"):
                install(root, plan(root, kit))
                self.assertTrue((root / ".github" / kit / "routine.md").exists(), kit)

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
