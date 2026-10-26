"""The build workflow checks the ticket, loops builder and reviewer, and only then merges."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / "workflows" / "build.js"

# Runs the workflow body with agent() answering from a script of replies, one list per label
# prefix, and prints the result and every agent call as JSON.
HARNESS = r"""
const fs = require('fs')
const [source, argsJson, repliesJson] = process.argv.slice(1)
const replies = JSON.parse(repliesJson)
const calls = []
const agent = async (prompt, opts) => {
  calls.push({ label: opts.label, agentType: opts.agentType || null, isolation: opts.isolation || null,
               model: opts.model || null, prompt })
  const key = Object.keys(replies).find(prefix => opts.label.startsWith(prefix))
  return key ? replies[key].shift() : null
}
const body = fs.readFileSync(source, 'utf8').replace('export const meta', 'const meta')
const run = new Function('args', 'agent', 'phase', 'log', `return (async () => {${body}})()`)
run(JSON.parse(argsJson), agent, () => {}, () => {})
  .then(result => console.log(JSON.stringify({ result, calls })))
  .catch(error => console.log(JSON.stringify({ error: error.message, calls })))
"""

READY = {"ready": True, "reason": "", "repo": "o/r", "title": "Add slugify", "body": "Turn titles into slugs."}
PR = {"pr_number": 4, "pr_url": "https://github.com/o/r/pull/4", "stopped_because": ""}
APPROVE = {"verdict": "approve", "findings": []}
CHANGES = {"verdict": "changes", "findings": [{"must_fix": True, "where": "slug.py:3", "what": "empty title crashes"}]}
MERGED = {"merged": True, "merge_commit": "abc1234", "reason": ""}


@unittest.skipUnless(shutil.which("node"), "needs node")
class BuildWorkflowTest(unittest.TestCase):
    def run_workflow(self, replies, args=12):
        out = subprocess.run(["node", "-e", HARNESS, str(WORKFLOW), json.dumps(args), json.dumps(replies)],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    def labels(self, run):
        return [call["label"] for call in run["calls"]]

    def test_an_issue_that_is_not_ready_starts_nothing(self):
        run = self.run_workflow({"check": [{**READY, "ready": False, "reason": "a red issue is open"}]})
        self.assertEqual(run["result"], {"issue": 12, "status": "not started", "reason": "a red issue is open"})
        self.assertEqual(self.labels(run), ["check #12"])

    def test_an_approved_change_goes_to_the_integrator(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "reviewer": [APPROVE], "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")
        self.assertEqual(self.labels(run), ["check #12", "builder, round 1", "reviewer, round 1", "integrator, PR #4"])

    def test_each_role_runs_as_its_plugin_agent_and_the_builder_in_a_worktree(self):
        run = self.run_workflow({"check": [READY], "builder": [PR], "reviewer": [APPROVE], "integrator": [MERGED]})
        builder, reviewer, integrator = run["calls"][1:]
        self.assertEqual((builder["agentType"], builder["isolation"], builder["model"]),
                         ("founding-agents:builder", "worktree", "sonnet"))
        self.assertEqual((reviewer["agentType"], reviewer["model"]), ("founding-agents:reviewer", "opus"))
        self.assertEqual(integrator["agentType"], "founding-agents:integrator")

    def test_the_reviewer_sees_the_issue_but_not_the_builders_reasoning(self):
        run = self.run_workflow({"check": [READY], "builder": [{**PR, "stopped_because": ""}],
                                 "reviewer": [APPROVE], "integrator": [MERGED]})
        prompt = run["calls"][2]["prompt"]
        self.assertIn("Turn titles into slugs.", prompt)
        self.assertNotIn("Return the PR's number", prompt)

    def test_findings_go_back_to_the_builder_on_the_same_pr(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR], "reviewer": [CHANGES, APPROVE],
                                 "integrator": [MERGED]})
        self.assertEqual(run["result"]["status"], "merged")
        second = run["calls"][3]["prompt"]
        self.assertIn("gh pr checkout 4", second)
        self.assertIn("slug.py:3: empty title crashes", second)

    def test_three_send_backs_go_to_the_founder_and_nothing_merges(self):
        run = self.run_workflow({"check": [READY], "builder": [PR, PR, PR], "reviewer": [CHANGES] * 3})
        self.assertIn("the founder decides", run["result"]["status"])
        self.assertNotIn("integrator, PR #4", self.labels(run))

    def test_a_builder_that_stops_without_a_pr_ends_the_run(self):
        run = self.run_workflow({"check": [READY],
                                 "builder": [{"pr_number": 0, "pr_url": "", "stopped_because": "split it in two"}]})
        self.assertEqual(run["result"]["status"], "stopped in build")
        self.assertEqual(run["result"]["reason"], "split it in two")

    def test_takes_the_issue_as_a_number_a_string_or_an_object(self):
        for args in (12, "#12", {"issue": 12}):
            run = self.run_workflow({"check": [{**READY, "ready": False, "reason": "x"}]}, args=args)
            self.assertEqual(run["result"]["issue"], 12)

    def test_no_issue_is_an_error(self):
        self.assertIn("Name the issue", self.run_workflow({}, args=None)["error"])


if __name__ == "__main__":
    unittest.main()
