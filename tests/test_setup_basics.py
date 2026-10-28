"""Setup's basics give a product its CLAUDE.md map and a fixtures folder, and never replace its own."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

SETUP = Path(__file__).resolve().parent.parent / "skills" / "setup"
sys.path.insert(0, str(SETUP))
from holdouts import CLASSES  # noqa: E402
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

    def test_the_fixtures_and_the_holdouts_name_the_same_failure_classes(self):
        readme = (SETUP / "basics" / "fixtures" / "README.md").read_text()
        listed = dict(re.findall(r"^- `([a-z-]+)/`: (.+)$", readme, re.M))
        self.assertEqual(listed, CLASSES)


if __name__ == "__main__":
    unittest.main()
