# Design

A team of agents that builds products with one founder. This doc is the spec until the agent files
exist; after that it records the decisions behind them.

## Where it comes from

Home Manual was built from June to October 2026 by one founder and many parallel Claude sessions:
5,410 commits in under five months, with no real users yet. Its history showed four costs, each of
which this team is shaped to prevent:

| cost | evidence in that history | what the team does instead |
|---|---|---|
| Built before deciding | 32 removal commits deleted 61,365 lines in eight days (16–23 Oct); pages were translated and audited days before being cut | A product lead writes a brief and the founder decides before any code |
| Found bugs late | 731 bug-sweep and audit commits, nearly all in October; fixes outnumbered features 2:1 that month | Edge-case QA runs the failure checklist on every change before merge |
| Many writers, one branch | Every push deployed for most of the project; the release gate arrived after 2,985 commits; about a dozen traps from a shared working tree | One worktree per builder; only the integrator merges; a gate before production |
| Red lights left red | The nightly off-site backup failed all 28 runs since it was added | Ops watch runs on a schedule and a red result reaches the founder's phone |

The fifth finding is the constraint on everything: **the founder's attention is the bottleneck.**
545 commits record an owner decision, and they came in bursts across 21 days.

## The team

Four lanes. The founder sits in the middle and is the only one who decides scope and taste.

| lane | role | runs | produces | may touch |
|---|---|---|---|---|
| Decide | **Product lead** | each new idea; a weekly scope review | a one-paragraph brief (who, what evidence, how we'll know); says no by default; owns the decision queue | no code |
| | **Researcher** | ongoing | interview guides, synthesis of what users said, the one metric | no code; never contacts users without the founder |
| | **Designer** | before code, and again after the build | mockups to pick from; a review of the rendered screens | mockups only |
| Build | **Architect** | each new surface; any schema or shared change | the plan builders work from, with the day-one defaults set | plans, schema review |
| | **Builders** (2–4) | in parallel, one worktree each | the change, with tests written first from the edge-case fixtures | their own worktree |
| | **Edge-case QA** | every change, before merge | the failure checklist: empty and one-item, other home/account shapes, other language, phone width, failed read, second user, time zones | read and run |
| Check | **Code reviewer** | every change | correctness and simplification; sees the diff, not the builder's reasoning | read only |
| | **Security reviewer** | changes to routes, permissions, storage or model calls | findings | read only |
| | **Optimiser** | weekly | page cost, dead code, one thing defined in several places | proposes builder tasks |
| Ship & run | **Integrator** | the only merger | rebase, run checks, gate production, cut releases | `main` and production |
| | **Ops watch** | scheduled | backups, release verdicts, production errors, spend; red reaches the founder | read plus notifications |
| | **Librarian** | after each incident; a weekly prune | a lesson as a test or lint rule; keeps the rules file capped; deletes guards for removed things | tests, lint config, docs |

**Start with five:** product lead, designer, builders, a reviewer combining QA and code review, and
the integrator. Add the others when their kind of work appears — except ops watch, which belongs on
day one.

## How a change flows

1. Idea → **product lead** writes the brief → founder decides.
2. **Designer** mocks it up → founder picks.
3. **Architect** writes the plan → **builders** build, each in its own worktree.
4. **Edge-case QA** and **code review** run in parallel.
5. **Integrator** merges and gates production → **ops watch** watches it run.

The founder sees steps 1 and 2 only. Every hand-off is a file, a ticket or a PR, so the next agent
starts with the context it needs.

## Principles

From Home Manual's history, and from what published agent teams reported by October 2026:

1. **Decide before building.** Mockups and briefs are cheap; production code carries costs forever
   (fixes, guards, translations, review).
2. **The builder never grades itself.** A separate evaluator drives the real app against hard pass
   marks. Expect to tune it: Anthropic found Claude a lenient QA agent out of the box.
3. **The strongest model plans; cheaper models build.** Cursor's current swarm splits planners and
   workers this way; workers used most of the tokens.
4. **Work runs as tickets, not sessions.** One ticket, one agent run, one worktree (OpenAI's
   Symphony, Claude Code's agent-team task list).
5. **Never two writers on the same files.** Parallelism pays only when work splits cleanly.
6. **A gate before production.** At two to four builders a merge queue costs little; large teams
   dropped single merge gates only at hundreds of agents or tens of thousands of merges a day.
7. **Lessons become code.** A rule that must hold is a test, a lint rule or a hook. The
   always-loaded rules file is a short map into `docs/` (Home Manual's grew to 4,392 lines before it
   was cut to 337; OpenAI found the same).
8. **Least privilege per role, and per-action approval** by a checking model instead of prompts.
9. **A red scheduled check stops other work** until it is fixed.
10. **Protect the founder's attention.** One decision queue, read once a day; each item carries a
    recommendation, a picture, and what each option costs.

Day-one engineering defaults the architect sets for a new product: one front end (no second
document surface), writes that change only the field that changed, string keys from the first
screen, one design-token source that generates every copy.

## How it maps to Claude Code

- **Roles** → agent files in the plugin's `agents/`, each with its model, effort and tools;
  builders also get their own worktree.
- **Procedures** → skills (edge-case checklist, design review from screenshots, release, `setup`).
- **The per-change pipeline** → two saved workflows in the plugin, `propose` and `build`.
- **Scheduled roles** (ops watch, optimiser, librarian) → routines, which `setup` creates in each
  product because a plugin cannot ship them.
- **Hard rules** → a plugin hook (only the integrator pushes to `main` or merges) and GitHub branch
  protection (nothing merges without passing checks).

## Decisions

Made on 24 Oct 2026, after checking the Claude Code docs and the plugins that already cover parts
of this (see Sources).

- **Packaging: one plugin plus a `setup` skill.** The plugin ships the agents, skills, hooks and
  workflows. Plugins cannot ship scheduled routines, and routines are not shared between people, so
  `setup` does the per-product part: it creates the routines, turns on branch protection for
  `main`, adds the labels and the fixtures folder, and writes the product's short CLAUDE.md. There
  is no template repo to copy and then fall out of sync with.
- **Tickets: GitHub Issues.** PRs and merges already live there, and `gh` reaches all of it.
  Markdown ticket files would put every builder on the same files (principle 5); Linear adds
  another login.
- **Coordination: subagents plus saved workflows, not agent teams.** Agent teams are experimental
  and off by default, and the docs steer sequential work to subagents; this pipeline is sequential.
  Separate sessions messaging each other is the other option, and six of the 31 lessons in a
  published team built that way are about those messages failing.
- **Two workflows, split where the founder decides.** `propose` runs steps 1 and 2 and ends with one
  queue item carrying the brief and the mockups, so the founder decides and picks in one sitting.
  `build` starts from a decided issue and runs steps 3 to 5. A workflow cannot stop mid-run to ask,
  so the founder's decision has to fall between workflows.
- **Builders get their worktree from the workflow step.** A workflow's `agent()` takes
  `isolation: 'worktree'` (and `agentType` for a named agent); the workflow script reference
  documents both, though the public docs page does not. Tested on 24 Oct 2026: such a step ran in
  a fresh worktree under `.claude/worktrees/` on its own branch, and the worktree was removed when
  the step changed nothing. No `git worktree add` fallback is needed.
- **Decision queue: a `needs-founder` issue label.** GitHub's phone app already notifies, and an
  issue holds the recommendation, the mockups and what each option costs. A nicer page comes later
  only if the label proves clumsy.
- **Red lights: ops watch opens a `red` issue, and the integrator merges nothing while one is
  open.** A routine cannot push to a phone itself, but an issue notifies through GitHub, and
  blocking merges is what makes principle 9 hold.
- **The gate: GitHub branch protection with required checks, plus a plugin hook.** The hook reads
  which agent is calling and blocks `git push` to `main` and `gh pr merge` for every agent but the
  integrator. The docs call hook filtering best-effort, so the hard gate sits on GitHub, where
  nothing local can get around it.
- **Models: the strongest model plans and judges; cheaper ones build** (principle 3). Today that is
  Opus 5.5 for the product lead, architect and reviewer, Sonnet 5.5 for builders and Haiku 5.5 for
  ops watch.
- **Generic vs product:** the plugin holds the edge-case checklist, which names failure classes;
  each product supplies its own fixtures and keeps its own rules in its own repo.
- **Borrow, don't depend.** Existing suites (gstack, Compound Engineering, Superpowers, GSD) cover
  parts of this, but they churn (Compound Engineering renamed its commands; GSD's original repo was
  archived) and their auto-triggered skills would compete with these roles. Ideas are copied with
  credit once the licence allows: Superpowers' test-first and worktree skills for builders, the
  lessons in fayerman-source/agent-team, GSD's rule that the orchestrator never writes code, and a
  local merge queue for the integrator. Products that use the team turn the overlapping plugins off.

## Still open

- **What name does a plugin agent report to hooks:** bare, or with the plugin prefix? Not yet
  tested: the test runs headless sessions, which need the `claude` command line signed in. Until
  then the merge guard accepts both `agent-team:integrator` and `integrator`.
- **Token budget per change:** set after measuring the first ten changes.

## Build order

Each step runs on a real change in a real product before the next one starts. Home Manual comes
first: its failures are known, so it shows whether the team prevents them.

1. **Guardrails.** Branch protection, the plugin hook and a first `setup`. Done when a builder's
   push to `main` is blocked. This step also tests which agent name hooks see.
2. **Ops watch.** Day one, as the team table says. Its first check is Home Manual's nightly
   off-site backup.
3. **`build` with three roles:** one builder (own worktree, tests first from the fixtures), one
   reviewer combining QA and code review (read only), and the integrator. Run it on three to five
   real issues.
4. **The decide lane:** product lead and designer as `propose`, feeding `needs-founder`. This
   completes the starting five.
5. **Grow on demand:** the architect for schema or shared changes; two to four parallel builders
   once one is routine; then the security reviewer, optimiser, librarian and researcher as their
   kind of work appears.

## How we'll know it works

One number per cost in the first table, and one for the founder's attention:

| cost | measure | should |
|---|---|---|
| Built before deciding | lines deleted within two weeks of being written | fall |
| Found bugs late | bugs found after merge, against bugs found before | mostly be found before |
| Many writers, one branch | merges not made by the integrator | be zero |
| Red lights left red | age of the oldest open `red` issue | be hours, not days |
| The founder's attention | items in the decision queue each day | fit one sitting |

## Sources

- Cursor — [Agent swarms and the new model economics](https://cursor.com/blog/agent-swarm-model-economics) (Jul 2026),
  [Towards self-driving codebases](https://cursor.com/blog/self-driving-codebases) (Feb 2026),
  [Auto-review](https://cursor.com/blog/agent-autonomy-auto-review) (Jun 2026)
- Anthropic — [Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps) (Mar 2026),
  [Redesigning source control](https://www.anthropic.com/research/redesigning-source-control) (Oct 2026),
  [Building a C compiler with parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) (Feb 2026),
  [Claude Code agent teams](https://code.claude.com/docs/en/agent-teams)
- OpenAI — [Harness engineering](https://openai.com/index/harness-engineering/) (Feb 2026),
  [Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) (Apr 2026)
- Claude Code docs, for the decisions — [Plugin components](https://code.claude.com/docs/en/plugins/components),
  [Hooks](https://code.claude.com/docs/en/hooks), [Workflows](https://code.claude.com/docs/en/workflows),
  [Routines](https://code.claude.com/docs/en/routines), [Worktrees](https://code.claude.com/docs/en/worktrees)
- Existing plugins borrowed from — [Superpowers](https://github.com/obra/superpowers),
  [fayerman-source/agent-team](https://github.com/fayerman-source/agent-team),
  [GSD Core](https://github.com/open-gsd/gsd-core),
  [claude-code-merge-queue](https://github.com/funador/claude-code-merge-queue)
