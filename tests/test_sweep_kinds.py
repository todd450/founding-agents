"""Each sweep kind stands alone, runs on demand or on a schedule, and follows the rules every sweep shares."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SWEEP = ROOT / "skills" / "sweep"
KINDS = SWEEP / "kinds"
SETUP = ROOT / "skills" / "setup"
sys.path.insert(0, str(SETUP))
from install_kit import SWEEP_KINDS, install, plan  # noqa: E402

RULES = KINDS / "every-sweep.md"


def words(path):
    """The file's text with every run of whitespace as one space, so a wrapped line still matches."""
    return " ".join(path.read_text().split())


class KindTest(unittest.TestCase):
    def test_the_folder_holds_the_five_kinds_and_their_shared_rules(self):
        self.assertEqual(sorted(p.stem for p in KINDS.glob("*.md")), sorted(SWEEP_KINDS + ("every-sweep",)))

    def test_the_skill_names_each_kinds_model(self):
        skill = (SWEEP / "SKILL.md").read_text()
        for kind in SWEEP_KINDS:
            row = re.search(rf"^\| `{kind}` \|.*\| (Opus|Sonnet|Haiku) \|", skill, re.M)
            self.assertIsNotNone(row, kind)

    def test_each_kind_reads_the_shared_rules_and_files_only_its_own_issues(self):
        for kind in SWEEP_KINDS:
            text = words(KINDS / f"{kind}.md")
            self.assertIn("First read `every-sweep.md` in this file's folder", text, kind)
            self.assertIn(f"titled `Sweep ({kind}): …`", text, kind)
            self.assertIn("## Pass marks for this kind", text, kind)

    def test_every_sweep_proposes_at_most_three_findings_and_never_changes_the_product(self):
        rules = words(RULES)
        for rule in ("A red issue stops the run.", "Never commit, push", "At most three findings a run",
                     "never file a finding twice, and a closed one means the founder said no",
                     "A decision already made is never a finding.", "labels[]=needs-founder",
                     "leaves the other kinds' alone", "a quiet run files nothing"):
            self.assertIn(rule, rules)

    def test_every_issue_carries_the_sections_build_reads(self):
        rules = words(RULES)
        self.assertIn("`### Pass marks`", rules)
        self.assertIn("`### Technical decisions`", rules)

    def test_the_architecture_sweep_reads_the_recent_merges_first(self):
        text = (KINDS / "architecture.md").read_text()
        self.assertLess(text.index("**The recent merges.**"), text.index("**The product as it is now.**"))
        self.assertIn("merged_at", text)

    def test_a_public_repos_security_findings_stay_in_a_private_advisory(self):
        text = words(KINDS / "security.md")
        self.assertIn("repos/<owner>/<repo>/security-advisories", text)
        self.assertIn("If the advisory cannot be created, file nothing for that finding", text)
        self.assertIn("never the live product", text)

    def test_every_preview_binds_to_this_machine(self):
        for path in KINDS.glob("*.md"):
            for command in re.findall(r"`([^`]*http\.server[^`]*)`", path.read_text()):
                self.assertIn("--bind 127.0.0.1", command, path.name)


class GitHubTest(unittest.TestCase):
    def test_every_command_is_rest_inside_the_repo_since_a_routine_gets_nothing_else(self):
        # In a cloud routine `gh issue` and `gh pr` go through GraphQL and get a 403, and so does
        # any REST path outside the routine's own repo.
        commands = [c for path in KINDS.glob("*.md") for c in re.findall(r"`(gh [^`]+)`", path.read_text())
                    if c not in ("gh issue", "gh pr", "gh api")]
        self.assertTrue(commands)
        for command in commands:
            self.assertTrue(command.startswith("gh api"), command)
            self.assertIn("repos/<owner>/<repo>", command)


class ScheduleTest(unittest.TestCase):
    def test_setup_installs_each_kind_where_its_routines_prompt_points(self):
        self.assertIn("Follow .github/sweeps/<kind>.md in this repo.", words(SETUP / "SKILL.md"))
        for kind in SWEEP_KINDS:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                install(root, plan(root, f"sweep-{kind}"))
                self.assertEqual((root / ".github/sweeps" / f"{kind}.md").read_text(),
                                 (KINDS / f"{kind}.md").read_text(), kind)
                # The kind reads the shared rules from beside it.
                self.assertEqual((root / ".github/sweeps/every-sweep.md").read_text(), RULES.read_text(), kind)


if __name__ == "__main__":
    unittest.main()
