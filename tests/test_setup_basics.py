"""Setup's basics give a product its CLAUDE.md map and a fixtures folder, and never replace its own."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent.parent / "skills" / "setup"
sys.path.insert(0, str(SETUP))
from install_kit import install, plan  # noqa: E402


class BasicsTest(unittest.TestCase):
    def test_writes_the_map_and_the_fixtures_readme(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            install(root, plan(root, "basics"))
            self.assertIn("./check.sh", (root / "CLAUDE.md").read_text())
            self.assertTrue((root / "fixtures" / "README.md").exists())

    def test_pins_opus_to_opus_5_5_in_the_products_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            install(root, plan(root, "basics"))
            settings = json.loads((root / ".claude" / "settings.json").read_text())
            self.assertEqual(settings["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"], "claude-opus-5-5")

    def test_never_replaces_the_products_own_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.json").write_text("{}\n")
            install(root, plan(root, "basics"))
            self.assertEqual((root / ".claude" / "settings.json").read_text(), "{}\n")

    def test_never_replaces_the_products_own_claude_md(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "CLAUDE.md").write_text("# Site\n")
            install(root, plan(root, "basics"))
            self.assertEqual((root / "CLAUDE.md").read_text(), "# Site\n")

    def test_the_founder_hands_the_merge_over_in_the_words_the_integrator_reads(self):
        # The product's CLAUDE.md and the integrator agree on one phrase; auto mode's approval lives in
        # the founder's own settings, since Claude Code never reads `autoMode` from a repo or a plugin.
        words = "the integrator merges even though merging deploys"
        root = SETUP.parent.parent
        for path in [SETUP / "basics" / "CLAUDE.md", SETUP / "SKILL.md", root / "agents" / "integrator.md",
                     root / "workflows" / "build.js"]:
            self.assertIn(words, " ".join(path.read_text().split()).lower(), path.name)
        entry = json.loads(re.search(r"```json\n\s*(\{\"autoMode\".*?)\n\s*```", (SETUP / "SKILL.md").read_text(), re.S).group(1))
        allow = entry["autoMode"]["allow"]
        self.assertEqual(allow[0], "$defaults")
        self.assertIn(words, allow[1])


if __name__ == "__main__":
    unittest.main()
