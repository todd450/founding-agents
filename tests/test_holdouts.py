"""Only edge-case QA reads the holdout scenarios, and setup gives them a home outside the product."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "hooks" / "guard_holdouts.py"
sys.path.insert(0, str(ROOT / "skills" / "setup"))
from holdouts import CLASSES, holdout_path, holdout_repo, seed  # noqa: E402


def guard(tool, tool_input, agent="founding-agents:builder"):
    event = {"tool_name": tool, "tool_input": tool_input}
    if agent:
        event["agent_type"] = agent
    return subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event), capture_output=True,
                          text=True).returncode


class GuardTest(unittest.TestCase):
    def test_blocks_a_builder_from_the_holdouts_however_it_asks(self):
        for tool, tool_input in (
            ("Read", {"file_path": "/Users/f/.founding-agents/holdouts/o/site/second-user/draft.md"}),
            ("Grep", {"pattern": "Expected", "path": "/Users/f/.founding-agents"}),
            ("Glob", {"pattern": "**/*.md", "path": "~/.founding-agents/holdouts"}),
            ("Bash", {"command": "cat ~/.founding-agents/holdouts/o/site/*/*.md"}),
            ("Bash", {"command": "gh repo clone o/site-holdouts /tmp/h"}),
            ("Bash", {"command": "gh api repos/o/site-holdouts/contents/time-zones"}),
        ):
            self.assertEqual(guard(tool, tool_input), 2, tool_input)

    def test_blocks_every_agent_but_qa(self):
        read = {"file_path": "/Users/f/.founding-agents/holdouts/o/site/README.md"}
        for agent in ("founding-agents:architect", "founding-agents:code-reviewer", "founding-agents:security-reviewer", "qa"):
            self.assertEqual(guard("Read", read, agent=agent), 2, agent)
        self.assertEqual(guard("Read", read, agent="founding-agents:qa"), 0)

    def test_the_founders_own_session_sets_them_up_and_writes_them(self):
        self.assertEqual(guard("Bash", {"command": "gh repo create o/site-holdouts --private"}, agent=None), 0)

    def test_lets_a_builder_work_on_the_product(self):
        for tool, tool_input in (
            ("Read", {"file_path": "/Users/f/code/site/fixtures/second-user.json"}),
            ("Bash", {"command": "./check.sh && gh pr create --fill"}),
        ):
            self.assertEqual(guard(tool, tool_input), 0, tool_input)


class SetupTest(unittest.TestCase):
    def test_the_repo_and_its_clone_sit_outside_the_product(self):
        self.assertEqual(holdout_repo("o/site"), "o/site-holdouts")
        self.assertEqual(holdout_path("o/site", home="/Users/f"), Path("/Users/f/.founding-agents/holdouts/o/site"))

    def test_seeds_a_readme_and_a_folder_per_failure_class_once(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            self.assertTrue(seed(folder, "o/site"))
            readme = (folder / "README.md").read_text()
            self.assertIn("## Expected", readme)
            for slug in CLASSES:
                self.assertTrue((folder / slug).is_dir(), slug)
                self.assertIn(f"`{slug}/`", readme)
            self.assertEqual(seed(folder, "o/site"), [])


if __name__ == "__main__":
    unittest.main()
