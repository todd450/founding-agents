---
name: sweep
description: Review the whole product for one kind of work - architecture, design, security, the codebase or the tests - and file at most three findings as needs-founder issues for build. Use when the founder asks for a sweep or a review of one of those, e.g. /founding-agents:sweep design. Each kind also runs on a schedule as a routine setup creates.
---

# Sweep

Five kinds of review, each of the whole product and each standing alone: a kind needs nothing
another found, files only its own issues (titled `Sweep (<kind>): …`) and runs on its own model and
schedule. Each kind's file in `kinds/` holds what it reads, looks for and checks, and
`kinds/every-sweep.md` holds the rules all five follow. The same files serve a run here and a
scheduled routine, which follows the copies `setup` installs under `.github/sweeps/`.

| Kind | Looks at | Model | Suggested schedule |
|---|---|---|---|
| `architecture` | one-way doors made without the founder, broken interfaces, a rule defined twice, day-one defaults | Opus | weekly |
| `design` | screens that differ, values outside the token source, phone width, states nobody designed, generic patterns | Opus | monthly |
| `security` | OWASP ASVS, tried against a local copy; details kept private on a public repo | Opus | monthly |
| `codebase` | page weight, `check.sh` time, dead code, copied code, budgets CI checks | Sonnet | on demand |
| `tests` | planted faults the suite misses, missing cases, flaky or slow tests | Sonnet | on demand |

## Running one now

From the product repo's folder:

1. **Name the kind.** With none, or one not in the table, list the five and ask which. One kind per
   run.
2. **Start one subagent** with the Agent tool, on the kind's model from the table, with
   `isolation: "worktree"`, so what it runs or tries stays out of this checkout, and this prompt,
   with the file's full path filled in: "Follow `<this skill's directory>/kinds/<kind>.md` for the
   repo in your working folder." The sweep runs in the subagent, not here, so the product's files
   stay out of this conversation.
3. **Pass on its last lines:** each issue filed, what it ran, and what it did not get to. A quiet
   run is a fine answer.

To run a kind on a schedule, use `setup`'s "Scheduled sweeps".
