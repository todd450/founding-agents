# Design

A team of agents that builds products with one founder.

## The team

| lane | role | runs | produces | may touch |
|---|---|---|---|---|
| Decide | **Product lead** | each new idea; a weekly scope review | a one-paragraph brief (who, what evidence, how we'll know); says no by default; owns the decision queue | no code |
| | **Designer** | before code, and again after the build | mockups to pick from; a review of the rendered screens | mockups only |
| Build | **Architect** | each new surface; any schema or shared change | the plan builders work from, with the day-one defaults set | plans, schema review |
| | **Builders** (2–4) | in parallel, one worktree each | the change, with tests written first from the visible edge-case fixtures | their own worktree; never the holdouts |
| | **Edge-case QA** | every medium- or high-risk change, before merge | the failure checklist: empty and one-item, other data and account shapes, other language, phone width, failed read, second user, time zones; run against the visible fixtures and the holdout scenarios builders never see | read and run; the only role that reads the holdouts |
| Check | **Code reviewer** | every change, on Sonnet when it is low risk | correctness and simplification; sees the diff, not the builder's reasoning | read only |
| | **Security reviewer** | high-risk changes: routes, sign-in, permissions, storage, secrets, outside input, model calls or shipped dependencies; a `security` sweep | findings | read only |
| | **Optimiser** | a weekly routine, for team cost; an agent in a `codebase` or `tests` sweep, for product cost | token cost per merged change, by role and model (weekly); page cost, dead code, one thing defined in several places, and the test suite's missing cases, slow or flaky tests, tests of wording and hand-written checks a standard tool does (sweep) | proposes builder tasks |
| Ship & run | **Integrator** | the only agent that merges | rebase, run checks, gate production, cut releases; where a merge deploys to production, readies it for the founder's merge | `main` and production |
| | **Ops watch** | a daily routine, and a nightly GitHub Actions check | backups, release verdicts, production errors, spend; red reaches the founder; whether each shipped brief did what it said | read plus notifications |
| | **Librarian** | a weekly routine: the week's incidents, and a prune | a lesson as a test or lint rule; keeps the rules file capped; deletes guards for removed things | tests, lint config, docs |

Every role is an agent in `agents/` except where its row says routine. A routine runs in the cloud
on a schedule, from instructions `setup` copies into each product, since a routine loads no plugin.
So there are nine agents and eleven roles: ops watch and the librarian are routines only, and the
optimiser is both.

Each role borrows the practices of a team or person known for that job, such as Airbnb for the
designer and Google SRE for ops watch: [exemplars.md](exemplars.md).

## How a change flows

1. Idea → **product lead** writes the brief → founder decides.
2. **Designer** mocks it up → each role recommends, then the team → founder picks.
3. **Architect** writes the plan and cuts it into build issues → **builders** build, each in its own
   worktree.
4. The reviewers the issue's risk calls for run in parallel: **code review** always, **edge-case QA** from
   medium, the **security reviewer** at high.
5. **Integrator** merges and gates production, or, where a merge deploys to production, readies
   the PR for the founder to merge → **ops watch** watches it run.
6. Two weeks after a brief's last issue merges (or as long as the brief says), **ops watch**
   checks whether it did what "how we'll know" said; a "didn't" goes back to the founder as keep,
   change or remove.

The founder sees steps 1 and 2, step 3 only when the plan needs a technical decision the brief
left open, step 5 when a merge is the release, and step 6 when a brief did not work. Every hand-off is a file, a ticket or a PR, so the next agent
starts with the context it needs.

## Principles

1. **Decide before building.** Mockups and briefs are cheap; production code carries costs forever
   (fixes, guards, translations, review).
2. **The builder never grades itself.** A separate evaluator drives the real app against hard pass
   marks, including scenarios the builder never saw. Expect to tune it: Anthropic found Claude a
   lenient QA agent out of the box.
3. **The strongest model plans; cheaper models build.** Cursor's current swarm splits planners and
   workers this way; workers used most of the tokens.
4. **Work runs as tickets, not sessions.** One ticket, one agent run, one worktree (OpenAI's
   Symphony, Claude Code's agent-team task list).
5. **Never two writers on the same files.** Parallelism pays only when work splits cleanly.
6. **A gate before production.** At two to four builders a merge queue costs little; large teams
   dropped single merge gates only at hundreds of agents or tens of thousands of merges a day.
7. **Lessons become code.** A rule that must hold is a test, a lint rule or a hook. The
   always-loaded rules file is a short map into `docs/` (the first product's grew to 4,392 lines
   before it was cut to 337; OpenAI found the same).
8. **Least privilege per role, and per-action approval** by a checking model instead of prompts.
9. **A red scheduled check stops other work** until it is fixed.
10. **Protect the founder's attention.** One decision queue, read once a day; each item carries the
    team's recommendation and each role's, with why in plain English, a picture, and what each
    option costs.

Day-one engineering defaults the architect sets for a new product: one front end (no second
document surface), writes that change only the field that changed, string keys from the first
screen, one design-token source that generates every copy.

## How it maps to Claude Code

- **Roles** → agent files in the plugin's `agents/`, each with its model, effort and tools;
  builders also get their own worktree.
- **Procedures** → skills (edge-case checklist, design review from screenshots, release, `setup`,
  `run-report`, `compare-changes`).
- **The per-change pipeline** → three saved workflows in the plugin: `propose`, `plan` and `build`,
  and a fourth, `sweep`, that finds work for `build` instead of starting from the founder's idea.
- **Scheduled roles** (optimiser, librarian) → routines, which `setup` creates in each product
  because a plugin cannot ship them. Ops watch's checks that need no judgement run as GitHub
  Actions schedules instead, which `setup` installs in the product.
- **How the agents behave** → the eval tasks in `evals/`, run with `claude -p` before a version
  bump that changes an agent, skill, workflow or model.
- **Hard rules** → plugin hooks (only the integrator pushes to `main` or merges; only QA reads the
  holdouts; a local preview binds to this machine and serves no secret) and GitHub branch
  protection (nothing merges without passing checks).

## Decisions

Each decision is the rule as it stands and why, grouped by topic. They were made against the
Claude Code docs and the plugins that already cover parts of this (see Sources).

### Packaging and setup

- **One plugin plus a `setup` skill.** The plugin ships the agents, skills, hooks and workflows.
  `setup` does each product's part, which a plugin cannot ship: the routines, branch protection,
  the labels, the holdout repo, and a starter `CLAUDE.md`, `check.sh` and `fixtures/` that the
  product then owns.
- **A change a product should get bumps the plugin's version,** since an install updates only when
  the version changes. A docs-only change does not.
- **The plugin stays generic.** It holds the failure classes; each product keeps its own fixtures,
  holdouts and rules.
- **The plugin repo stays private** while the founder is its only user. Each person runs the team
  on their own login, and the plugin never ships or shares a token.
- **Each role learns from a named exemplar** ([exemplars.md](exemplars.md)), which the founder
  picks: a named practice gives an agent something concrete to do and the founder words to correct
  it with.
- **Borrow, don't depend.** Ideas from other agent suites are copied with credit, not depended on,
  since those suites churn and their skills would compete with these roles.

### Tickets, the queue and the workflows

- **Tickets are GitHub Issues, and the decision queue is the `needs-founder` label.** PRs already
  live there, and GitHub's phone app notifies.
- **Saved workflows run subagents, not agent teams,** since the pipeline is sequential.
- **Workflows split where the founder decides,** since a workflow cannot stop mid-run to ask:
  `propose` ends at the brief and mockups, `plan` at the build issues, and `build` at the merge.
  `sweep` finds work for `build`. A workflow never reads the clock or random numbers.
- **Every decision put to the founder is a script-built queue item** with every role's
  recommendation and the team's. Each role picks without seeing the others; an Opus step weighs
  them on their reasons and names any role that disagrees.

### Deciding: `propose`

- **`propose`: brief, then mockups, then one queue item.** `/founding-agents:propose <issue or
  idea>`. The product lead writes the brief into the issue, recommends go or no-go, says whether it
  changes anything on screen, and names every technical one-way door it settles. On a go with
  something on screen, the designer storyboards the journey and makes two or three options at
  different stars. A no-go skips the mockups, which would be spent allowance, but still reaches the
  founder, who can overrule it. The founder answers with a letter and `decided`, and `build` hands
  that answer to the builder and the reviewers.
- **Mockups: one HTML page per option on a `propose/issue-<n>` branch, with screenshots in the
  issue.** A page shows real content at real lengths at any width; phone and desktop screenshots
  from the `mockup-screenshots` skill let the founder compare options in the issue without opening
  anything. The branch is never merged, so mockups never become product code.
- **The designer's options are built at once, one designer each.** One designer checks that
  screenshots can be taken (and stops if not), clears an earlier run's mockups, storyboards, and
  writes each option's spec and its pick to `mockups/issue-<n>/storyboard.md`. Then one designer
  per option, each in its own worktree, builds its page and screenshots and touches only its own
  files, so the phase takes about as long as one option. The script builds the result from what
  the branch holds: a missing option is left out and named, and the run stops when fewer than two
  remain, the pick is missing, or the branch holds anything outside the issue's mockups folder.

### Planning: one-way doors and build issues

- **Technical one-way doors reach the founder before they are built in.** A one-way door is a
  choice that costs a lot to reverse once code or people depend on it, such as a framework, a build
  step, how the product deploys or stores data, or a dependency that ships to users. The product
  lead and the architect name each one, the founder answers it in a queue item, and `build`, the
  builder and the code reviewer each refuse one the founder has not said yes to. A check tool run
  from `check.sh` is never one.
- **`plan`: the architect cuts a decided brief into build issues.** Once the founder has answered
  every one-way door the plan needs, each issue names the files it owns (no two share one), its
  risk tier and the decisions it settles. If any is unanswered, it opens nothing and asks.
- **Pass marks are ones the reviewers can check, or the founder's by name.** A pass mark that needs
  a dashboard, a login or the live site goes under "The founder checks", and no reviewer sends a
  change back for it.
- **"Build after" is only for a real dependency.** Issues that must merely look or read alike say
  "Matches #<n>" instead, and `build` never waits on that.

### Building

- **`build` runs a check, the builder, the reviewers and the integrator.** The check refuses an
  issue that is not decided, settles an unanswered one-way door, or arrives while a `red` issue is
  open. The builder and each reviewer work in their own worktree, and reviewers see the issue and
  the PR, never the builder's summary. After three rounds, or when a fixed must-fix comes back, the
  run stops for the founder.
- **Parallel builders: `build` on a brief builds two to four issues at once.** It is safe only
  because no two issues share a file. The integrator still merges one PR at a time, each tested on
  top of the last.
- **Agents that run at once keep out of each other's way,** each with its own scratch folder and
  port, stopping only the server it started.
- **Builders use standard tools before writing checks, and test behaviour, not wording.**
- **Every PR that changes the screen carries before-and-after screenshots,** which QA checks
  against the running product, since the founder reviews from a phone.

### Review

- **Review splits into edge-case QA, code review and security review,** and a change is approved
  only when every reviewer it gets approves.
- **Review is proportional to risk.** Low risk (wording or static content) gets code review alone;
  medium (styling, layout or ordinary logic) adds QA; high (routes, sign-in, permissions, stored
  data, secrets, outside input, model calls or a dependency that ships) adds security review. When
  unsure, the higher. Any reviewer can raise the tier; nothing lowers it.
- **After the first round, reviewers review only what changed.**
- **A finding's severity depends on who can reach it.** A must-fix that only a trusted writer can
  reach counts as a Nit when review would see it or the product refuses it loudly; anything a
  reader, a user or an outside service can reach stays must-fix.

### Merging and the gate

- **The gate: GitHub branch protection with required checks, plus a plugin hook.** `setup` makes
  one CI job, `check`, required on `main`; it runs `check.sh`, the product's single command for
  every check, which the product owns. The hook blocks `git push` to `main` and `gh pr merge` for
  every agent but `founding-agents:integrator`, matched with its plugin prefix so no other agent
  called `integrator` passes. Hooks are best-effort, so the hard gate is GitHub's.
- **The integrator tests the merge, not the branch.** If `main` has not moved since the PR's last
  push, the PR's green checks already tested the merge. If it has, `gh pr update-branch` brings the
  PR up to date and the checks run again.
- **Where a merge deploys to production, the founder merges.** The integrator gets the PR up to
  date and green, then stops; `build` posts a `Ready for your merge` item and carries on with other
  issues. The same happens when Claude Code refuses a merge, which the team never works around
  (principle 8).
- **Nothing merges while a `red` issue is open** (principle 9).

### Holdouts

- **Holdout scenarios: QA keeps some edge-case scenarios hidden from builders.** For each failure
  class, some scenarios are visible fixtures that builders write their tests from; the rest are
  holdouts that only edge-case QA reads. Agents shape code to the tests in front of them without
  meaning to, and Claude is a lenient QA agent out of the box (principle 2), so a scenario the
  builder never saw is the one check it cannot have fitted.
- **How holdouts stay hidden.** They live in a private `<product>-holdouts` repo that `setup`
  creates and clones to `~/.founding-agents/holdouts/<owner>/<name>`, outside every product folder
  and worktree, so nothing in the product points to them; one Markdown file per scenario (setup,
  steps, expected), in a folder per failure class. The `guard_holdouts` hook blocks every agent but
  `founding-agents:qa` from any tool call naming that folder or a `-holdouts` repo; the founder's
  own session passes, since it writes them. Like the merge guard it is best-effort. The founder
  writes the first scenarios, never through an agent, and QA adds one or two where a change touches
  a class with none. A failing holdout is reported by its class and what went wrong, never the
  scenario. A scenario a builder has seen moves into the visible fixtures, which is the founder's
  job for now, and a new holdout replaces it.

### Finding work: sweeps and routines

- **Sweeps find work for `build`.** `/founding-agents:sweep codebase|tests|security` runs a finder
  (the optimiser, or the security reviewer for security) that only reads and runs the product and
  brings at most five ranked findings, each with its evidence, size and pass marks. They go to the
  founder as `sweep` issues in one queue item; the founder decides which to fix, and the rest are
  closed. On a public repo a security finding's details go in a private draft advisory.
- **Routines propose, never change.** The optimiser measures what the team costs to run, and the
  librarian asks which check would have stopped each of the week's incidents. Each runs weekly and
  files at most three `needs-founder` proposals, built through `build` like any change; neither
  proposes cutting a check or a review for tokens alone. A routine loads no plugin, so its
  instructions are a file `setup` copies into the product and keeps current.
- **Ops watch is a nightly check with no model, plus a daily routine.** The nightly GitHub Actions
  job checks the deploy and every link, so it runs even when the week's limit is used up. The daily
  routine checks that scheduled jobs still run, `main` passes, merges are live, spend is within the
  product's budget, and whatever the product lists in `.github/ops-watch/watch.md`. A failing check
  opens one `red` issue that the next green run closes; a check that could not run is reported,
  never red.

### Cost, models and evals

- **Every agent and step names its model.** Opus 5.5 plans, judges and builds: the product lead,
  architect, designer, builders, QA, the code and security reviewers, and the finders. Sonnet 5.5
  runs the integrator, the weekly routines, the roles' views and low-risk code review; Haiku 5.5
  runs ops watch and the workflows' small steps. `setup` pins Opus 5.5 in full, since the `opus`
  alias can resolve to an older, dearer Opus.
- **Every run reports its cost.** The `run-report` skill posts each run's time, tokens and cost by
  role and model on its issue, stalled runs included, and flags a run over its budget. The
  optimiser tracks tokens per merged change, and ops watch raises red when spend passes the
  product's budget.
- **Whether the plugin pays is measured.** The `compare-changes` skill compares merged PRs made
  with and without the plugin on cost, time to merge and fixes needed within two weeks.
- **Nothing falls through to paid billing by accident.** No run meant for the plan sets
  `ANTHROPIC_API_KEY` or uses `--bare`, fast mode or `/code-review ultra`. Whether usage credits
  are on is the founder's call.
- **Evals test the agents' judgement; `tests/` tests the wiring.** Each task in `evals/` comes from
  a real run's failure and is graded by a script. A change to an agent, skill, workflow or model
  runs one trial of the touched roles' tasks before its version bump. The full set, three trials
  each, runs before a release, since one trial shows a change did not break an agent but cannot
  tell a reliable one from a lucky one. Evals run on the founder's machine, sealed off from GitHub,
  and stay out of CI.

## Build order

Each new role or workflow runs on a real change in a real product before the next one is built on
it. A small real product makes a good test bed: it gives every step a real change to run on, and a
fresh one shows the team from its first commit, with no history to work around.

1. **Guardrails.** Branch protection, the plugin hook and a first `setup`. Done when a builder's
   push to `main` is blocked.
2. **Ops watch,** on day one. Its first check is a scheduled job the product runs, or for a new
   product a check of the product itself.
3. **`build` with three roles:** one builder, one reviewer and the integrator, run on three to five
   real issues.
4. **The decide lane:** the product lead and the designer as `propose`, feeding `needs-founder`. A
   product that can build nothing until its words and look are decided, such as a website, takes
   this step before step 3.
5. **Grow on demand:** the architect's `plan`, parallel builders, review split into QA, code and
   security review, the optimiser and the librarian, and `sweep`, each once its kind of work
   appears.

Every step is built. Still to run on a real product: a `tests` or `security` sweep, risk tiers and
the check-back.

## Sources

- Cursor — [Agent swarms and the new model economics](https://cursor.com/blog/agent-swarm-model-economics) (Jul 2026)
- Anthropic — [Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps) (Mar 2026),
  [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (Jan 2026)
- OpenAI — [Harness engineering](https://openai.com/index/harness-engineering/) (Feb 2026),
  [Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) (Apr 2026)
- Ramp — [Why we built our background agent](https://builders.ramp.com/post/why-we-built-our-background-agent), for
  screenshots in every PR
- StrongDM — [Software Factory](https://rywalker.com/research/strongdm-factory) (a third-party write-up, Sep 2026), for
  holdout scenarios
- Claude Code docs — [agent teams](https://code.claude.com/docs/en/agent-teams),
  [plugins](https://code.claude.com/docs/en/plugins/components), [workflows](https://code.claude.com/docs/en/workflows),
  [routines](https://code.claude.com/docs/en/routines) and [costs](https://code.claude.com/docs/en/costs)
- Existing plugins borrowed from — [Superpowers](https://github.com/obra/superpowers),
  [fayerman-source/agent-team](https://github.com/fayerman-source/agent-team),
  [GSD Core](https://github.com/open-gsd/gsd-core),
  [claude-code-merge-queue](https://github.com/funador/claude-code-merge-queue)
- Each role's exemplar — listed in [exemplars.md](exemplars.md)
