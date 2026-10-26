"""Runs a workflow script under Node with agent() answering from scripted replies."""

import json
import shutil
import subprocess
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"
HAVE_NODE = shutil.which("node") is not None

# Each label prefix in replies has a list of answers, used in turn. Prints the result (or the
# error) and every agent call as JSON.
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


def run_workflow(name, replies, args):
    out = subprocess.run(["node", "-e", HARNESS, str(WORKFLOWS / f"{name}.js"), json.dumps(args),
                          json.dumps(replies)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)
