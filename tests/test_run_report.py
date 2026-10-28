"""The run report prices each model call once, by role, and finds the run by workflow and issue."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "run-report"))
from report import build_runs, cost, find_session, project_logs, runs_table, summarise, table  # noqa: E402


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

    def test_each_call_is_priced_by_the_model_it_ran_not_its_family(self):
        # Half Badger's build #1 asked for `opus` and ran Opus 5: priced as Opus 5.5 it read $7.08,
        # where Claude Code counted $11.10. These are that run's Opus, Sonnet and Haiku calls, and
        # Claude Code's own cost for each.
        opus = {"input_tokens": 406, "output_tokens": 182203, "cache_read_input_tokens": 6083537,
                "cache_creation_input_tokens": 435287, "cache_creation": {"ephemeral_1h_input_tokens": 73186}}
        sonnet = {"input_tokens": 14, "output_tokens": 5598, "cache_read_input_tokens": 205282,
                  "cache_creation_input_tokens": 84282}
        haiku = {"input_tokens": 28, "output_tokens": 1051, "cache_read_input_tokens": 46138,
                 "cache_creation_input_tokens": 26095}
        self.assertAlmostEqual(cost("claude-opus-5", opus), 10.593864750000002, places=6)
        self.assertAlmostEqual(cost("claude-sonnet-5", sonnet), 0.4616541, places=6)
        self.assertAlmostEqual(cost("claude-haiku-4-5-20251001", haiku), 0.04251555, places=6)
        self.assertLess(cost("claude-opus-5-5", opus), cost("claude-opus-5", opus))


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
        self.assertEqual(summarise(self.session)[("main session", "sonnet-5-5")]["calls"], 2)

    def test_each_subagent_is_reported_under_its_role_and_model(self):
        builder = summarise(self.session)[("builder", "opus-5-5")]
        self.assertEqual((builder["calls"], builder["cached"], builder["out"]), (2, 5000, 2000))

    def test_the_table_gives_the_run_time_and_the_total(self):
        report = table(summarise(self.session), "`build` #10")
        self.assertIn("`build` #10 · 20 min", report)
        self.assertIn("| builder | opus-5-5 | 10 min | 2 |", report)
        self.assertIn("API-equivalent", report)
        self.assertNotIn("Over budget", report)

    def test_a_run_over_its_budget_is_flagged_above_the_table(self):
        report = table(summarise(self.session), "`build` #10", budget=0.01)
        self.assertIn("**Over budget:**", report)
        self.assertLess(report.index("Over budget"), report.index("| Role |"))


    def test_the_outcome_is_recorded_above_the_table(self):
        report = table(summarise(self.session), "`build` #10", budget=0.01, outcome="stopped")
        self.assertIn("**Outcome:** stopped for the founder", report)
        self.assertLess(report.index("Outcome"), report.index("Over budget"))
        self.assertNotIn("Outcome", table(summarise(self.session), "`build` #10"))

    def test_a_run_left_for_the_founders_merge_says_so(self):
        report = table(summarise(self.session), "`build` #10", outcome="ready")
        self.assertIn("**Outcome:** ready for the founder's merge", report)

    def test_a_model_with_no_price_is_named_rather_than_left_out_quietly(self):
        write(self.session.with_suffix("") / "subagents" / "agent-a2.jsonl",
              call("x1", "claude-new-model-9", "2026-10-26T10:05:00Z", output_tokens=1_000_000))
        (self.session.with_suffix("") / "subagents" / "agent-a2.meta.json").write_text(json.dumps({"agentType": "founding-agents:qa"}))
        report = table(summarise(self.session), "`build` #10")
        self.assertIn("**Not priced:** claude-new-model-9.", report)
        self.assertNotIn("Not priced", table(summarise(self.session.with_name("none.jsonl")), "`build` #10"))


def report_on(issue, stamp, outcome=None):
    body = f"**Run report** · `build` #{issue} · 20 min · $3.00 at API prices\n\n"
    if outcome:
        body += f"**Outcome:** {outcome}\n\n"
    return {"created_at": stamp, "body": body + "| Role | Model |"}


class BuildRunsTest(unittest.TestCase):
    """Ramp's measure: the share of runs that end in a merge without a person stepping in."""

    def test_a_merge_counts_as_without_the_founder_only_on_the_first_run_on_its_issue(self):
        counts = build_runs([
            report_on(4, "2026-10-26T12:00:00Z", "merged"),
            report_on(4, "2026-10-26T10:00:00Z", "stopped for the founder"),
            report_on(5, "2026-10-26T11:00:00Z", "merged"),
            report_on(6, "2026-10-26T13:00:00Z", "merged"),
        ])
        self.assertEqual(counts, {"merged alone": 2, "merged after a stop": 1, "ready": 0, "stopped": 1, "unrecorded": 0})

    def test_a_run_left_for_the_founders_merge_is_counted_apart(self):
        counts = build_runs([report_on(4, "2026-10-26T10:00:00Z", "ready for the founder's merge")])
        self.assertEqual(counts["ready"], 1)
        self.assertIn("| Ready, left for the founder's merge | 1 | 100% |", runs_table(counts))

    def test_reports_from_before_outcomes_are_left_out_but_still_mark_their_issue(self):
        counts = build_runs([report_on(4, "2026-10-25T10:00:00Z"), report_on(4, "2026-10-26T10:00:00Z", "merged"),
                             {"created_at": "2026-10-26T11:00:00Z", "body": "**Run report** · `propose` #8 · 5 min"}])
        self.assertEqual(counts, {"merged alone": 0, "merged after a stop": 1, "ready": 0, "stopped": 0, "unrecorded": 1})

    def test_the_table_gives_each_share(self):
        text = runs_table({"merged alone": 2, "merged after a stop": 1, "ready": 0, "stopped": 1, "unrecorded": 3}, "2026-10-20")
        self.assertIn("**Build runs** since 2026-10-20 · 4 with a recorded outcome", text)
        self.assertIn("| Merged without the founder | 2 | 50% |", text)
        self.assertIn("| Stopped for the founder | 1 | 25% |", text)
        self.assertIn("3 report(s) from before outcomes were recorded are left out", text)

    def test_no_runs_says_so_rather_than_dividing_by_zero(self):
        self.assertIn("none with a recorded outcome yet",
                      runs_table({"merged alone": 0, "merged after a stop": 0, "ready": 0, "stopped": 0, "unrecorded": 0}))


class FindSessionTest(unittest.TestCase):
    def test_finds_the_newest_run_of_that_workflow_on_that_issue(self):
        with tempfile.TemporaryDirectory() as folder:
            logs = Path(folder)
            prompt = lambda text: {"type": "user", "message": {"content": text}}
            write(logs / "a.jsonl", prompt("<command-name>/founding-agents:build</command-name><command-args>4</command-args>"))
            write(logs / "b.jsonl", prompt("<command-name>/founding-agents:build</command-name><command-args>40</command-args>"))
            write(logs / "c.jsonl", prompt("<command-name>/founding-agents:propose</command-name><command-args>4</command-args>"))
            self.assertEqual(find_session(logs, "build", 4).name, "a.jsonl")
            write(logs / "d.jsonl", prompt("<command-name>/founding-agents:plan</command-name><command-args>4</command-args>"))
            self.assertEqual(find_session(logs, "propose", 4).name, "c.jsonl")
            self.assertEqual(find_session(logs, "plan", 4).name, "d.jsonl")
            self.assertIsNone(find_session(logs, "build", 5))

    def test_a_run_started_on_an_idea_in_words_is_found_by_its_report_step(self):
        # Half Badger's first `propose` named no issue in its first prompt, since the product lead
        # opened #1 partway through, and the report step found no session and posted nothing.
        with tempfile.TemporaryDirectory() as folder:
            logs = Path(folder)
            prompt = lambda text: {"type": "user", "message": {"content": text}}
            write(logs / "a.jsonl", prompt('<command-name>/founding-agents:propose</command-name><command-args>"Rebuild the site"</command-args>'))
            write(logs / "a" / "subagents" / "workflows" / "wf_1" / "agent-r.jsonl",
                  prompt("Use the run-report skill: run its script with `--workflow propose --issue 1 --budget 5 --post`."))
            write(logs / "b.jsonl", prompt('<command-name>/founding-agents:propose</command-name><command-args>"Another idea"</command-args>'))
            self.assertEqual(find_session(logs, "propose", 1).name, "a.jsonl")
            self.assertIsNone(find_session(logs, "propose", 11))
            self.assertIsNone(find_session(logs, "build", 1))

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
