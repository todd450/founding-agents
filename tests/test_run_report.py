"""The run report prices each model call once, by role, and finds the run by workflow and issue."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "run-report"))
from report import cost, find_session, project_logs, summarise, table  # noqa: E402


def call(message_id, model, stamp, **usage):
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": message_id, "model": model, "usage": usage}}


def write(path, *lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))


class CostTest(unittest.TestCase):
    def test_prices_each_kind_of_token(self):
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000,
                 "cache_creation_input_tokens": 2_000_000, "cache_creation": {"ephemeral_1h_input_tokens": 1_000_000}}
        # Opus 5.5: $4 in, $20 out, $0.20 cache read, $5 a 5-minute write, $8 a 1-hour write.
        self.assertAlmostEqual(cost("claude-opus-5-5", usage), 4 + 20 + 0.20 + 5 + 8)

    def test_cache_writes_without_a_split_count_as_five_minute_writes(self):
        self.assertAlmostEqual(cost("claude-sonnet-5-5", {"cache_creation_input_tokens": 1_000_000}), 2.50)

    def test_an_unknown_model_costs_nothing_rather_than_a_guess(self):
        self.assertEqual(cost("some-other-model", {"output_tokens": 1_000_000}), 0.0)


class SummariseTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.session = Path(self.folder.name) / "s1.jsonl"
        write(self.session,
              {"type": "user", "message": {"content": "/founding-agents:build 10"}},
              call("m1", "claude-sonnet-5-5", "2026-10-26T10:00:00Z", output_tokens=100),
              call("m1", "claude-sonnet-5-5", "2026-10-26T10:00:01Z", output_tokens=100),
              call("m2", "claude-sonnet-5-5", "2026-10-26T10:20:00Z", output_tokens=100))
        agent = Path(self.folder.name) / "s1" / "subagents" / "workflows" / "wf_1" / "agent-a1"
        write(agent.with_suffix(".jsonl"),
              call("b1", "claude-opus-5-5", "2026-10-26T10:01:00Z", input_tokens=10, cache_read_input_tokens=5000),
              call("b2", "claude-opus-5-5", "2026-10-26T10:11:00Z", output_tokens=2000))
        agent.with_suffix(".meta.json").write_text(json.dumps({"agentType": "founding-agents:builder"}))

    def tearDown(self):
        self.folder.cleanup()

    def test_a_call_logged_on_several_lines_counts_once(self):
        self.assertEqual(summarise(self.session)[("main session", "sonnet")]["calls"], 2)

    def test_each_subagent_is_reported_under_its_role_and_model(self):
        builder = summarise(self.session)[("builder", "opus")]
        self.assertEqual((builder["calls"], builder["cached"], builder["out"]), (2, 5000, 2000))

    def test_the_table_gives_the_run_time_and_the_total(self):
        report = table(summarise(self.session), "`build` #10")
        self.assertIn("`build` #10 · 20 min", report)
        self.assertIn("| builder | opus | 10 min | 2 |", report)
        self.assertIn("API-equivalent", report)
        self.assertNotIn("Over budget", report)

    def test_a_run_over_its_budget_is_flagged_above_the_table(self):
        report = table(summarise(self.session), "`build` #10", budget=0.01)
        self.assertIn("**Over budget:**", report)
        self.assertLess(report.index("Over budget"), report.index("| Role |"))


class FindSessionTest(unittest.TestCase):
    def test_finds_the_newest_run_of_that_workflow_on_that_issue(self):
        with tempfile.TemporaryDirectory() as folder:
            logs = Path(folder)
            prompt = lambda text: {"type": "user", "message": {"content": text}}
            write(logs / "a.jsonl", prompt("<command-name>/founding-agents:build</command-name><command-args>4</command-args>"))
            write(logs / "b.jsonl", prompt("<command-name>/founding-agents:build</command-name><command-args>40</command-args>"))
            write(logs / "c.jsonl", prompt("<command-name>/founding-agents:propose</command-name><command-args>4</command-args>"))
            self.assertEqual(find_session(logs, "build", 4).name, "a.jsonl")
            self.assertEqual(find_session(logs, "propose", 4).name, "c.jsonl")
            self.assertIsNone(find_session(logs, "build", 5))

    def test_a_sweep_is_found_by_its_workflow_alone(self):
        with tempfile.TemporaryDirectory() as folder:
            logs = Path(folder)
            write(logs / "a.jsonl", {"type": "user", "message": {"content":
                  "<command-name>/founding-agents:sweep</command-name><command-args>security</command-args>"}})
            self.assertEqual(find_session(logs, "sweep", 31).name, "a.jsonl")

    def test_project_logs_are_named_from_the_folder_path(self):
        self.assertEqual(project_logs(Path("/Users/t/code/my.site")).name, "-Users-t-code-my-site")


if __name__ == "__main__":
    unittest.main()
