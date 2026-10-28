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

- **Packaging: one plugin plus a `setup` skill.** The plugin ships the agents, skills, hooks and
  workflows. Plugins cannot ship scheduled routines, and routines are not shared between people, so
  `setup` does the per-product part: the routines, branch protection for `main`, the labels, the
  fixtures folder, the holdout repo and the product's short `CLAUDE.md`. There is no template repo
  to copy and then fall out of sync with.
- **The plugin's version changes with every change a product should get.** A merged change that
  adds or alters an agent, skill, hook or workflow bumps `.claude-plugin/plugin.json`; a docs-only
  change does not. An install keeps its copy by version, and `claude plugin update` calls a plugin
  current while its version is unchanged.
- **`setup` writes starters the product then owns.** A short `CLAUDE.md` (what it is, `./check.sh`,
  where decisions live, its own rules), `check.sh`, and a `fixtures/` folder whose README names the
  holdouts' failure classes, which a test keeps in step. None is replaced once the product has one.
  `setup` also creates the `red` label, so `build` and the integrator can check for red before ops
  watch first raises it, and the routines arrive with the roles that run them.
- **Generic vs product.** The plugin holds the edge-case checklist, which names failure classes;
  each product supplies its own fixtures and holdouts, and keeps its own rules in its own repo.
- **The plugin repo stays private** while the founder is its only user.
- **Each person runs the team on their own login.** Anthropic's terms cover one subscriber's
  ordinary use through `claude -p`, a `claude setup-token` token for CI, and routines. The plugin
  never ships or shares a token; anyone else signs in with their own account or an API key.
- **Each role learns from a named exemplar** ([exemplars.md](exemplars.md)). A named practice
  ("storyboard the journey", "test the merge, not the branch") gives an agent something concrete to
  do and gives the founder words to correct it with; "be a great designer" does neither. Roles
  borrow practices, not looks. The founder picks the exemplars, since they are taste.
- **Borrow, don't depend.** Suites that cover parts of this (gstack, Compound Engineering,
  Superpowers, GSD) churn, and their auto-triggered skills would compete with these roles. Ideas
  are copied with credit once the licence allows: Superpowers' test-first and worktree skills, the
  lessons in fayerman-source/agent-team, GSD's rule that the orchestrator never writes code, and a
  local merge queue for the integrator. Products that use the team turn the overlapping plugins
  off.

### Tickets, the queue and the workflows

- **Tickets: GitHub Issues.** PRs and merges already live there, and `gh` reaches all of it.
  Markdown ticket files would put every builder on the same files (principle 5); Linear adds
  another login.
- **Decision queue: a `needs-founder` issue label.** GitHub's phone app already notifies, and an
  issue holds the recommendation, the pictures and what each option costs.
- **Coordination: subagents plus saved workflows, not agent teams.** The pipeline is sequential,
  agent teams are experimental and off by default, and separate sessions messaging each other fail
  at the messages.
- **Workflows split where the founder decides.** A workflow cannot stop mid-run to ask, so each
  one ends where the founder decides: `propose` ends at the brief and mockups, `plan` at the build
  issues for a decided brief, and `build` at the merge. `sweep` finds work for `build`. A workflow
  never reads the clock or random numbers, which a test holds. A headless `claude -p` run waits for
  a workflow only 600 seconds unless `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` is set.
- **Queue items are built by a script, not written by a model,** so every item has the same shape:
  the recommendation, each option with its cost and pictures, and how to answer.
- **Every decision put to the founder carries every role's recommendation and the team's.** The
  founder decides better with more to go on. In `propose`'s and `plan`'s queue items each role with
  an agent gives its pick and why, on Sonnet, without seeing the others' picks; an Opus step weighs
  them on their reasons, not by count, and names any role that disagrees. The item leads with the
  team's pick. Each workflow keeps its roles in one list, and a test checks that every agent a
  workflow names has an agent file. A role that returns nothing is left out.

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

- **Technical one-way doors reach the founder before they are built in.** A one-way door costs a
  lot to reverse once code or people depend on it: a framework or none, a build step, how the
  product deploys, its stack, how it stores data, a dependency that ships to users, an outside
  service, an interface others rely on. The product lead names each one a brief settles, even one
  taken for granted; the architect lists those each build issue settles; and the founder answers
  them in a queue item with options, a recommendation and the cost of reversing. `build`'s check
  refuses an issue that settles one the founder has not said yes to, the builder stops rather than
  choose one, and the code reviewer sends back a change that makes one. A check tool run from
  `check.sh` ships to no one, so adding one is never a one-way door, and where a helper lives or
  which list a check reads is the builder's call.
- **`plan`: the architect cuts a decided brief into build issues.** `/founding-agents:plan
  <brief>`. A Haiku check refuses a brief without `decided` or one already cut; the architect, on
  Opus, lists the one-way doors the plan needs. If the founder has answered them all, it opens the
  build issues, each saying "Part of #<brief>", the files it owns (no two share one), its risk
  tier, any "Build after #<n>" and the decisions it settles, and posts the plan on the brief. If
  any is unanswered it opens nothing, posts one queue item, and moves `decided` off the brief, so
  adding it again is the founder's yes. The founder does not label each build issue; their
  attention goes to the decisions, not to approving cuts.
- **Pass marks are ones the reviewers can check, or the founder's by name.** Reviewers check from
  the PR's branch, a server on `127.0.0.1`, the public site and `gh`. A pass mark needing a
  dashboard, a login, an account or the live site after the deploy goes under "The founder
  checks", with when, and no reviewer sends a change back for one. Sweeps follow the same rule.
- **"Build after" is only for a real dependency; consistency is "Matches".** An issue builds after
  another only when it cannot be built or checked without that one merged, and says what it needs.
  Issues that must look or read alike say "Matches #<n>" and both carry the shared thing (the exact
  marker, the wording); `build` never waits on that line.

### Building

- **`build`: check, builder, reviewers, integrator.** `/founding-agents:build <issue>`, from the
  product's folder. The check, on Sonnet since it judges, refuses an issue that is not decided or
  cut from a decided brief, settles an unanswered one-way door, or arrives while a `red` issue is
  open (principle 9); an open PR never makes an issue unready. The builder works in its own
  worktree on `build/issue-<n>` and continues an open PR from its reviews rather than starting
  again. Each reviewer gets its own worktree, so the founder's checkout never moves, and gets the
  issue and the PR, never the builder's summary. Send-backs go to the same PR. After three rounds
  the run stops for the founder, and it stops sooner when a must-fix from an earlier round, posted
  before the builder's latest push, comes back after a fix; a Nit later rated must-fix is new, not
  a repeat. The run ends with the `tidy-worktrees` skill, which removes a workflow agent's worktree
  once everything in it is on GitHub.
- **Builders get their worktree from the workflow step.** A workflow's `agent()` takes
  `isolation: 'worktree'` (and `agentType` for a named agent), so no `git worktree add` fallback is
  needed. It needs a repo with at least one commit.
- **Parallel builders: `build` on a brief builds its issues two to four at a time.** Two by default
  (`build <brief> 3` for three, four at most), since every builder and reviewer draws on the same
  Opus allowance. An issue starts once everything it builds after has merged and is skipped if one
  of those did not. The integrator merges one PR at a time, in approval order, each tested on top of
  the last (principle 6). It is safe only because no two issues share a file (principle 5); a
  builder stops rather than edit a file another issue owns. One run report goes on the brief.
- **Agents that run at once keep out of each other's way.** The builder and the reviewers keep
  scratch files in their worktree or their own `mktemp -d`, typing its full path into each command
  rather than saving it to a fixed file, serve on a free port, and stop only the server they
  started, by its PID, never with `pkill` or `killall` by pattern.
- **Builders use standard tools before writing checks, and test behaviour, not wording.** A
  validator, a linter with rules for the product's conventions, a link checker, an accessibility
  checker and a real browser at phone and desktop widths, all run from `check.sh`; custom tests
  only for the product's own rules and facts. A hand-written check of what a tool does misses what
  the tool catches, so the reviewer sends one back and names the tool and the rule.
- **Every PR that changes the screen carries before-and-after screenshots.** The founder reviews
  from a phone, and a diff that reads well can still look wrong. The builder serves `main` and its
  branch, shoots each page the change shows on at phone and desktop width, and commits only the
  shots to a `screenshots/issue-<n>` branch started empty, so they never land in the product. A
  change with nothing on screen says "No visible change." QA shoots the same pages and sends back
  missing or mismatched shots, since pictures only the builder checks show what the builder hoped.
  Fix rounds retake them.

### Review

- **Review splits into edge-case QA, code review and security review.** Each reviewer works in its
  own worktree and posts its own comment. A change is approved only when every reviewer it gets
  approves, and the builder receives all their findings, each marked with who raised it. A QA
  must-fix is something QA can show going wrong for someone, or missing from the issue; a test the
  issue did not ask for is a Nit, and how tests are written is code review's.
- **Review is proportional to risk.** Each issue is rated by what it touches. Low (wording or
  static content) gets code review on Sonnet; medium (styling, layout or ordinary logic) adds QA;
  high (routes, sign-in, permissions, stored data, secrets, outside input, model calls or a
  dependency that ships) adds security review, all on Opus. The architect rates each issue, and
  `build`'s check rates an unrated one or raises the rating; when unsure, the higher, and unknown
  counts as high. Any reviewer can raise the tier, adding reviewers at once; nothing lowers it.
  The builder stays on Opus at every tier.
- **Reviewers start as soon as they are needed, and re-review only what changed.** Every reviewer
  a tier needs starts with the others, and one a raise adds starts the moment that review returns.
  The builder runs `check.sh`, opens the PR and returns without waiting for CI; the code reviewer
  reads CI's result and sends back a failing run. From the second round each reviewer reviews only
  the diff since the commit it last saw, what those fixes affect, and whether its findings are
  fixed; what it saw before and did not raise is left alone.
- **A finding's severity depends on who can reach it.** Every finding says who can put the bad
  value where it hurts: anyone, a signed-in user, an outside service, only someone trusted, or no
  one (for the code, its tests or CI). A must-fix that only a trusted writer can reach counts as a
  Nit when review would see the value or the product refuses it loudly (the build, a check or the
  command fails, and nothing wrong is shown, written or sent); the integrator posts those on the PR
  as left for the founder. An ordinary slip that reaches readers, or harm a trusted writer could do
  unseen, stays must-fix. A failing holdout is rated the same way. The workflow, the reviewers and
  the eval graders read one rule.

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
- Spending a plan — [Using Claude Code with your Pro or Max plan](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan),
  Claude Code docs on [costs](https://code.claude.com/docs/en/costs),
  [headless runs](https://code.claude.com/docs/en/headless),
  [authentication](https://code.claude.com/docs/en/authentication),
  [fast mode](https://code.claude.com/docs/en/fast-mode),
  [ultrareview](https://code.claude.com/docs/en/ultrareview) and
  [legal and compliance](https://code.claude.com/docs/en/legal-and-compliance) (read 24 Oct 2026)
- Each role's exemplar — listed in [exemplars.md](exemplars.md)
- Existing plugins borrowed from — [Superpowers](https://github.com/obra/superpowers),
  [fayerman-source/agent-team](https://github.com/fayerman-source/agent-team),
  [GSD Core](https://github.com/open-gsd/gsd-core),
  [claude-code-merge-queue](https://github.com/funador/claude-code-merge-queue)
- Screenshots in every PR — Ramp, [Why we built our background agent](https://builders.ramp.com/post/why-we-built-our-background-agent)
- Evals — Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (Jan 2026)
- Learning from runs — Anthropic, [Getting started with loops](https://claude.com/blog/getting-started-with-loops);
  Ramp, [Why we built our background agent](https://builders.ramp.com/post/why-we-built-our-background-agent)
  (read 27 Oct 2026)
- Holdout scenarios — [StrongDM Software Factory](https://rywalker.com/research/strongdm-factory)
  (a third-party write-up, Sep 2026)
