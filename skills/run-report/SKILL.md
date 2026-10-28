---
name: run-report
description: Report a Founding Agents run's time, tokens and API-equivalent cost by role, from Claude Code's session logs, and post it on the run's issue. Use at the end of a build or propose run, or when the founder asks what a run took or cost.
---

# Report a run

Run from the product repo's folder:

- `python3 <this skill's directory>/report.py --workflow build --issue <n> --post` reports the newest
  session that ran `/founding-agents:build <n>` and comments the table on issue `<n>`.
- Use `--workflow propose` for a propose run. For an idea in words, `--issue` is the issue the product
  lead opened; the script finds the run by the report step's own prompt, since the first prompt
  names no issue.
- Use `--workflow plan` for a plan run, with the brief it planned as `--issue`.
- Use `--workflow sweep` for a sweep run, with `--issue` the queue item it opened; it reports the
  newest session that ran a sweep.
- `--budget <dollars>` flags a run that cost more, above the table. The workflows pass their own
  budget.
- `--outcome merged`, `--outcome ready` (approved, left for the founder's merge) or
  `--outcome stopped` records how the run ended, above the table. `build` passes it.
- `python3 <this skill's directory>/report.py --runs` reads every `build` run report on the repo
  and prints the share of runs that ended in a merge without the founder, the share that merged
  only after an earlier run on the issue stopped, the share left ready for the founder's merge, and
  the share that stopped. `--since <date>`
  counts only reports from that date. Use it when the founder asks how often `build` gets a change
  merged on its own.
- Leave out `--post` to print the table only; `--session <path to a .jsonl>` reports on one session
  log directly.

The table gives each role and model its time, model calls, input (new and read from cache), output
and cost, then the total. Post it exactly as the script prints it; do not round, summarise or
reword it.

Each call is priced by the model it actually ran, not the alias a workflow asked for, so the total
matches what Claude Code counts. A model the script has no price for is named above the table and
left out of the cost; add its price to `PRICES` in the script.

Cost is API-equivalent at list prices. On a Pro or Max plan the run uses the weekly limit instead,
so the figure compares runs and roles; it is not a bill. If the script finds no session, say so and
post nothing.
