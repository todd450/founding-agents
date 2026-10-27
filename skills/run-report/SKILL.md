---
name: run-report
description: Report a Founding Agents run's time, tokens and API-equivalent cost by role, from Claude Code's session logs, and post it on the run's issue. Use at the end of a build or propose run, or when the founder asks what a run took or cost.
---

# Report a run

Run from the product repo's folder:

- `python3 <this skill's directory>/report.py --workflow build --issue <n> --post` reports the newest
  session that ran `/founding-agents:build <n>` and comments the table on issue `<n>`.
- Use `--workflow propose` for a propose run. For an idea in words, `--issue` is the issue the product
  lead opened.
- Leave out `--post` to print the table only; `--session <path to a .jsonl>` reports on one session
  log directly.

The table gives each role and model its time, model calls, input (new and read from cache), output
and cost, then the total. Post it exactly as the script prints it; do not round, summarise or
reword it.

Cost is API-equivalent at list prices. On a Pro or Max plan the run uses the weekly limit instead,
so the figure compares runs and roles; it is not a bill. If the script finds no session, say so and
post nothing.
