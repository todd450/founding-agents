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

- **Roles** → agent files in `.claude/agents/`, each with its model, effort and tools.
- **Procedures** → skills (edge-case checklist, design review from screenshots, release).
- **The per-change pipeline** → a saved workflow (build → QA and review → integrate).
- **Scheduled roles** (ops watch, optimiser, librarian) → routines.
- **Hard rules** → hooks: builders cannot push to `main`; nothing merges without passing checks.

## Open decisions

- **Packaging:** a Claude Code plugin, a template repo to copy, or both.
- **Ticket store:** GitHub Issues, Linear, or markdown files in the repo.
- **Coordination:** Claude Code agent teams (experimental, off by default) or subagents plus
  workflows.
- **Where the decision queue lives:** an artifact page, an issue label, or a file.
- **Models and budget:** which model per role, and a token budget per change.
- **What is generic:** the edge-case checklist names failure classes; each product supplies its own
  fixtures.

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
