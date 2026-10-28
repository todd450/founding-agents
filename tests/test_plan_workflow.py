"""The plan workflow checks the brief, and the architect either opens build issues or asks the founder."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_harness import HAVE_NODE, run_workflow  # noqa: E402

READY = {"ready": True, "reason": "", "repo": "o/site", "title": "Brief: a pricing page",
         "decision": "B, and D1: GitHub Pages"}
PLANNED = {"decisions": [], "plan_url": "https://github.com/o/site/issues/7#issuecomment-2", "stopped_because": "",
           "issues": [{"number": 8, "title": "Add the price table", "after": []},
                      {"number": 9, "title": "Link pricing from the home page", "after": [8]}]}
DOOR = {"decision": "Where prices are stored", "options": ["in the page", "a JSON file"], "recommend": "a JSON file",
        "why": "Both pages read the same prices.", "reverse": "an hour while two pages read them"}
POSTED = {"comment_url": "https://github.com/o/site/issues/7#issuecomment-3"}
TEAM = {"why": "Keep prices in one place.", "decisions": [
    {"id": "P1", "choice": "a JSON file", "why": "QA would keep it in the page, but two pages read it."}]}


@unittest.skipUnless(HAVE_NODE, "needs node")
class PlanWorkflowTest(unittest.TestCase):
    def labels(self, run):
        return [call["label"] for call in run["calls"]]

    def test_a_brief_that_is_not_ready_starts_nothing(self):
        run = run_workflow("plan", {"check": [{**READY, "ready": False, "reason": "already planned as #8"}]}, 7)
        self.assertEqual(run["result"], {"issue": 7, "status": "not started", "reason": "already planned as #8"})
        self.assertEqual(self.labels(run), ["check #7"])

    def test_the_check_wants_the_decided_label_and_no_issues_cut_from_it_yet(self):
        prompt = run_workflow("plan", {"check": [{**READY, "ready": False, "reason": "x"}]}, 7)["calls"][0]["prompt"]
        self.assertIn("labelled `decided`", prompt)
        self.assertIn('Part of #7', prompt)

    def test_a_planned_brief_names_its_issues_in_order_and_how_to_build_them(self):
        run = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)
        self.assertEqual(run["result"]["status"], "planned")
        self.assertEqual(run["result"]["issues"], ["#8 Add the price table", "#9 Link pricing from the home page (after #8)"])
        self.assertEqual(run["result"]["next"], "/founding-agents:build 7")
        self.assertEqual(self.labels(run), ["check #7", "architect", "run report"])

    def test_the_architect_runs_as_its_plugin_agent_on_opus_with_the_founders_answers(self):
        architect = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)["calls"][1]
        self.assertEqual((architect["agentType"], architect["model"]), ("founding-agents:architect", "opus"))
        self.assertIn("The founder decided: B, and D1: GitHub Pages", architect["prompt"])

    def test_each_issue_says_what_brief_it_is_part_of_its_files_and_its_decisions(self):
        prompt = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)["calls"][1]["prompt"]
        for part in ("Part of #7.", "Build after #<n>: <what of #<n>", "## Files", "no two issues own the same file",
                     "## Technical decisions", "technical one-way door"):
            self.assertIn(part, prompt)

    def test_the_architect_links_consistency_apart_from_dependency(self):
        # Half Badger's #6 to #9 were chained partly to stay consistent, so parallel builders idled.
        prompt = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)["calls"][1]["prompt"]
        self.assertIn("Matches #<n>: <what stays the same in both>", prompt)
        self.assertIn('Write "Build after" only for a real dependency', prompt)

    def test_pass_marks_the_reviewers_cannot_check_go_to_the_founder(self):
        # Half Badger's #2 needed a dashboard click and a preview behind Vercel's login.
        prompt = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)["calls"][1]["prompt"]
        self.assertIn("## The founder checks", prompt)
        self.assertIn("with no dashboard, login or account", prompt)

    def test_a_preview_command_binds_to_this_machine_and_serves_no_secret(self):
        prompt = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)["calls"][1]["prompt"]
        self.assertIn("binds to 127.0.0.1, and serves a folder that holds no secret", prompt)

    def open_decision(self, **replies):
        return run_workflow("plan", {"check": [READY], "architect": [{**PLANNED, "issues": [], "plan_url": "",
                                                                     "decisions": [DOOR]}],
                                     "queue": [POSTED], **replies}, 7)

    def test_an_open_decision_goes_to_the_founder_and_no_issues_are_opened(self):
        run = self.open_decision(team=[TEAM])
        self.assertEqual(run["result"]["status"], "needs the founder")
        labels = self.labels(run)
        self.assertEqual(labels[:2], ["check #7", "architect"])
        self.assertEqual(labels[-3:], ["team", "queue item", "run report"])
        item = run["calls"][-2]["prompt"]
        self.assertIn("**P1. Where prices are stored:** in the page / a JSON file. Reversing it later: an hour", item)
        self.assertIn("--remove-label decided --add-label needs-founder", item)
        self.assertIn("`/founding-agents:plan 7` plans it with your answers", item)

    def test_every_other_role_recommends_and_the_team_weighs_them(self):
        run = self.open_decision(team=[TEAM], qa=[{"why": "", "decisions": [
            {"id": "P1", "choice": "in the page", "why": "One file is one thing to check."}]}])
        voices = [c for c in run["calls"] if c["agentType"] not in (None, "founding-agents:architect")]
        self.assertEqual({c["agentType"] for c in voices},
                         {f"founding-agents:{n}" for n in ("product-lead", "researcher", "designer", "builder", "qa",
                                                           "code-reviewer", "security-reviewer", "integrator")})
        for voice in voices:
            self.assertEqual(voice["model"], "sonnet")
            self.assertNotIn("Each role's choices", voice["prompt"])
        team = next(c for c in run["calls"] if c["label"] == "team")
        self.assertEqual(team["model"], "opus")
        self.assertIn("- Architect: P1: a JSON file. Both pages read the same prices.", team["prompt"])
        self.assertIn("- QA: P1: in the page. One file is one thing to check.", team["prompt"])

    def test_the_queue_item_leads_with_the_team_then_each_role(self):
        item = self.open_decision(team=[TEAM], qa=[{"why": "", "decisions": [
            {"id": "P1", "choice": "in the page", "why": "One file is one thing to check."}]}])["calls"][-2]["prompt"]
        self.assertIn("**The team:** Keep prices in one place.", item)
        self.assertIn("  - **The team: a JSON file.** QA would keep it in the page, but two pages read it.", item)
        self.assertIn("  - Architect: a JSON file. Both pages read the same prices.", item)
        self.assertIn("  - QA: in the page. One file is one thing to check.", item)
        self.assertNotIn("because", item)

    def test_without_a_team_view_each_role_still_reaches_the_founder(self):
        item = self.open_decision()["calls"][-2]["prompt"]
        self.assertIn("**The team** gave no overall recommendation", item)
        self.assertIn("  - Architect: a JSON file.", item)

    def test_every_voice_is_an_agent_file(self):
        agents = Path(__file__).resolve().parent.parent / "agents"
        source = (Path(__file__).resolve().parent.parent / "workflows" / "plan.js").read_text()
        for name in re.findall(r"agentType: 'founding-agents:([a-z-]+)'", source):
            self.assertTrue((agents / f"{name}.md").exists(), name)

    def test_an_architect_that_opens_nothing_stops_the_run(self):
        run = run_workflow("plan", {"check": [READY], "architect": [{**PLANNED, "issues": [], "plan_url": "",
                                                                     "stopped_because": "the brief is one line of copy"}]}, 7)
        self.assertEqual(run["result"]["status"], "stopped in plan")
        self.assertEqual(run["result"]["reason"], "the brief is one line of copy")

    def test_a_run_past_its_check_posts_its_report_on_the_brief(self):
        report = run_workflow("plan", {"check": [READY], "architect": [PLANNED]}, 7)["calls"][-1]
        self.assertEqual((report["label"], report["model"]), ("run report", "haiku"))
        self.assertIn("--workflow plan --issue 7 --budget 5 --post", report["prompt"])

    def test_takes_the_brief_as_a_number_a_string_or_an_object(self):
        for args in (7, "#7", {"issue": 7}):
            run = run_workflow("plan", {"check": [{**READY, "ready": False, "reason": "x"}]}, args)
            self.assertEqual(run["result"]["issue"], 7)

    def test_no_brief_is_an_error(self):
        self.assertIn("Name the decided brief", run_workflow("plan", {}, None)["error"])


if __name__ == "__main__":
    unittest.main()
