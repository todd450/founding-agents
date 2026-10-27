#!/usr/bin/env python3
"""PreToolUse hook: only edge-case QA reads the holdout scenarios.

Holdouts are edge-case scenarios the builder never sees, so passing them shows the code handles a
failure class, not just the cases it was tested against (docs/design.md, "Holdout scenarios").
They live in a private `<product>-holdouts` repo cloned under ~/.founding-agents/holdouts, outside
every product folder and worktree. This hook blocks any agent but QA from a tool call
that names that folder or that repo. Sessions with no agent, the founder's own, pass: they set
the holdouts up and write them. Like the merge guard this is best-effort, since a shell can reach
a file without naming it.
"""

import json
import sys

QA = "founding-agents:qa"
MARKS = (".founding-agents", "-holdouts")


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    agent = event.get("agent_type")
    if not agent or agent == QA:
        return 0
    if not any(mark in json.dumps(event.get("tool_input") or {}) for mark in MARKS):
        return 0
    print(
        f"Blocked the {agent} agent from the holdout scenarios. Only founding-agents QA "
        "reads them; build from the product's visible fixtures and handle the whole failure class.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
