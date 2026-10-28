# Design

A team of agents that builds products with one founder. This doc is the spec until the agent files
exist; after that it records the decisions behind them.

## The team

Four lanes. The founder sits in the middle and is the only one who decides scope and taste.

| lane | role | runs | produces | may touch |
|---|---|---|---|---|
| Decide | **Product lead** | each new idea; a weekly scope review | a one-paragraph brief (who, what evidence, how we'll know); says no by default; owns the decision queue | no code |
| | **Researcher** | ongoing | interview guides, synthesis of what users said, the one metric | no code; never contacts users without the founder |
| | **Designer** | before code, and again after the build | mockups to pick from; a review of the rendered screens | mockups only |
| Build | **Architect** | each new surface; any schema or shared change | the plan builders work from, with the day-one defaults set | plans, schema review |
| | **Builders** (2–4) | in parallel, one worktree each | the change, with tests written first from the visible edge-case fixtures | their own worktree; never the holdouts |
| | **Edge-case QA** | every change, before merge | the failure checklist: empty and one-item, other data and account shapes, other language, phone width, failed read, second user, time zones; run against the visible fixtures and the holdout scenarios builders never see | read and run; the only role that reads the holdouts |
| Check | **Code reviewer** | every change | correctness and simplification; sees the diff, not the builder's reasoning | read only |
| | **Security reviewer** | changes to routes, permissions, storage, model calls or shipped dependencies; a `security` sweep | findings | read only |
| | **Optimiser** | weekly, for team cost; a `codebase` sweep, for product cost | token cost per merged change, by role and model (weekly); page cost, dead code, one thing defined in several places (sweep) | proposes builder tasks |
| | **Test auditor** | a `tests` sweep | missing cases, slow or flaky tests, tests of wording, hand-written checks a standard tool does | proposes builder tasks |
| Ship & run | **Integrator** | the only merger | rebase, run checks, gate production, cut releases | `main` and production |
| | **Ops watch** | scheduled | backups, release verdicts, production errors, spend; red reaches the founder; whether each shipped brief did what it said | read plus notifications |
| | **Librarian** | after each incident; a weekly prune | a lesson as a test or lint rule; keeps the rules file capped; deletes guards for removed things | tests, lint config, docs |

**Start with five:** product lead, designer, builders, a reviewer combining QA and code review, and
the integrator. Add the others when their kind of work appears — except ops watch, which belongs on
day one.

Each role borrows the practices of a team or person known for that job, such as Airbnb for the
designer and Google SRE for ops watch: [exemplars.md](exemplars.md).

## How a change flows

1. Idea → **product lead** writes the brief → founder decides.
2. **Designer** mocks it up → each role recommends, then the team → founder picks.
3. **Architect** writes the plan and cuts it into build issues → **builders** build, each in its own
   worktree.
4. **Edge-case QA** and **code review** run in parallel.
5. **Integrator** merges and gates production → **ops watch** watches it run.
6. Two weeks after a brief's last issue merges (or as long as the brief says), **ops watch**
   checks whether it did what "how we'll know" said; a "didn't" goes back to the founder as keep,
   change or remove.

The founder sees steps 1 and 2, step 3 only when the plan needs a technical decision the brief
left open, and step 6 when a brief did not work. Every hand-off is a file, a ticket or a PR, so the next agent
starts with the context it needs.

## Principles

From the first product's history, and from what published agent teams reported by October 2026:

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
- **Hard rules** → a plugin hook (only the integrator pushes to `main` or merges) and GitHub branch
  protection (nothing merges without passing checks).

## Decisions

Made on 24 Oct 2026, after checking the Claude Code docs and the plugins that already cover parts
of this (see Sources).

- **Packaging: one plugin plus a `setup` skill.** The plugin ships the agents, skills, hooks and
  workflows. Plugins cannot ship scheduled routines, and routines are not shared between people, so
  `setup` does the per-product part: it creates the routines, turns on branch protection for
  `main`, adds the labels, the fixtures folder and the holdout repo, and writes the product's short
  CLAUDE.md. There is no template repo to copy and then fall out of sync with.
- **The plugin's version changes with every change a product should get.** An install keeps its
  copy by version, and `claude plugin update` reports a plugin as current while its version is
  unchanged: on 26 Oct 2026 the website's install at 0.1.0 still lacked `build` and `propose`
  after both had merged. A merged change that adds or alters an agent, skill, hook or workflow
  bumps `.claude-plugin/plugin.json`; a docs-only change does not.
- **`setup` writes starters the product then owns.** Added on 27 Oct 2026: the `basics` kit gives a
  product a short `CLAUDE.md` (what it is, `./check.sh`, where decisions live, its own rules) and a
  `fixtures/` folder whose README names the same failure classes as the holdouts, which a test
  keeps in step. Like `check.sh`, neither is ever replaced once the product has one; a long
  `CLAUDE.md` is what the first product had to cut from 4,392 lines (principle 7). `setup` also
  creates the `red` label, so `build` and the integrator can check for red before ops watch first
  raises it. The routines arrive with the roles that run them.
- **Tickets: GitHub Issues.** PRs and merges already live there, and `gh` reaches all of it.
  Markdown ticket files would put every builder on the same files (principle 5); Linear adds
  another login.
- **Coordination: subagents plus saved workflows, not agent teams.** Agent teams are experimental
  and off by default, and the docs steer sequential work to subagents; this pipeline is sequential.
  Separate sessions messaging each other is the other option, and six of the 31 lessons in a
  published team built that way are about those messages failing.
- **Workflows split where the founder decides.** `propose` runs steps 1 and 2 and ends with one
  queue item carrying the brief and the mockups, so the founder decides and picks in one sitting.
  `plan` cuts a decided brief into build issues (step 3's plan), and `build` takes one of them, or
  a decided issue small enough to need no plan, through steps 3 to 5. A workflow cannot stop
  mid-run to ask, so the founder's decision has to fall between workflows.
- **Builders get their worktree from the workflow step.** A workflow's `agent()` takes
  `isolation: 'worktree'` (and `agentType` for a named agent); the workflow script reference
  documents both, though the public docs page does not. Tested on 24 Oct 2026: such a step ran in
  a fresh worktree under `.claude/worktrees/` on its own branch, and the worktree was removed when
  the step changed nothing. No `git worktree add` fallback is needed.
- **`build` in its first version: check, then builder and reviewer up to three rounds, then the
  integrator.** It runs as `/founding-agents:build <issue>` from the product's folder. A cheap first
  step refuses an issue without the `decided` label, or while a `red` issue is open (principle 9).
  The builder works in its own worktree on `build/issue-<n>`; the reviewer gets its own worktree
  too, so checking out the PR never moves the founder's checkout. The reviewer is given the issue
  and the PR, not the builder's summary, since it reviews the diff and the running product. Each
  send-back reaches the same builder role on the same PR with the findings; after three, the run
  stops and the PR waits for the founder instead of looping. Every step names its model. Left for
  later: pacing to the weekly limit, described below; the holdout scenarios followed on 27 Oct. Tested on
  25 Oct 2026 with `claude -p "/founding-agents:build 1"` on a throwaway repo: the builder opened
  the PR, the reviewer drove about 30 inputs and sent it back with one must-fix, the builder fixed
  it on the same PR, the reviewer approved with nits only, and the integrator merged it. The
  builder's and reviewer's worktrees stay behind once they hold commits, so they pile up under
  `.claude/worktrees/` until something removes them.
- **`build` continues an open PR, stops on a finding it failed to fix twice, and tidies up.**
  Decided on 26 Oct 2026, from the website's runs. Its first step finds an open PR on
  `build/issue-<n>` or one that closes the issue, and the builder continues it from its reviews
  instead of starting again; #4 and #6 needed their issues edited by hand to do that. The check is told an
  open PR never makes an issue unready: on the website's #27 on 27 Oct, it read PR #35 as "already
  being built" and skipped it, and the six issues that build after it could not start. The reviewer
  marks each must-fix that an earlier review raised and is still unfixed as a repeat, and one
  repeat after a builder's fix ends the run for the founder, before a third round: the stalls on #4
  and #6 were the same findings coming back, at 43% of the website's spend. New findings still get
  the three rounds. A repeat counts only findings from an earlier round, posted before the
  builder's latest push, and from the second round reviewers are given the previous round's
  must-fix list. A Nit an earlier round raised and a reviewer now rates must-fix is a new finding,
  not a repeat, since the builder was allowed to skip it. Both came from the website's #27 on
  27 Oct, where each stopped a run as if a fix had failed twice: first a finding code review had
  raised minutes earlier in the same round, then a link-parsing point the security reviewer had
  parked as informational twice and re-rated in round 4. Every run after its first step then runs the `tidy-worktrees` skill, which
  removes a workflow agent's worktree (`wf_...`) only when it has no uncommitted change and its
  commit is on a branch at origin. A session's own worktree in the same folder is never touched.
  Runs go one at a time, so a running run's worktree is never in the way; parallel builders will
  need this to wait for every run to end.
- **`propose` in its first version: brief, mockups, one queue item.** It runs as
  `/founding-agents:propose <issue or idea>`. The product lead writes the brief into the issue (a new
  one for an idea in words) and recommends go or no-go. On a go, the designer storyboards the journey
  and makes two or three options at different stars. A no-go skips the mockups, since mockups for
  an idea the product lead advises against are spent allowance; the item still reaches the founder,
  who can overrule it. The last step posts one comment built by the script, not written by a model,
  so every item has the same shape: the recommendation, each option with its stars, cost and
  screenshots, and how to answer. The founder answers by replying with a letter and adding
  `decided`; `build` reads that reply and hands it to the builder and the reviewer. The product
  lead and the designer run on Opus, since they plan and judge. Tested on 26 Oct 2026 on a
  throwaway repo: on an idea with no evidence behind it the product lead recommended no-go and
  offered a smaller bet, and the designer was skipped. After the founder overruled it in a comment,
  the designer storyboarded three options at 3, 5 and 7 stars and pushed only their pages and
  screenshots, and the queue item showed all three with costs. The first try found that the
  designer had no `Skill` tool, so it could not find the screenshot script and built a CI renderer
  instead; it now has the tool, and stops when screenshots cannot be taken. A headless run
  (`claude -p`) stops waiting for a workflow after 600 seconds unless
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` is set. A brief that changes nothing on screen, such as
  how the product is built or deploys, skips the designer too: the product lead says whether it
  does, and the item asks only go or no-go and each technical decision. Found on 26 Oct 2026 before
  the website's build-and-deploy brief, which would otherwise have sent the designer to mock up a
  choice with no screens.
- **Each queue item gives every role's recommendation and the team's, each with why in plain
  English.** Decided by the founder on 27 Oct 2026: they decide better with more to go on, and the
  item carried only the product lead's go or no-go and the designer's pick, with no reason for the
  pick. After the designer, every other role (researcher, architect, builder, QA, code reviewer,
  security reviewer and integrator) recommends go or no-go, an option and a choice on each
  technical decision, from what its job knows: the evidence, what is already built, the work, what
  could go wrong for people using it, what it adds to look after, the risk to people's data, and
  the release. That is seven more calls per run, on Sonnet, so the budget is the thing to watch.
  Each sees the brief and the choices but not the
  other roles' picks, so it gives its own view instead of echoing theirs. A team step then weighs
  every view on its reasons, not by counting votes, and names any role that disagrees and why the
  team goes the other way. The item leads with the team's recommendation, then each role's in a
  line, and each technical decision shows the team's choice and each role's under it. The views
  run on Sonnet at medium effort, since they read a brief and give an opinion; the team step runs
  on Opus, since it judges. The roles who give a view are one list in `propose`, and a test checks
  that every agent a workflow names has an agent file, so a change to the roster cannot silently
  drop a voice. A role that returns nothing is left out, and the item still posts.
- **Mockups: one HTML page per option on a `propose/issue-<n>` branch, with screenshots in the
  issue.** Decided by the founder on 25 Oct 2026. A page shows real content at real lengths and can
  be opened at any width; the phone and desktop screenshots, taken with headless Chrome by the
  `mockup-screenshots` skill, let the founder compare options in the issue without opening
  anything. The branch is never merged, so mockups never become product code by accident.
- **Every PR that changes the screen carries before-and-after screenshots.** Decided on 27 Oct
  2026, from Ramp's background agent, Inspect, which puts screenshots in its PRs so a change can
  be judged without opening it. The founder reviews PRs from GitHub's phone app, and the website's
  #5 merged with a layout gap the reviewer missed: the diff read well and the tests passed, but
  nobody looked at the page. The builder serves `main` and its branch, shoots each page the change
  shows on at phone and desktop width with the `mockup-screenshots` skill, which now takes a served
  page's URL and a folder, and commits only the screenshots on a `screenshots/issue-<n>` branch
  started empty, so like the mockups they never land in the product. The description shows them
  the way `propose`'s queue item does; a change with nothing on screen says "No visible change."
  QA shoots the same pages from the branch and sends back a visible change with no screenshots, a
  page left out, or an after screenshot that does not match what it sees, since pictures only the
  builder checks show what the builder hoped. Fix rounds retake them, so the founder sees the
  change that merges. Builder and QA got the `Skill` tool for it, and a test now holds that every
  agent told to use a skill has the tool. Not yet run on a real product.
- **Technical one-way doors reach the founder before they are built in.** Decided by the founder on
  26 Oct 2026, after the website's "no build step or framework" was settled by an aside in a brief
  ("the architect confirms that, not the founder"), with no architect to confirm it, and written
  into a build issue as a rule. A one-way door here is a choice that costs a lot to reverse once
  code or people depend on it: a framework or none, a build step, how the product deploys, its
  stack, how it stores data, a dependency that ships, an outside service, an interface others rely
  on. The product lead names each one a brief settles, even one taken for granted, and `propose`'s
  queue item lists them with options, a recommendation and the cost of reversing, for the founder
  to answer. `build`'s first step, now on Sonnet because it has to judge, refuses an issue that
  settles one not named in its "Technical decisions" section or in a queue item on it; the builder
  stops rather than choose one, and the code reviewer sends back a change that makes one. Agents post
  with the founder's own GitHub login, so a comment's author cannot show who decided: a decision
  counts as seen when it is named where the founder's `decided` label says yes to it. The architect
  lists, in each build issue it cuts, the decisions that issue settles.
- **`plan`: the architect cuts a decided brief into build issues.** Built on 27 Oct 2026, because
  the website's step 3 found nothing between a decided brief and its build issues; they were cut by
  hand, and one hand-cut issue carried "no build step or framework" as a rule nobody had decided. It
  runs as `/founding-agents:plan <brief>`: a Haiku check refuses a brief without `decided` or one
  already cut, then the architect, on Opus, reads the brief, the founder's answers and the product,
  and lists the one-way doors the plan needs. If the founder has answered all of them, it opens the
  build issues in order, each starting "Part of #<brief>", naming the files it owns (no two share
  one), "Build after #<n>" when it depends on another, and the decisions it settles with the
  founder's choice, then posts the plan on the brief. If any is unanswered it opens nothing: one
  script-built queue item lists them, labelled `needs-founder`, and moves the `decided` label off
  the brief so that adding it again is the founder's yes to the new decisions. The founder does not
  label each build issue: `build` accepts an issue cut from a decided brief, and waits until every
  issue it builds after is closed. The founder's attention goes to the decisions, not to approving
  cuts. Not yet run on a real product; schema review of a builder's change, the architect's other
  job, is left until a product has a schema.
- **`plan`'s queue item carries every role's choice and the team's.** Done on 27 Oct 2026, after
  the founder asked for each role's recommendation on every decision put to them. When the
  architect stops with open decisions, every other role with an agent (product lead, researcher,
  designer, builder, QA, code reviewer, security reviewer, integrator) chooses on each, on Sonnet,
  without seeing the others' picks; an Opus step weighs them on their reasons, not by count, and
  names any role that disagrees. The queue item leads with the team's pick, then the architect's
  and each role's, each with its own reason as a sentence. It mirrors `propose`'s queue item
  (#31). The voices cost a run only when the architect has stopped, which on the website was one
  of two runs.
- **Parallel builders: `build` on a brief builds its issues two to four at a time.** Built on 27 Oct
  2026, on top of `plan`. `/founding-agents:build <brief>` sees the issues the architect cut from
  the brief and builds them with two builders at once by default; `build <brief> 3` asks for three,
  and four is the most. Each issue gets the same check, builder and reviewer as a single build,
  starts only once every issue it builds after has merged, and is skipped when one of those did
  not merge. The integrator merges one PR at a time, in the order they are approved, each tested
  on top of the one merged before it (principle 6, Rust's bors); a builder that finishes early
  waits for its turn rather than racing. Parallelism is safe only because the architect gives no
  two issues the same files (principle 5); the builder stops rather than edit a file another
  issue owns. One run report goes on the brief. Two builders is the default because builders and
  reviewers all run on Opus, so four at once spends the week's Opus allowance four times as fast,
  and pacing to the weekly limit is not built yet. Not yet run on a real product.
  Agents running at once share one machine: on 27 Oct 2026 eval trials run side by side
  overwrote each other's `/tmp/index.html.bak`, and one QA reviewed another trial's checkout
  through `/tmp/qa-pr8`. So the builder, QA and the code and security reviewers keep scratch
  files in their worktree or a fresh `mktemp -d` and serve on a free port.
- **Review splits into edge-case QA, code review and security review.** Done on 27 Oct 2026, at
  the founder's request. Each round of `build`, QA and the code reviewer run side by side, each in
  its own worktree and posting its own comment; when the change touches routes, sign-in,
  permissions, stored data, secrets, outside input, model calls or a dependency that ships, the
  security reviewer looks too (when it starts is the next entry). The change is approved only when every reviewer approves, and the builder
  gets all their findings, each marked with who raised it. QA is the only role that reads the
  holdouts, so the holdout guard now trusts `founding-agents:qa`. The split's cost: two Opus
  reviewers each round where there was one, and the reviewer was already the largest cost in five
  of six website builds; the optimiser's numbers say whether it pays.
  A QA must-fix is something it can show going wrong: the product doing the wrong thing for
  someone, or missing what its issue asks. A test the issue did not ask for is a Nit, and how
  tests are written is code review's; found on 27 Oct 2026, when QA sent back a correct page in
  two of three eval trials for a test the issue never asked for.
- **Reviews weigh who can reach a finding, and the integrator merges on checks CI already ran.**
  Decided by the founder on 27 Oct 2026, to speed up `build` after the website's #27 took six
  review rounds and about $36. Most of those rounds chased ever-subtler ways to slip a bad link into
  facts only the founder can write: the public key is read-only and every change to the snapshot
  is reviewed. The reviewers now say who can put a bad value where it hurts: anyone on the
  internet, a user, or only someone the team trusts. A finding only a trusted writer can reach,
  where review would see it, is at most low, so a Nit; it is must-fix when a reader, a user or an
  outside service can reach it, or when it lets a trusted writer harm readers unseen. Ordinary
  slips in kept data (empty, too long, a typo) stay must-fix. The integrator still tests the merge,
  not the branch, but when `main` has not moved since the PR's last push, the PR's green required
  checks already tested exactly what the merge will be, so it merges on them instead of rerunning
  `check.sh`, its install and its browser tests. When `main` has moved, it brings the PR up to
  date with `gh pr update-branch`, which needs no force-push, and waits for the checks again.
- **`build` starts each reviewer as soon as it is known to be needed, and the builder does not wait
  for CI.** Decided on 27 Oct 2026, after the first multi-issue build on the website (brief #14)
  took 23 minutes from check to merge for its smallest issue, #26. Its session logs show where the
  time went: check 0.6 min, builder 7.9, QA 7.6 beside code review 3.6, security review 5.7, then
  the integrator 1.0. The security review started only when QA finished, four minutes after code
  review had flagged the diff, because it waited for both. Installs were not the cost: in every
  worktree `npm ci` took under a second from the shared `~/.npm`, Playwright's browsers are shared
  per user, and the whole `check.sh` ran in 5 to 8 seconds. The model's own work was over 90% of
  each reviewer's time and three quarters of the builder's; the builder's one long tool call was
  watching CI, 94 seconds on #26, which nobody asked it to do. In CI, `npm ci` took 3 to 4 seconds and the browser download 7; what varied was
  `playwright install --with-deps` fetching system fonts and libraries with apt, 13 seconds to 8
  minutes depending on the mirror.
  So the check now also says whether the issue touches routes, sign-in, permissions, stored data,
  secrets, outside input, model calls or a dependency that ships, and when it does the security
  reviewer runs beside QA and code review. The code reviewer's flag stays as the fallback for a
  diff that turns out to touch those when the issue did not say so, and that review now starts the
  moment code review returns rather than when QA does. The builder runs `check.sh`, opens the PR
  and returns; CI runs while the reviewers work, the code reviewer reads its result and sends back
  a failing run as a must-fix finding, and the integrator still merges only on green, so no check
  is skipped and a CI failure still reaches the builder in the same round. On #26 that would have
  been about 16 minutes instead of 23: the review takes as long as its slowest reviewer (7.6
  minutes rather than 13.3), and the builder loses its 1.5-minute wait. CI caches for npm and
  Playwright were left out: they would save under 10 seconds a run, CI now runs while review
  does, and the slow part, apt, is the product's own `check.sh` choice. A product whose CI wait starts to
  matter can run its job in Playwright's container image instead, which is its own decision.
- **The optimiser and the librarian run as weekly routines that propose, never change.** Built on
  27 Oct 2026, the same way as ops watch's daily routine: each one's instructions are a file
  `setup` copies into the product (`.github/optimiser/routine.md`, `.github/librarian/routine.md`)
  and keeps current, since a routine loads no plugin, and both reach GitHub only through `gh api`.
  The optimiser reads the run reports for tokens per merged change, by role and model, this week
  against last, posts the numbers as a comment on one standing issue, and proposes at most three
  savings; it never proposes cutting a check or a review for tokens alone, leaving that trade to
  the founder. The librarian reads the week's incidents (red issues, changes sent back again and
  again, fixes for what a merge broke, runs that stopped for the founder), asks which check would
  have stopped each, and files at most three guards or prunes. Every proposal is a `needs-founder`
  issue, so a guard or a saving is built through `build` like any change, after the founder's
  `decided`. Both run on Sonnet: they judge, but weekly and on a small amount of reading. First
  run on the website on 27 Oct 2026, each in about a minute. The optimiser opened issues through
  `gh api`, which settles that a routine can write: it posted the week's numbers (one merged
  change at $6.19, 16% of the week's cost on a `propose` run waiting for the founder) and proposed
  one saving, a size budget for the page in `check.sh`. The librarian filed nothing, correctly:
  the changes sent back three times and the errors found after merge were already guarded by the
  standard checks and browser tests that came after them. Both found `search/` blocked and listed
  issues instead, which their instructions now say.
- **The optimiser's work splits by what it looks at: team cost weekly, product cost in a sweep.**
  Decided by the founder on 27 Oct 2026, merging `sweep` (which added an optimiser agent as the
  `codebase` finder) onto `main` (which had the optimiser as a weekly routine). Both had looked at
  the product's own cost, and the website got the same page-size proposal twice, #18 from the
  routine and #19 from a sweep. Now the weekly routine measures only what the team costs to run:
  tokens per merged change by role and model, cost spent without a merge, and what every session
  loads, which needs a week's trend. `/founding-agents:sweep codebase`, with `agents/optimiser.md`,
  owns what the product costs: page weight, dead code, one thing defined in several places, found
  in a focused sprint with pass marks. One role, two triggers, and one owner for each kind of
  finding, so nothing reaches the queue twice; a test holds the routine to its half.
- **A finding `build` saw come back unfixed becomes a lesson.** Decided on 27 Oct 2026, when the
  founder asked which of Anthropic's, OpenAI's and Ramp's practices to adopt. `build` already
  stopped when a must-fix came back after the builder's fix, but the stop fixed nothing for the next
  change, and stalls of that kind were 43% of the website's spend. Now the same stop also opens an
  issue titled `Repeated finding on PR #<n>`, labelled `librarian`, naming each finding and the
  PR and asking for a test, a lint rule, a hook or a skill. OpenAI's Codex guidance runs a
  retrospective when an agent makes the same mistake twice, and Anthropic's "Getting started with
  loops" says to encode a fix into the system for every later run (principle 7). The script writes
  the issue, not a model, so each has the same shape; one already open for that PR gets a comment
  instead of a twin. Agents post with the founder's login, so the label, not the author, marks it.
  The librarian reads these issues before the week's other incidents and files each guard as a
  `Lesson:` proposal like any other, so the founder still decides what is built. Every guard's
  failure message says how to fix the problem, not only what failed, since the builder that trips
  it acts on that message alone (OpenAI's harness-engineering post).
- **Run reports say whether `build` ended in a merge, and `run-report --runs` gives the share.**
  Decided the same day. Ramp calls the share of agent sessions that end in a merged PR the most
  important number it tracks. Each `build` report now says `**Outcome:** merged` or
  `**Outcome:** stopped`, and `report.py --runs` reads every report on the repo through REST and
  gives the share of runs that merged without the founder, that merged only after an earlier run on
  the issue stopped, and that stopped. A merged run closes its issue, so a second run on an issue
  means the founder stepped in after the first; that is how "without the founder" is counted, since
  nothing records a founder's edit to an issue between runs. A brief's run counts as merged only
  when every issue cut from it merged. Reports from before outcomes were recorded are left out, and
  the optimiser gives the same shares in its weekly numbers.
- **The researcher prepares and makes sense of conversations; the founder has them.** Built on
  27 Oct 2026, at the founder's request and before any product has users, so it waits for one. It
  is an agent the founder calls on demand, not a workflow step: research has no fixed place in a
  change, and runs when a question comes up. Each question is an issue labelled `research`, holding
  the interview guide, the founder's pasted notes and the synthesis, which keeps what people did
  apart from what is inferred, with names and dates. The product lead reads those issues as the
  strongest evidence a brief can cite. The researcher never contacts anyone, since every message
  sent in the founder's name is the founder's to send.
- **Every shipped brief gets a check-back, in ops watch's daily routine, with a script for the
  rest.** Built on 27 Oct 2026, after the founder asked which practices from Y Combinator and
  Every's compound engineering to adopt. YC's advice is to build what people want and watch the
  number that shows it; Every ends each piece of work by asking what worked. The team did neither:
  every brief said how we'll know it worked, nothing ever looked, and every measure below was about
  the team's process. The founder's first product had no real users after five months and 5,410
  commits. Now, two weeks after a brief's last issue closes as completed (or as long as its "how
  we'll know" says, as "Check back: 3 weeks"), the check-back posts on the brief what it said,
  what actually happened, and a verdict: worked, didn't, or can't tell yet. A "didn't" opens a
  `needs-founder` item asking whether to keep, change or remove what was built, with a
  recommendation; change and remove go through `propose`. It is never red: a feature nobody uses
  is a decision for the founder, not an outage, and must not stop merges. "Can't tell yet" is
  checked again one window later, three times at most, so a product with no data hears so without
  hearing it every fortnight forever. A script (`check_back.py`, which `setup` copies into the
  product beside the routine) finds what is due, posts every check-back in one shape and counts
  the score, because none of that needs judgement; the routine reads the evidence and gives the
  verdict. The evidence is the one metric and other signs of use the product names in its own
  `watch.md`, research issues and the brief's comments; the routine reaches only its own repo, so a
  number kept elsewhere counts once the founder copies it in.
  Where it runs was the founder's choice. The researcher, the product lead and the optimiser
  recommended a new weekly routine following the researcher's instructions: the verdict is a
  reading of evidence about people, which is the researcher's job, and the product lead should not
  grade its own brief (principle 2). Ops watch recommended its own daily run, which already exists,
  so there is nothing new to set up or to pay for. Leaving it with the researcher on demand had no
  backer, since nobody calling it is the gap. The founder chose ops watch on 27 Oct 2026, over the
  team's recommendation: one routine fewer, and a check-back lands the day it is due. The cost is
  the judgement running on Haiku, the weakest model; the routine leans to "can't tell yet" when
  unsure, and the researcher gives a second reading when the founder asks.
- **Decision queue: a `needs-founder` issue label.** GitHub's phone app already notifies, and an
  issue holds the recommendation, the mockups and what each option costs. A nicer page comes later
  only if the label proves clumsy.
- **Sweeps: a third workflow that finds work and hands it to `build`.** Decided by the founder on
  27 Oct 2026, for sprints that optimise the codebase, improve the test suite or look for
  vulnerabilities. `/founding-agents:sweep codebase|tests|security` runs on demand; a weekly
  routine can call it once it has run by hand. Only the start differs from a feature: a finder
  (the optimiser, the test auditor or the security reviewer) reads and runs the product and brings
  at most five findings, ranked, each with its evidence, the fix's size, what leaving it costs,
  its pass marks and any technical decision it settles. A script files each as an issue labelled
  `sweep` and posts one `needs-founder` queue item listing them; the founder adds `decided` to the
  ones worth fixing, `build` builds each, and the rest are closed, since nothing is kept for later.
  The founder still picks because a sweep left to fix all it finds is how the first product ran
  up 731 bug-sweep and audit commits. A sweep of the codebase is the optimiser's weekly routine on
  demand and at more depth, so it leaves out what an open `Optimiser:` proposal covers. A finder only reads, so a sweep never writes over a build;
  its fixes go through `build` one at a time like any change. Each finding's **pass marks** say
  what done means for that kind, since "does it work" is not the question: for the codebase,
  behaviour unchanged and the measured number moved; for tests, the suite still fails on faults
  planted in the code it covers; for security, a test that reproduces the exploit fails before the
  fix and passes after. The builder meets each and QA sends back any it cannot confirm.
  On a public repo a security finding's details go in a draft security advisory, which only the
  repo's admins see, and its issue and the queue item carry only a summary that does not reveal
  it; the fix's PR still shows the change, so publishing the advisory after the merge is the
  founder's call. The finders run on Opus, since they judge. The test auditor is a role the team
  table did not have; its exemplars are the founder's to change. Tested on 27 Oct 2026 with a codebase
  sweep of the website (`claude -p` with this plugin): in 16 minutes and $2.60 the optimiser found
  nothing slow (8 KB gzipped, no script) and instead five checks the repo claims and nothing
  enforces, three of them proved by doctored copies that passed every check, filed as #19 to #23
  with queue item #24. Three things changed from it. The script read the clock for the queue
  item's date, which a workflow may not do, and crashed after filing; a test now keeps every
  workflow off the clock and random numbers. #19 repeated the weekly optimiser's open proposal #18,
  so a sweep now leaves out open `Optimiser:` proposals. And every finding named a technical
  decision, mostly where a helper lives or which list a check reads, which would have had the
  founder reply on five issues before any `decided`; the finder is now told those are the
  builder's. The run's last step could not remove worktrees: headless auto mode refuses
  `git worktree remove --force`, so a build run's worktrees stay until removed by hand.
- **Red lights: ops watch opens a `red` issue, and the integrator merges nothing while one is
  open.** A routine cannot push to a phone itself, but an issue notifies through GitHub, and
  blocking merges is what makes principle 9 hold.
- **Ops watch's site check runs as a nightly GitHub Actions job, not a routine.** Decided by the
  founder on 25 Oct 2026. Checking that the Pages deploy is green and every link resolves needs no
  model, so a script does it: it spends none of the plan's allowance and still runs when the week's
  limit is used up, when a routine would fail without raising red. A failure opens one `red` issue,
  kept current while the check stays red and closed by the next green run; the job itself passes,
  so the issue is the only alarm, and it fails only when the check cannot run. A link that fails is
  tried once more after a pause, so a blip does not raise red. `setup` copies the script into the
  product, because a product's workflow cannot read this private repo; rerunning `setup` updates the
  copy. GitHub stops a public repo's scheduled workflows after 60 days with no activity, and ops
  watch cannot report its own silence; checks that need judgement (spend, release verdicts) stay
  with the Haiku routine. A product served off Pages, as the website is on Vercel since 27 Oct,
  sets the repository variable `OPS_WATCH_URL` to its live address: the check then crawls that
  address and does not ask the Pages API, and a Pages product's check is unchanged. The plugin's
  copy holds this path so that rerunning `setup`, which replaces the product's copy, keeps it.
- **Ops watch's judgement checks run as a daily routine whose instructions live in the product.**
  Built on 27 Oct 2026. The routine checks that every scheduled workflow still runs and passed
  (which covers the site check's silence, including GitHub turning schedules off after 60 days),
  that `main` passes, that changes merged in the last day are live, and the week's run-report
  totals against a budget the product sets, then the checks the product lists in
  `.github/ops-watch/watch.md`, such as backups. A red opens one `red` issue per check and the next
  green run closes it; a check that could not run is reported, never red. Three facts from the
  routine docs shaped it: a cloud session does not install plugins, so the prompt is
  `.github/ops-watch/routine.md`, copied into the product and kept current by `setup`; the cloud's
  GitHub proxy blocks GraphQL, so `gh issue` and `gh pr` fail and every call is `gh api` over
  REST, which a test holds; and a routine can only be created by `/schedule` or the web, so
  `setup` creates it through the `schedule` skill after the founder's yes. Whether Haiku can be
  picked as a routine's model is not documented; `setup` falls back to the cheapest offered.
  First run on the website on 27 Oct 2026, on Haiku, which routines accept: scheduled checks and
  `main` were green, and the live-site check could not run, since the cloud's network refused
  `github.io` with a 403. So the routine no longer fetches the site: it reads what GitHub Pages
  serves (`pages/builds/latest`) and checks each merge is in that commit, reading the served
  files there. The cloud's GitHub proxy also serves only the routine's own repo, so `search/`
  gets a 403 too; a test now holds every routine's calls to `repos/<owner>/<repo>/`. A routine
  created through the API gets every claude.ai connector the founder has unless they are
  cleared, so `setup` creates each with none.
- **The gate: GitHub branch protection with required checks, plus a plugin hook.** The hook reads
  which agent is calling and blocks `git push` to `main` and `gh pr merge` for every agent but the
  integrator. The docs call hook filtering best-effort, so the hard gate sits on GitHub, where
  nothing local can get around it.
- **Every product's checks run in one CI job that branch protection requires.** Decided by the
  founder on 26 Oct 2026. `setup` installs a `ci` workflow whose one job, `check`, runs `check.sh`,
  the product's single command for every check, then makes `check` the required status check. The
  website showed why: its 46 tests ran only when an agent chose to run them, since it had no CI
  and its protection required no checks, so a change that broke them could still have merged.
  `setup` keeps the workflow current but never replaces `check.sh`, which the product owns.
- **Builders use standard tools before writing checks, and test behaviour, not wording.** Decided
  with the CI. The website's tests rebuilt by hand what standard tools do: 53 regular-expression
  searches over the HTML, a home-made tag parser whose bug on `<br/>` cost a review round, a colour
  rule that needed a CSS linter and sent #4 back three times, and layout tests that read the CSS
  text and passed while the rendered page had no gutter. Some pinned today's exact wording, and
  one called GitHub's API. The builder now reaches first for a validator, a linter with rules for
  the product's conventions, a link checker, an accessibility checker and a real browser at phone
  and desktop widths, all run from `check.sh`, and writes custom tests only for the product's own
  rules and facts. The reviewer sends back a hand-written check where a standard tool would do.
  The first eval run (below) found the code reviewer turning a CSS linter down as an undecided
  dependency, since its instructions said "a dependency that ships" where the workflows say ships
  to users; it asked for better regexes instead, which is #4's stall. A check tool run from
  `check.sh` ships to no one, and this decision already says checks use them, so the reviewer's
  and builder's instructions now say adding one is never a one-way door, and the reviewer names
  the tool and the rule.
- **The hook trusts only `founding-agents:integrator`.** Hooks see a plugin agent's name with the
  plugin prefix, both when a session starts with `--agent` and when the agent runs as a subagent; a
  session with no agent reports none. Tested on 25 Oct 2026 with `tests/e2e_guard.sh`: the builder
  and the plain session were blocked, the integrator passed both ways. The builder's own prompt
  forbids pushing to `main`, so the test tells each session the push is a test of the guard;
  without that the builder declines, the hook never runs, and the script now fails. Accepting the
  bare name would let any user or project agent called `integrator` merge, so the guard no longer
  does.
- **Each role learns from a named exemplar** ([exemplars.md](exemplars.md)). A named practice
  ("storyboard the journey", "test the merge, not the branch") gives an agent something concrete to
  do and gives the founder words to correct it with; "be a great designer" does neither. Roles
  borrow practices, not looks, so the designer works like Airbnb without making products look like
  Airbnb. The founder picks the exemplars, since they are taste; Airbnb for the designer was the
  founder's choice.
- **Token cost belongs to the optimiser.** Nobody owned it, and principle 3 only works if someone
  measures it. The optimiser tracks tokens per merged change, by role and model, and what they cost:
  a share of the weekly limit on a Pro or Max plan, dollars on an API key. It proposes cuts as
  builder tasks; ops watch raises red when spend passes the budget.
- **Every run reports its time, tokens and cost on its issue.** Decided by the founder on 26 Oct
  2026. `build` and `propose` end with a Haiku step that runs the `run-report` skill, which reads
  Claude Code's session logs for the run and its agents, counts each model call once, and posts one
  table: each role and model's time, calls, new and cached input, output and cost, then the total.
  Cost is at API list prices, so on a plan it is API-equivalent: it compares runs and roles, while
  the plan itself bills the weekly limit. A run that stalls posts too, because stalls are where the
  cost goes: of the seven website runs, about $37 in all, the two that stalled were 43%. The
  reviewer was the largest cost in five of the six builds. Until the optimiser exists these
  reports are the measure of tokens per merged change. Each workflow passes a budget of $5 a run,
  above the website's typical build and below its stalls, and the report flags a run over it above
  the table. Agents post with the founder's login, so the flag notifies nobody; ops watch's red on
  spend waits for the optimiser.
- **Whether the plugin pays is measured against changes made without it.** Asked for by the founder
  on 27 Oct 2026: the measures below judge the team on its own, and say nothing about whether a
  plain Claude session would have done as well. The `compare-changes` skill reads merged PRs and
  compares the two groups on cost, time to merge and fixes needed within two weeks. A PR from
  `build`'s branch counts as with the plugin; any other change needs a `with-plugin` or
  `without-plugin` label, since nothing else on GitHub tells them apart. Cost is the run reports on
  the PR and the issues it closes, so a plain session counts only once its own report is posted on
  its PR. A fix later is a merged PR within two weeks that changed one of the same files and is
  labelled or titled as a fix: a guess, so the table names each one for the founder to check.
- **Evals test the agents themselves, and a change runs them before its version bump.** Decided by
  the founder on 27 Oct 2026 (#34), after the team's own recommendation. The tests in `tests/`
  run the workflows with scripted replies, so they prove the wiring, not the judgement: a change to
  an agent's instructions or a model choice shipped untested, and the builder moved to Opus, and
  `propose`'s role views to Sonnet, with no data behind either. So a change that alters an agent,
  skill or workflow, or a model choice, runs the eval set before its version bump: a change to one
  agent runs that agent's tasks, and a model change, a workflow change or a release runs all of
  them. The set follows Anthropic's *Demystifying evals for AI agents*: 19 tasks in `evals/`, each
  taken from a real website run and testing one failure class, each graded by a script, with a
  reference answer that passes and a known-bad answer (the website's own mistake where there was
  one) that fails, which `tests/test_evals.py` holds both ways without a model. Seven want a stop,
  a refusal or an approval, so a role that sends everything back scores nothing there. Tasks the
  team got right on the website are regression tasks and should stay near 100%; tasks it got wrong
  are capability tasks, which start low and show whether a change helps. They run on the founder's
  machine with `claude -p` on the plan, three trials each: one trial cannot tell a reliable agent
  from a lucky one, and flakiness is what stalled #4 and #6. Each trial is a throwaway repo with a
  local `origin`, a stand-in `gh` that serves the task's issue and PR and records what the agent
  posts, and an empty GitHub login, so nothing reaches GitHub; each step's prompt is taken from the
  workflow itself, so a prompt edited in `workflows/` is what gets tested. They do not run in CI,
  which would spend allowance on every push of a draft. A session started with `--agent` gets only
  its agent file's tools, so it cannot return `--json-schema`'s structured output: an agent step is
  asked to end its reply with the result as JSON, and Haiku reads it from the reply when that
  fails. First run, 27 Oct 2026: 57 trials in 45 minutes, $26.45 at API prices, against the $35
  estimated; 91% of trials passed and 89% of tasks passed all three. Two failures are the agents':
  on the regex colour test the code reviewer found every hole but never said to use a CSS linter
  (0 of 3), which is #4's stall, and QA sent back a correct page in two of three, asking for a test
  the issue did not. Three were the graders': two pinned the words an agent might use and one read
  markup as words, found by reading the transcripts and fixed before counting, which a test now
  holds. Most capability tasks passed every trial, since the instructions changed after the website
  runs (standard tools, the review split), so they need harder tasks before they say much. The
  builder on Sonnet passed all fifteen of its trials, as Opus did, at $0.22 a trial against $0.78;
  three builder tasks are too few to move it back, so harder builder tasks come before that choice.
  The second run, the same day, tested the fixes those failures led to (below, under standard
  tools, the review split and parallel builders) and four harder builder tasks: the token rule,
  a gutter measured in a real browser, a count of the PR's own review rounds, and links only to
  the repo's public pages. It also found the trials were not independent: agents wrote fixed
  scratch paths such as `/tmp/index.html.bak`, so trials running at once overwrote each other.
  Each trial now has its own `TMPDIR`, trials that share an issue or PR number never run at once,
  and each records any fixed `/tmp` path or port it used. 103 trials, $63.98: the code reviewer
  passed all 21, task 01 included; QA 11 of 12, its one miss a judgement call on the fixture's
  wording; the builder on Opus all 35, and on Sonnet 27 of 35, failing the rendered gutter and
  the token linter four times in five each, at $0.32 a trial against $0.98. The model choice
  went to the founder (#41). A third of trials still used a fixed `/tmp` name, mostly a
  note holding the path of their own `mktemp -d` folder.
- **Models: the strongest model plans and judges; cheaper ones build** (principle 3). Today that is
  Opus 5.5 for the product lead, architect, designer, QA, the code and security reviewers and the
  builders, Sonnet 5.5 for the integrator and Haiku 5.5 for ops watch and the workflows' small
  steps.
- **Builders run on Opus, an exception to principle 3.** The founder's choice on 26 Oct 2026, after
  the first website builds on Sonnet; on #5 the Sonnet builder was sent back once and still shipped
  a step status the issue had said to check against the repo. The cost is the shared limit:
  builder and reviewer now draw on the same Opus allowance, so a heavy day of review can stop
  builds. The optimiser's tokens-per-merged-change, by role and model, is the measure that says
  whether it pays. Confirmed by the founder on 27 Oct 2026 (#41), with the evals behind it this
  time: on seven builder tasks from the website's failures, five trials each, Opus passed all 35
  and Sonnet 27, failing the token linter and the gutter measured in a real browser four times in
  five each, which are the failures that stalled the website, at $0.32 a trial against Opus's
  $0.98. The optimiser's alternative, Sonnet first with Opus on a send-back, was left for later:
  it needs new workflow logic, evaluated before it ships.
- **On a Pro or Max plan the team paces itself to the weekly limit.** A plan meters a rolling 5-hour
  window and a weekly limit, not dollars, and the weekly limit is the one a team runs into.
  Allowance left at the weekly reset is lost; going past it stops runs or bills usage credits at
  API rates. Before `build` takes a ticket it compares how much of the week's limit is used with
  how much of the week has gone: ahead of pace it builds only decided issues; behind pace near the
  reset it also takes work kept for spare allowance. The status line's `rate_limits` field is the
  only reading a program can get, so `setup` adds a status line that saves it where `build` reads
  it. Hooks and routines cannot read it, and it updates only while a session is open.
- **Spare allowance goes to deciding and checking, and to the hours the founder is away.** Work
  kept for spare allowance is more edge-case scenarios, a second review pass, more mockups to pick
  from, and the optimiser's and librarian's tickets; never a feature nobody decided on, since
  that would break principle 1, decide before building. Routines run on the plan with no
  charge for the cloud machine, so ops watch, the optimiser and the librarian run overnight while
  the founder decides during the day. A routine or headless run that hits the limit fails instead
  of pausing, so each run takes one ticket and leaves its issue where the next run picks it up.
- **Nothing falls through to paid billing by accident.** `claude -p` always uses `ANTHROPIC_API_KEY`
  when it is set, so no environment meant to run on the plan sets it. No run uses `--bare`, which
  never reads the plan's login and is due to become the default for `-p`. Fast mode and
  `/code-review ultra` bill only as usage credits, so the pipeline uses neither. Whether usage
  credits are on, and their monthly cap, is the founder's call; with them off, a run that hits the
  limit stops and waits. Every agent and workflow step names its model, because Max otherwise runs
  Opus 5.5. Opus and Sonnet have separate limits; with builders on Opus too, only the integrator
  and the small steps fall on Sonnet's.
- **Each person runs the team on their own login.** Anthropic's terms cover one subscriber's
  ordinary use through the documented paths: `claude -p`, a `claude setup-token` token for CI, and
  routines. The plugin never ships or shares a token; anyone else who uses it signs in with their
  own account or an API key.
- **Generic vs product:** the plugin holds the edge-case checklist, which names failure classes;
  each product supplies its own fixtures and holdouts, and keeps its own rules in its own repo.
- **Holdout scenarios: QA keeps some edge-case scenarios hidden from builders.** For each failure
  class, some scenarios are visible fixtures that builders write their tests from; the rest are
  holdouts that only edge-case QA reads. A builder that writes tests from the cases it can see and
  then makes them pass has shown its code fits those cases, not that it handles the class. Agents
  shape code to the tests in front of them without meaning to, and Claude is a lenient QA agent
  out of the box (principle 2), so a scenario the builder never saw is the one check it cannot
  have fitted. StrongDM keeps its scenarios outside the codebase for the same reason, like a
  held-back test set. A change that passes every visible test and fails a holdout is exactly what
  this exists to catch.
- **How holdouts stay hidden.** They live in a separate private repo that `setup` creates and
  clones outside the product's folder, because a builder's worktree holds everything in the
  product repo. A plugin hook blocks builder agents from reading that path; like the merge guard
  it is best-effort, since a builder's shell can reach any file on the machine. When a holdout
  fails, QA sends back the failure class and what went wrong, not the scenario. A scenario a
  builder has seen moves into the visible fixtures, and a new holdout replaces it.
- **Holdouts in practice.** Built on 27 Oct 2026. The repo is `<product>-holdouts`, cloned to
  `~/.founding-agents/holdouts/<owner>/<name>`, a path every machine can work out from the
  product's name, so nothing in the product points to it. It holds one Markdown file per scenario
  (setup, steps, expected) in a folder per failure class. The hook (`guard_holdouts.py`) blocks
  every agent but `founding-agents:qa` (the reviewer until the split) from any tool call naming that folder or a
  `-holdouts` repo; the founder's own session, which has no agent, passes, because it creates the
  repo and writes the scenarios. The founder writes the first ones there, never through an agent,
  so no builder's context ever held them; QA adds one or two wherever a change touches a
  class that has none. A failing holdout is a must-fix finding naming only its class and what
  went wrong, and `build` asks for nothing more in the findings it hands the builder. Moving a
  seen scenario into the visible fixtures is left to the founder until the librarian exists.
  Tested on 27 Oct 2026 with `tests/e2e_holdouts.sh` and real sessions: the builder started with
  `--agent` and the code reviewer as a subagent were blocked, QA both ways and the founder's own
  session read the scenario, and hooks saw each agent's name with the plugin prefix. Agents with
  their own worktree need a repo with at least one commit. Not yet run on a real product.
- **Borrow, don't depend.** Existing suites (gstack, Compound Engineering, Superpowers, GSD) cover
  parts of this, but they churn (Compound Engineering renamed its commands; GSD's original repo was
  archived) and their auto-triggered skills would compete with these roles. Ideas are copied with
  credit once the licence allows: Superpowers' test-first and worktree skills for builders, the
  lessons in fayerman-source/agent-team, GSD's rule that the orchestrator never writes code, and a
  local merge queue for the integrator. Products that use the team turn the overlapping plugins off.

## Still open

- **Each change's share of the week:** on a plan the budget is a share of the weekly limit, not
  dollars, and Anthropic publishes no numbers for the limits. Set it after measuring the first ten
  changes from their run reports; the optimiser owns it once it exists.
- **Can a routine run `build` overnight, and know how much of the week is left?** Running decided
  issues while the founder is away would use allowance that otherwise expires, but nothing
  documented shows a routine starting a plugin workflow or reading the plan's remaining limit.

## Build order

Each step runs on a real change in a real product before the next one starts.

**The first product is the Founding Agents website** ([todd450/founding-agents-site](https://github.com/todd450/founding-agents-site), named `agent-team-site` until 26 Oct 2026),
decided by the founder on 24 Oct 2026. It is a test bed: a small real product that gives every build
step a real change to run on, not a launch to outside users. A fresh product also shows the team
from its first commit, with no history it has to work around. Whether the team does its job shows
up in the measures below. The plugin repo stays
private, since the founder is the only user for now. A website bends the order in two places:

- **The decide lane comes before `build`** (step 4 before step 3): nothing on a site can be built
  until its words and look are decided. On 25 Oct 2026 the founder chose to build step 3's agents
  and workflow first anyway, tested on a throwaway repo; step 3 is done only once it has run on
  three to five website issues, which come out of the decide lane.
- **Ops watch's first check is the site itself:** a nightly check that the Pages deploy is green
  and every link resolves, since a new site runs no scheduled job of its own yet.

1. **Guardrails.** Branch protection, the plugin hook and a first `setup`. Done when a builder's
   push to `main` is blocked. Done on 24 Oct 2026 on the website: its `main` needs a pull request
   with admins included, and the hook blocked a builder session's push.
2. **Ops watch.** Day one, as the team table says. Its first check is a scheduled job the product
   runs, or for a new product a check of the product itself. Done on 25 Oct 2026 on the website:
   Pages serves the README as a placeholder, the nightly site check is installed through `setup`,
   its first run on GitHub was green, and a red run by hand opened one `red` issue, updated it and
   closed it on green.
3. **`build` with three roles:** one builder (own worktree, tests first from the visible fixtures),
   one reviewer combining QA and code review (read only; runs the visible fixtures and the
   holdouts), and the integrator. Run it on three to five real issues. Done on 26 Oct 2026 on the
   website, without holdouts, which were built on 27 Oct 2026 and have not run there yet: four issues cut by hand from the decided
   brief went through `build` to merge. #4 was sent back three times on a test the issue asked
   for that needed a CSS linter, and merged once the founder narrowed it; #5 merged after one
   send-back, with a stale step status and a layout gap the reviewer missed; #6 was sent back
   three times on Sonnet and merged in one round once the builder moved to Opus; #10, which fixed
   the errors found by reading the live page after #6, merged in one round. Two gaps showed:
   `build` could not continue an open PR unless its issue said so (fixed on 26 Oct 2026, above),
   and nothing cut a decided brief into build issues; the architect's `plan` now does.
4. **The decide lane:** product lead and designer as `propose`, feeding `needs-founder`. This
   completes the starting five. Done on 26 Oct 2026 on the website: on its brief the product lead
   recommended go on a smaller test-bed site and rewrote the brief to match, the designer pushed
   three options at 2, 5 and 7 stars to `propose/issue-1`, and one `needs-founder` queue item
   carried them with their costs.
5. **Grow on demand:** the architect for schema or shared changes (built as `plan` on 27 Oct 2026,
   not yet run on the website); two to four parallel builders once one is routine (built into
   `build` on 27 Oct 2026, not yet run on the website); then the security reviewer, optimiser,
   librarian and researcher as their kind of work appears. QA and code review became two roles,
   with the security reviewer beside them, on 27 Oct 2026, and the optimiser and librarian became
   weekly routines the same day, and the researcher became an agent the founder calls; ops watch
   took on check-backs on shipped briefs the same day. None has run on the website yet. Every role
   in the team table now has an agent or a routine. The same day a test auditor joined the
   optimiser and the security reviewer as the finders `sweep` runs; it is done once a sweep of each
   kind has run on the website and its findings have gone through `build`.

## How we'll know it works

One number for each cost the team is shaped to prevent, one for the founder's attention, and one
for whether people want what the team built, which the other five cannot show:

| cost | measure | should |
|---|---|---|
| Built before deciding | lines deleted within two weeks of being written | fall |
| Found bugs late | bugs found after merge, against bugs found before | mostly be found before |
| Many writers, one branch | merges not made by the integrator | be zero |
| Red lights left red | age of the oldest open `red` issue | be hours, not days |
| The founder's attention | items in the decision queue each day | fit one sitting |
| Built what nobody wanted | shipped briefs that did what "how we'll know" said, among those with a check-back verdict (the check-back prints it) | rise, with few briefs left at "can't tell yet" |
| The founder's attention | share of `build` runs that merge without the founder (`run-report --runs`) | rise |

Whether the team beats a plain Claude session on the same kind of change is the `compare-changes`
skill's table: cost, time to merge and fixes within two weeks, with the plugin and without it.

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
  [the status line](https://code.claude.com/docs/en/statusline),
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
