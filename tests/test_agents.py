"""Every agent file names itself, its model and its tools, so no role runs on a default by accident."""

import re
import unittest
from pathlib import Path

AGENTS = sorted((Path(__file__).resolve().parent.parent / "agents").glob("*.md"))
MODELS = {"opus", "sonnet", "haiku"}


def frontmatter(path):
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.S)
    return dict(line.split(": ", 1) for line in match.group(1).splitlines()) if match else {}


class AgentFileTest(unittest.TestCase):
    def test_each_agent_names_itself_after_its_file(self):
        for path in AGENTS:
            self.assertEqual(frontmatter(path).get("name"), path.stem, path.name)

    def test_each_agent_names_its_model_and_its_tools(self):
        for path in AGENTS:
            meta = frontmatter(path)
            self.assertIn(meta.get("model"), MODELS, path.name)
            self.assertTrue(meta.get("tools"), path.name)
            self.assertTrue(meta.get("description"), path.name)

    def test_only_the_builder_and_the_designer_can_write_files(self):
        writers = {path.stem for path in AGENTS if "Write" in frontmatter(path).get("tools", "")}
        self.assertEqual(writers, {"builder", "designer"})


if __name__ == "__main__":
    unittest.main()
