"""Runs a workflow script under Node with agent() answering from scripted replies."""

import json
import shutil
import subprocess
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"
HAVE_NODE = shutil.which("node") is not None

# Each label prefix in replies has a list of answers, used in turn; a prefix in slow takes that many
# milliseconds to answer. Prints the result (or the error), every agent call, and when each call
# started and ended, as JSON.
HARNESS = r"""
const fs = require('fs')
const [source, argsJson, repliesJson, slowJson] = process.argv.slice(1)
const replies = JSON.parse(repliesJson)
const slow = JSON.parse(slowJson)
const calls = []
const events = []
const agent = async (prompt, opts) => {
  calls.push({ label: opts.label, agentType: opts.agentType || null, isolation: opts.isolation || null,
               model: opts.model || null, effort: opts.effort || null, schema: opts.schema || null, prompt })
  events.push(`start ${opts.label}`)
  const wait = Object.keys(slow).find(prefix => opts.label.startsWith(prefix))
  if (wait) await new Promise(resolve => setTimeout(resolve, slow[wait]))
  events.push(`end ${opts.label}`)
  const key = Object.keys(replies).find(prefix => opts.label.startsWith(prefix))
  return key ? replies[key].shift() : null
}
const body = fs.readFileSync(source, 'utf8').replace('export const meta', 'const meta')
const parallel = thunks => Promise.all(thunks.map(thunk => thunk().catch(() => null)))
const run = new Function('args', 'agent', 'parallel', 'phase', 'log', `return (async () => {${body}})()`)
run(JSON.parse(argsJson), agent, parallel, () => {}, () => {})
  .then(result => console.log(JSON.stringify({ result, calls, events })))
  .catch(error => console.log(JSON.stringify({ error: error.message, calls, events })))
"""


def run_workflow(name, replies, args, slow=None):
    out = subprocess.run(["node", "-e", HARNESS, str(WORKFLOWS / f"{name}.js"), json.dumps(args),
                          json.dumps(replies), json.dumps(slow or {})], capture_output=True, text=True,
                         check=True).stdout
    return json.loads(out)
