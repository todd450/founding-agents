#!/usr/bin/env python3
"""PreToolUse hook for eval trials: no agent, QA included, reaches the machine's real holdouts.

QA keeps holdouts in `~/.founding-agents/holdouts` and pushes new ones to the product's
`-holdouts` repo. A trial keeps the founder's home folder, since the plan's login lives there, so
on 27 Oct 2026 trial QA wrote eval scenarios into the website's real holdouts and pushed them to
GitHub, and later trials, and the website's own QA, ran them. `run.py` passes this hook to every
trial with `--settings`; a trial runs as if holdouts were not set up, as the first runs did.
"""

import json
import sys

MARKS = (".founding-agents", "-holdouts")


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if not any(mark in json.dumps(event.get("tool_input") or {}) for mark in MARKS):
        return 0
    print("The holdout scenarios are not available to this run: treat them as not set up, and write "
          "none.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
