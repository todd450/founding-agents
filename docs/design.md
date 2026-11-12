# Design

A team of agents that builds products with one founder.

## The team

| lane | role | runs | produces | may touch |
|---|---|---|---|---|
| Decide | **Product lead** | each new idea, as `propose`'s brief step | a brief (who, what evidence, the appetite, how we'll know); says no by default | issues only |
| | **Designer** | before code, and again after the build; the `design` sweep | mockups to pick from; a review of the rendered screens; at most three findings a sweep: screens that differ, values outside the token source, phone width, states nobody designed | mockups and issues |
| Build | **Architect** | the `architecture` sweep, weekly by default; in `propose`, its choice on any technical one-way door, or a full view when the founder puts it on the panel | at most three findings a sweep: one-way doors that went in undecided, broken interfaces, one thing defined twice, missing day-one defaults | issues only |
| | **Builder** | one decided issue at a time, in its own worktree | the change, with tests written first from the edge-case fixtures | its own worktree |
| Check | **Reviewer** | every change, before merge | reads the diff for correctness, simplicity, tests and undecided one-way doors, then drives the running product through the failure checklist: empty and one-item, other data and account shapes, other language, phone width, failed read, second user, time zones; sees the diff, not the builder's reasoning | read and run |
| | **Security reviewer** | changes that touch routes, sign-in, permissions, storage, secrets, outside input, model calls or shipped dependencies, as the check, the reviewer or the founder says; the `security` sweep | findings | read only, apart from issues and advisories |
| | **Optimiser** | the `codebase` and `tests` sweeps, on demand | page cost, dead code, copied code, and the test suite's missing cases, faults it misses, slow or flaky tests, tests of wording and hand-written checks a standard tool does | issues only |
| Ship & run | **Ops watch** | a daily routine, and a nightly GitHub Actions check | backups, release verdicts, production errors; red reaches the founder; whether each shipped brief did what it said | read plus notifications |
| | **Librarian** | a weekly routine: the week's incidents, and a prune | a lesson as a test or lint rule; keeps the rules file capped; deletes guards for removed things | tests, lint config, docs |

Every role is an agent in `agents/` except where its row says routine, sweep or step. A routine
runs in the cloud on a schedule, from instructions `setup` copies into each product, since a
routine loads no plugin; a sweep's instructions are the sweep skill's own files, run on demand or
as a routine. So there are five agents and nine roles: the product lead is `propose`'s brief step,
ops watch and the librarian are routines, the optimiser is the `codebase` and `tests` sweeps, and
the architect, the designer and the security reviewer are agents that also each run a sweep of
the whole product.

Each role borrows the practices of a team or person known for that job, such as Airbnb for the
designer and Google SRE for ops watch: [exemplars.md](exemplars.md).

## How a change flows

1. Idea → **product lead** writes the brief → founder decides.
2. **Designer** mocks it up → the roles the founder put on the panel recommend → founder picks.
3. **Builders** build the decided issue, each in its own worktree. A brief too big for one change
   is cut into issues in a session first.
4. The **reviewer** reads the diff and drives the product; the **security reviewer** joins when the
   issue or the diff touches routes, sign-in, stored data or secrets, or when the founder asks.
5. Once the reviewers approve and the required checks pass, `build` leaves a "Ready for your
   merge" comment → the **founder** merges on GitHub → **ops watch** watches it run.
6. Two weeks after a brief's last issue merges (or as long as the brief says), **ops watch**
   checks whether it did what "how we'll know" said; a "didn't" goes back to the founder as keep,
   change or remove.

The founder sees steps 1 and 2, step 3 only when a cut is needed, step 5 when a merge is the release they kept, and step 6 when a brief did not work. Every hand-off is a file, a ticket or a PR, so the next agent
starts with the context it needs.

## Principles

1. **Decide before building.** Mockups and briefs are cheap; production code carries costs forever
   (fixes, guards, translations, review).
2. **The builder never grades itself.** A separate evaluator drives the real app against hard pass
   marks. Expect to tune it: Anthropic found Claude a
   lenient QA agent out of the box.
3. **Judgement and edits stay on a strong model; cheap models do what is cheap to check.** Planning,
   building and reviewing run on Opus; checks, queueing and tidying, where a wrong answer is easy
   to spot, run on Haiku or Sonnet. Cursor's swarm puts its workers on cheaper models, but
   Anthropic's own guide keeps code edits on the main model, and so does this team.
4. **Work runs as tickets, not sessions.** One ticket, one agent run, one worktree (OpenAI's
   Symphony, Claude Code's agent-team task list).
5. **Never two writers on the same files.** Parallelism pays only when work splits cleanly.
6. **A gate before production.** With one builder a merge gate costs little; large teams
   dropped single merge gates only at hundreds of agents or tens of thousands of merges a day.
7. **Lessons become code.** A rule that must hold is a test, a lint rule or a hook. The
   always-loaded rules file is a short map into `docs/` (the first product's grew to 4,392 lines
   before it was cut to 337; OpenAI found the same).
8. **Least privilege per role, and per-action approval** by a checking model instead of prompts.
9. **A red scheduled check stops other work** until it is fixed.
10. **Protect the founder's attention.** One decision queue, read once a day; each item carries the
    recommendations the founder asked for, with why in plain English, a picture, and what each
    option costs.

Day-one engineering defaults the architecture and design sweeps check a product for: one front end (no second
document surface), writes that change only the field that changed, string keys from the first
screen, one design-token source that generates every copy.

## How it maps to Claude Code

- **Roles** → agent files in the plugin's `agents/`, each with its model, effort and tools;
  builders also get their own worktree.
- **Procedures** → skills (edge-case checklist, design review from screenshots, release, `setup`,
  and `watch` to see what a run's agents did).
- **The per-change pipeline** → two saved workflows in the plugin, `propose` and `build`. The
  `sweep` skill finds work for `build` instead of starting from the founder's idea.
- **Scheduled roles** (ops watch, librarian, and any sweep the founder schedules) → routines, which `setup` creates in each product
  because a plugin cannot ship them. Ops watch's checks that need no judgement run as GitHub
  Actions schedules instead, which `setup` installs in the product.
- **How the agents behave** → the eval tasks in `evals/`, run with `claude -p` before a version
  bump that changes an agent, skill, workflow or model.
- **Hard rules** → plugin hooks (no session pushes to `main` or merges; a local preview
  binds to this machine and serves no secret) and GitHub branch
  protection (nothing merges without passing checks).

## Decisions

Each decision is the rule as it stands and why, grouped by topic. They were made against the
Claude Code docs and the plugins that already cover parts of this (see Sources).

### Packaging and setup

- **One plugin plus a `setup` skill.** The plugin ships the agents, skills, hooks and workflows.
  `setup` does each product's part, which a plugin cannot ship: the routines, branch protection,
  the labels, and a starter `CLAUDE.md`, `check.sh` and `fixtures/` that the
  product then owns.
- **A change a product should get bumps the plugin's version,** since an install updates only when
  the version changes. A docs-only change does not.
- **The plugin stays generic.** It holds the failure classes; each product keeps its own fixtures
  and rules.
- **The plugin repo is public, under MIT.** A plugin installs from its repo, so a private one
  leaves the public website pointing at a team nobody else can install. Each person runs the team
  on their own login, and the plugin never ships or shares a token. Until 1.0 any version may change the team, and pull
  requests come by invitation.
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
  `propose` ends at the brief and mockups, and `build` at the merge. A workflow never reads the clock or random numbers.
- **Every decision put to the founder is a script-built queue item** with the brief's
  recommendation, the designer's pick and the view of each role the founder put on the panel.
  Each role picks without seeing the others; with two or more on the panel, an Opus step weighs
  them on their reasons and names any role that disagrees.

### Deciding: `propose`

- **`propose`: brief, then mockups, then one queue item.** `/founding-agents:propose <issue or
  idea>`. The brief step writes the brief into the issue, recommends go or no-go, says whether it
  changes anything on screen, and names every technical one-way door it settles. On a go with
  something on screen, the designer storyboards the journey and makes two or three options at
  different stars. A no-go skips the mockups, which would be spent allowance, but still reaches the
  founder, who can overrule it. The founder answers with a letter and `decided`, and `build` hands
  that answer to the builder and the reviewers.
- **The founder chooses the panel on each run.** Decided 9 Nov 2026. `propose 7` asks no one
  beyond the brief and the designer; `propose 7 builder reviewer` adds those two, `propose 7 all` every
  role, and an idea takes `panel: ...` at its end. A role that does not exist is refused with the
  choices. The architect still gives its choice on any technical one-way door the brief names,
  panel or not, since those are the founder's and the costliest to get wrong. The team step runs
  only with two or more roles on the panel; with fewer there is nothing to weigh. Until then every
  brief got five roles' views and an Opus team step (the founder asked on 2 Nov for every role's
  pick), and on small changes the views mostly repeated the designer's reasons. Choosing the panel
  per run, as with a sweep's kind, keeps the views for the ideas that need them, and `propose`
  does not change when the roles do.
- **The product lead is a step, not an agent.** Since 9 Nov 2026 the brief step's prompt holds
  what the product lead agent knew (Shape Up's appetite and no-gos, no by default, evidence apart
  from inference, a check-back the routine can read), so `propose` is the only place it lives.
- **A design iteration skips the brief.** `propose` on an issue labelled `design` changes how a
  screen already built looks or reads, so there is no who or evidence to weigh, and the brief's
  default no would only slow it. The issue names the screen, what is wrong with it and what must
  stay, or `propose` does not start. The designer screenshots the screen as it is, then two
  options close to it are built at once; no option may need a technical one-way door. "Keep it as
  it is" stands beside the options, and the pick goes straight to `build`. It is a mode of
  `propose` rather than a workflow of its own, because it ends at the same decision.
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

### One-way doors and build issues

- **Technical one-way doors reach the founder before they are built in.** A one-way door is a
  choice that costs a lot to reverse once code or people depend on it, such as a framework, a build
  step, how the product deploys or stores data, or a dependency that ships to users. The product
  lead names each one in the brief, the founder answers it in a queue item, and `build`, the
  builder and the reviewer each refuse one the founder has not said yes to. A check tool run
  from `check.sh` is never one.
- **No planning workflow.** `plan`, where the architect cut a decided brief into build issues and
  seven roles then weighed in on each open decision, was dropped: cutting a brief takes a few
  minutes in a session, and up to nine agent calls to advise on one decision cost more than the
  advice was worth.
- **Pass marks are ones the reviewers can check, or the founder's by name.** A pass mark that needs
  a dashboard, a login or the live site goes under "The founder checks", and no reviewer sends a
  change back for it.

### Building

- **`build` runs a check, the builder and the reviewers, then readies the PR for the founder.** The check refuses an
  issue that is not decided, settles an unanswered one-way door, or arrives while a `red` issue is
  open. The builder and each reviewer work in their own worktree, which the workflow asks for (an
  agent file's own `isolation` did not give a reviewer one), and reviewers see the issue and
  the PR, never the builder's summary. After three rounds, or when a fixed must-fix comes back, the
  run stops for the founder.
- **One issue per run.** `build` once built every issue `plan` cut from a brief, two to four
  builders at once. With `plan` gone nothing cut those issues, so that mode was dropped: a run
  builds the one issue it is given.
- **Agents that run at once keep out of each other's way,** each with its own scratch folder and
  port, stopping only the server it started.
- **Builders use standard tools before writing checks, and test behaviour, not wording.**
- **Every PR that changes the screen carries before-and-after screenshots,** which the reviewer checks
  against the running product, since the founder reviews from a phone.
- **The builder runs the tests near its change as it works, and the whole suite once before it
  pushes.** On go-bag's #113 it ran the whole suite five times in a 13-minute round, 6.9 minutes of
  it, for a change that passed first time. A break far from the change is caught one step later, by
  that last run or by CI's on the PR, which gates the merge either way.

### Review

- **One reviewer reads the diff and drives the product.** Code review and edge-case QA were two
  agents from 27 Oct to 9 Nov 2026, split so that only QA could read the holdout scenarios. With
  the holdouts gone, the two read the same issue and diff, so one agent does both. It shipped on
  12 Nov 2026, after two go-bag builds: with reviewers reading CI's result, code review took a
  minute of a run and the second reviewer was mostly a second bill.
- **Security review is on request.** The security reviewer joins when the check reads in the issue,
  or the reviewer sees in the diff, a change to routes, sign-in, permissions, stored data, secrets,
  outside input, model calls or a dependency that ships, or when the founder runs
  `build <n> security`; once on, it stays on for that PR. The founder chose a separate reviewer
  over a security checklist inside the reviewer. A change is approved only when every reviewer it
  gets approves.
- **Every change gets the same review.** Risk tiers (code review alone on Sonnet for low risk, QA
  from medium, security review at high, raised by any reviewer) were dropped: rating and raising
  the tier took more workflow than the cheaper low-risk review saved.
- **After the first round, reviewers review only what changed.**
- **Reviewers read CI's result and do not run the suite again.** The builder runs it before it
  pushes, and CI's run on the PR is the one that gates the merge. On go-bag's #113 the suite ran
  about 17 times for a change that passed first time, and with the product's own stop hook that was
  two-thirds of a 31-minute run; four of those runs were reviewers', two at once in one folder at
  190 seconds each where one takes 75. A reviewer runs a test only to settle a finding, and the
  whole suite only when the PR has no checks.
- **A must-fix is something a reader or a user could meet.** A problem only someone the team trusts
  could cause, that review or a loud failure would catch, is a Nit. This was a field on every
  finding and a workflow rule that downgraded such findings; it is now a sentence in the
  reviewer's instructions, and its evals hold it.
- **Every workflow step is told it is one step of a run already going.** Claude Code shows each
  agent the message that started the session, as a request that outranks the step's own task. On
  go-bag's #147 that message was a brief ("check the plugin version, run the build, report"), and
  the Ready and Tidy agents, on Haiku, followed it instead of their step: an approved PR with a
  green check was never handed to GitHub, and no worktree was removed. The Opus and Sonnet steps of
  the same run did their own work. So each step's task opens by saying the request started the run
  and is not the step's to carry out. Not yet seen to hold on a real run.

### Merging and the gate

- **GitHub merges an approved PR once its required checks pass; no agent merges.** Decided
  11 Nov 2026. From 9 Nov, when the integrator went, the founder merged every PR by hand, and two
  days on called the click a hassle: it added nothing the reviewers and the checks had not already
  said. `build`'s last step now asks GitHub to merge (`gh pr merge --auto --squash`), so no agent
  is trusted to merge and nothing goes around a check. The founder still merges by hand a PR whose
  issue lists "The founder checks", one where a reviewer's findings were left to them, one in a
  repo that requires no check (asking there would merge with nothing checked), and one where the
  ask is refused: on Half Badger auto mode refused three of four of the integrator's merges that
  deploy, and a refusal now costs a click, not the run. The integrator stays gone: it needed an
  agent, a hook exemption for its name and an `autoMode` entry in the founder's own settings.
- **The gate: GitHub branch protection with required checks, plus a plugin hook.** `setup` makes
  one CI job, `check`, required on `main`, and requires a PR to be up to date before it merges; it
  runs `check.sh`, the product's single command for every check, which the product owns. The hook
  blocks `git push` to `main` and `gh pr merge` for every session and agent. One merge passes,
  `gh pr merge --auto` without `--admin`, and never from one of the team's roles, so whoever
  builds or reviews a change does not ship it. The hook cannot see a review: `build` asks only
  after its reviewers approve, and a session that asks on its own is held by the required checks
  alone. Hooks are best-effort, so the hard gate is GitHub's.
- **Test the merge, not the branch.** Branch protection's up-to-date rule is the Not Rocket
  Science Rule: GitHub refuses a merge whose checks ran against an older `main`. `build`'s last
  step brings the PR up to date (`gh pr update-branch`) and waits for its required checks before
  it asks GitHub to merge or posts "Ready for your merge", so neither the ask nor the founder's
  click is refused. It does neither while a check fails or a `red` issue is open, and it never
  works around a refusal (principle 8).
- **Nothing merges while a `red` issue is open** (principle 9).

### Edge cases

- **No hidden scenarios.** The reviewer runs the product's visible fixtures and makes its own cases
  from the failure checklist; builders see everything the reviewer sees. Holdout scenarios, kept from builders in a
  private repo behind a hook, were dropped: for one founder, the repo, the hook and their setup
  weighed more than the cases they added.

### Finding work: sweeps and routines

- **Five sweeps, each standing alone.** `/founding-agents:sweep <kind>` reviews the whole product
  for one kind of work: architecture, design, security, the codebase or the tests. A kind needs
  nothing another found and files only its own issues, so the founder runs or schedules any one
  alone. Each files at most three `needs-founder` issues a run, titled `Sweep (<kind>): …`, with
  evidence, pass marks and any technical decisions; the founder adds `decided` to the ones to
  build. On a public repo a security finding's details go in a private draft advisory.
- **A sweep is a file, not a workflow.** Each kind is one file in the sweep skill, beside one file
  of rules all five share, and the same files serve a run on demand (a subagent on the kind's
  model, in its own worktree) and a routine (`setup` copies them into the product). The `sweep`
  workflow they replaced ran only three kinds, and a routine can run no workflow, so the weekly
  architecture review had needed a second copy of its instructions. A kind runs on one model
  rather than a model per step. The optimiser agent went with the workflow: its practices are the
  `codebase` and `tests` files. The architect's agent file still repeats the architecture sweep's
  practices, for its view in `propose`.
- **Routines propose, never change.** The librarian asks which check would have stopped each of
  the week's incidents. It runs weekly and files at most three `needs-founder` proposals, built
  through `build` like any change, and never proposes cutting a check or a review for tokens alone.
  A routine loads no plugin, so its instructions are a file `setup` copies into the product and
  keeps current.
- **Architecture review is weekly, not per change.** It was the architect's `plan` step for each
  brief; with `plan` gone, the architecture sweep run weekly looks at what merged and catches the
  same drift for one Opus run a week, and the founder wanted it periodic. `setup` suggests design
  and security monthly and the rest on demand, since five weekly sweeps could add fifteen issues a
  week to the queue.
- **Ops watch is a nightly check with no model, plus a daily routine.** The nightly GitHub Actions
  job checks the deploy and every link, so it runs even when the week's limit is used up. The daily
  routine checks that scheduled jobs still run, `main` passes, merges are live, and whatever the product lists in `.github/ops-watch/watch.md`. A failing check
  opens one `red` issue that the next green run closes; a check that could not run is reported,
  never red.

### Cost, models and evals

- **Every agent and step names its model.** Opus 5.5 plans, judges and builds: the brief,
  architect, designer, builders, the reviewer and the security reviewer, and the architecture, design
  and security sweeps. Sonnet 5.5 runs the librarian's routine, the codebase and
  tests sweeps and the roles' views; Haiku 5.5
  runs ops watch and the workflows' small steps. `setup` pins all three in full, since an alias
  can resolve to an older model: `opus` has run an older, dearer Opus, and `haiku` still means
  Haiku 4.5 on an older Claude Code.
- **Every agent and step names its effort too, and effort goes up before the model does.** Decided
  11 Nov 2026, from Anthropic's model guide. The builder, the reviewers, the designer and the brief
  had named a model and no effort, so each ran on whatever the session that started the run was
  set to. They now start at medium, where the guide measured Opus 5.5 about 2.5 points below high
  for about 70% of the cost. Two steps run at high: the security review, where a miss costs most,
  and the builder on a change the reviewers sent back, where medium has already fallen short.
  That follows the guide's order when a result is not good enough: let the model check its own
  work (the builder's tests), then raise effort, and only then move up a model. Running
  everything at high costs more and, in the guide's numbers, passes less often than a cheap first
  try with the failures run again harder.
- **Fable 5.2 was tried and Opus 5.5 stays.** On 11 Nov 2026 the builder's seven eval tasks and
  the brief's one ran on both, one trial each. Both passed every task; Fable cost $1.07 a builder
  task against Opus's $0.46, and $1.52 for the brief against $0.54. The tasks are ordinary build
  failures that Opus already passes, so they cannot show Fable doing better, only that it costs
  more here. The guide recommends Fable for large refactors and architecture planning; the
  architect has no eval task, so that is untested. Try it again when a real run fails on Opus at
  high effort, which adds the task that could tell them apart.
- **The team does not measure its own cost.** Run reports, per-issue budgets, a weekly token
  routine and a skill comparing PRs made with and without the plugin were dropped: measuring the
  team had become work of its own. Claude Code's own usage view covers what a run costs, and a
  change sent back three times still stops for the founder.
- **The founder can watch a run, from the record Claude Code already keeps.** Decided 11 Nov 2026.
  The `watch` skill draws a run as a timeline, a close-up of each agent's steps, waits and failed
  steps, and a live board of who is working and who has gone quiet. The founder asked for it to
  see where to improve the team: on the Half Badger run of 27 Oct it showed one change that took
  three rounds and a QA pass that spent 12 of its 30 minutes waiting on a stalled browser run.
  It is not the measuring dropped above. It reads the per-agent
  files Claude Code writes for every workflow run, so no agent or workflow step reports anything,
  a run costs no more tokens, and nothing is posted or kept; and it shows time and steps, not
  tokens or cost. The page leaves out every command and its output, which can hold a secret, and
  the live board answers only this machine with the page and the run's data, never a file.
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
3. **`build` with three roles:** one builder and one reviewer, with the founder merging, run on three to five
   real issues.
4. **The decide lane:** the brief and the designer as `propose`, feeding `needs-founder`. A
   product that can build nothing until its words and look are decided, such as a website, takes
   this step before step 3.
5. **Grow on demand:** the security reviewer, the librarian, and the sweeps, each once its kind of
   work appears.

Every step is built. Still to run on a real product: a `tests`, `design` or `security` sweep, a
sweep as a routine, security review on request and the check-back.

## Sources

- Cursor — [Agent swarms and the new model economics](https://cursor.com/blog/agent-swarm-model-economics) (Jul 2026)
- Anthropic — [Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps) (Mar 2026),
  [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (Jan 2026)
- OpenAI — [Harness engineering](https://openai.com/index/harness-engineering/) (Feb 2026),
  [Symphony](https://openai.com/index/open-source-codex-orchestration-symphony/) (Apr 2026)
- Ramp — [Why we built our background agent](https://builders.ramp.com/post/why-we-built-our-background-agent), for
  screenshots in every PR
- Anthropic — [Which Claude model should you build with?](https://claude.dev/blog/which-claude-model-should-you-build-with/)
  (Nov 2026), for effort before model and edits on the strong model
- Claude Code docs — [agent teams](https://code.claude.com/docs/en/agent-teams),
  [plugins](https://code.claude.com/docs/en/plugins/components), [workflows](https://code.claude.com/docs/en/workflows),
  [routines](https://code.claude.com/docs/en/routines) and [costs](https://code.claude.com/docs/en/costs)
- Existing plugins borrowed from — [Superpowers](https://github.com/obra/superpowers),
  [fayerman-source/agent-team](https://github.com/fayerman-source/agent-team),
  [GSD Core](https://github.com/open-gsd/gsd-core),
  [claude-code-merge-queue](https://github.com/funador/claude-code-merge-queue)
- Each role's exemplar — listed in [exemplars.md](exemplars.md)
