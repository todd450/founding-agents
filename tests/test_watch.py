"""Watching a run reads Claude Code's own record of it, shows no command or output, and serves the
live board to this machine only."""

import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "watch"))
from watch import page, read_run, records, runs, server  # noqa: E402

START = 1_800_000_000


def at(seconds):
    return datetime.fromtimestamp(START + seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def told(seconds, text):
    return {"type": "user", "timestamp": at(seconds), "message": {"content": text}}


def step(seconds, tool, given, call):
    return {"type": "assistant", "timestamp": at(seconds),
            "message": {"content": [{"type": "tool_use", "id": call, "name": tool, "input": given}]}}


def result(seconds, call, failed=False):
    return {"type": "user", "timestamp": at(seconds),
            "message": {"content": [{"type": "tool_result", "tool_use_id": call, "is_error": failed}]}}


class WatchTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        top = Path(self.folder.name).resolve()
        self.home, self.product = top / "claude", top / "my product"
        self.product.mkdir()
        self.run = records(self.product, self.home) / "session-1" / "subagents" / "workflows" / "wf_one"
        self.run.mkdir(parents=True)

    def tearDown(self):
        self.folder.cleanup()

    def agent(self, name, lines, meta, run=None):
        run = run or self.run
        run.mkdir(parents=True, exist_ok=True)
        (run / f"agent-{name}.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))
        (run / f"agent-{name}.meta.json").write_text(json.dumps(meta))

    def a_build(self):
        self.agent("b1", [
            told(0, "Build issue #12 in acme/shop: a quieter footer"),
            step(10, "Bash", {"command": "curl -H 'Authorization: Bearer sk-secret' x", "description": "Fetch the issue"}, "c1"),
            result(12, "c1"),
            step(40, "Edit", {"file_path": "/work/site/index.html"}, "c2"),
            result(41, "c2", failed=True),
            step(200, "StructuredOutput", {"pr_number": 3}, "c3"),
        ], {"agentType": "founding-agents:builder", "model": "opus"})
        self.agent("r1", [
            told(205, "Review PR #3 in acme/shop, which builds issue #12: a quieter footer"),
            step(230, "Bash", {"command": "gh pr diff 3", "description": "Read the diff"}, "c4"),
        ], {"agentType": "founding-agents:reviewer", "model": "opus"})
        (self.run / "journal.jsonl").write_text(
            json.dumps({"type": "started", "agentId": "b1"}) + "\n"
            + json.dumps({"type": "result", "agentId": "b1", "result": {}}) + "\n"
            + json.dumps({"type": "started", "agentId": "r1"}) + "\n")

    def test_a_run_reads_as_agents_in_order_with_times_from_its_start(self):
        self.a_build()
        run = read_run(self.run, now=START + 400)
        builder, reviewer = run["agents"]
        self.assertEqual((builder["role"], builder["s"], builder["e"]), ("builder", 0, 200))
        self.assertEqual((reviewer["role"], reviewer["s"], reviewer["e"]), ("reviewer", 205, 230))
        self.assertEqual(run["now"], 400)
        self.assertEqual([(s["t"], s["k"], s["d"], s["x"]) for s in builder["steps"]],
                         [(10, "Bash", "Fetch the issue", 0), (40, "Edit", "index.html", 1), (200, "StructuredOutput", "", 0)])

    def test_both_agents_of_a_change_are_filed_under_its_issue(self):
        self.a_build()
        self.assertEqual([a["subject"] for a in read_run(self.run)["agents"]], ["Issue #12", "Issue #12"])

    def test_an_agent_is_working_until_the_journal_holds_its_result(self):
        self.a_build()
        self.assertEqual([a["done"] for a in read_run(self.run)["agents"]], [True, False])

    def test_with_no_journal_every_agent_counts_as_finished(self):
        self.a_build()
        (self.run / "journal.jsonl").unlink()
        self.assertEqual([a["done"] for a in read_run(self.run)["agents"]], [True, True])

    def test_the_page_holds_no_command_and_no_full_path(self):
        self.a_build()
        html = page(read_run(self.run), self.product)
        self.assertIn("Fetch the issue", html)
        for hidden in ("sk-secret", "curl", "gh pr diff", "/work/site"):
            self.assertNotIn(hidden, html)

    def test_instructions_that_close_a_script_cannot_break_the_page(self):
        self.agent("x1", [told(0, "Fix the </script><script>alert(1)</script> tag")], {})
        self.assertNotIn("</script><script>alert", page(read_run(self.run), self.product))

    def test_a_half_written_last_line_waits_for_the_next_read(self):
        self.a_build()
        with (self.run / "agent-r1.jsonl").open("a") as record:
            record.write('{"type": "assistant", "timestamp": "' + at(300) + '", "mess')
        self.assertEqual(len(read_run(self.run)["agents"][1]["steps"]), 1)

    def test_a_newer_record_gives_the_step_its_name_and_phase_and_its_real_instructions(self):
        self.agent("n1", [
            told(0, "[Workflow harness — user request] A note from Claude Code:\n  build 12"),
            told(0, "[Workflow harness — computed task] Another note:\n  Build issue #12 in acme/shop"),
            step(5, "Read", {"file_path": "/work/README.md"}, "c1"),
        ], {"agentType": "founding-agents:builder", "description": "builder #12, round 1", "workflowPhase": "Build",
            "pickedEffortModel": "claude-opus-5-5"})
        agent = read_run(self.run)["agents"][0]
        self.assertEqual((agent["label"], agent["phase"], agent["model"]), ("builder #12, round 1", "Build", "claude-opus-5-5"))
        self.assertEqual(agent["brief"], "Build issue #12 in acme/shop")

    def test_runs_come_newest_first_and_only_for_this_product(self):
        self.a_build()
        later = self.run.parent / "wf_two"
        self.agent("z1", [told(900, "Check whether issue #13 can be built")], {}, run=later)
        os.utime(self.run / "agent-b1.jsonl", (START, START))
        os.utime(self.run / "agent-r1.jsonl", (START, START))
        os.utime(later / "agent-z1.jsonl", (START + 900, START + 900))
        self.assertEqual([f.name for f in runs(self.product, self.home)], ["wf_two", "wf_one"])
        other = self.product.parent / "another"
        other.mkdir()
        self.assertEqual(runs(other, self.home), [])

    def test_the_live_board_listens_on_this_machine_only_and_serves_no_file(self):
        self.a_build()
        (self.product / ".env").write_text("TOKEN=sk-secret\n")
        board = server(self.product, self.home)
        self.addCleanup(board.server_close)
        self.assertEqual(board.server_address[0], "127.0.0.1")
        threading.Thread(target=board.serve_forever, daemon=True).start()
        self.addCleanup(board.shutdown)
        url = f"http://127.0.0.1:{board.server_address[1]}"
        run = json.load(urllib.request.urlopen(f"{url}/run.json"))
        self.assertEqual([a["role"] for a in run["agents"]], ["builder", "reviewer"])
        self.assertIn('"live":true', urllib.request.urlopen(f"{url}/").read().decode())
        for path in ("/.env", "/watch.py", "/../.env"):
            with self.assertRaises(urllib.error.HTTPError) as refused:
                urllib.request.urlopen(url + path)
            self.assertEqual(refused.exception.code, 404, path)
            refused.exception.close()


if __name__ == "__main__":
    unittest.main()
