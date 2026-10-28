"""Every agent file names itself, its model and its tools, so no role runs on a default by accident."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = sorted((ROOT / "agents").glob("*.md"))
MODELS = {"opus", "sonnet", "haiku"}


def words(path):
    """The file's text with every run of whitespace as one space, so a wrapped line still matches."""
    return " ".join(path.read_text().split())


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

    def test_an_agent_told_to_use_a_skill_has_the_skill_tool(self):
        # The designer once had no Skill tool, could not find the screenshot script, and built its own.
        skills = [path.name for path in (AGENTS[0].parent.parent / "skills").iterdir() if path.is_dir()]
        for path in AGENTS:
            named = [skill for skill in skills if f"`{skill}` skill" in words(path)]
            if named:
                self.assertIn("Skill", frontmatter(path)["tools"], f"{path.name} names {named}")

    def test_the_builder_and_qa_look_for_screenshots_on_the_same_branch(self):
        for role in ("builder", "qa"):
            text = words(AGENTS[0].parent / f"{role}.md")
            self.assertIn("`mockup-screenshots` skill", text, role)
            self.assertIn("`screenshots/issue-<n>`", text, role)
            self.assertIn("No visible change.", text, role)

    def test_every_agent_a_workflow_runs_has_an_agent_file(self):
        names = {path.stem for path in AGENTS}
        for script in (ROOT / "workflows").glob("*.js"):
            for name in re.findall(r"agentType: 'founding-agents:([a-z-]+)'", script.read_text()):
                self.assertIn(name, names, f"{script.name} runs {name}, which has no agent file")



class ProportionTest(unittest.TestCase):
    """Reviews weigh who can reach a finding, and the integrator does not repeat checks CI ran."""

    def read(self, name):
        text = (Path(__file__).resolve().parent.parent / "agents" / f"{name}.md").read_text()
        return " ".join(text.split())

    def test_reviewers_rate_a_finding_by_who_can_reach_it(self):
        # On the website's #27, six rounds went on link tricks only the founder's own data could carry.
        self.assertIn("Rate severity by who can reach the input", self.read("security-reviewer"))
        self.assertIn("Rate a failure by who meets it", self.read("qa"))
        self.assertIn("by who can reach the input", self.read("code-reviewer"))

    def test_the_integrator_merges_on_green_checks_when_main_has_not_moved(self):
        integrator = self.read("integrator")
        self.assertIn("git merge-base --is-ancestor origin/main FETCH_HEAD", integrator)
        self.assertIn("gh pr update-branch", integrator)
        self.assertIn("Merge on that green result, without rerunning them", integrator)


if __name__ == "__main__":
    unittest.main()
