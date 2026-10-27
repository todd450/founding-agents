# Design

A team of agents that builds products with one founder. This doc is the spec until the agent files
exist; after that it records the decisions behind them.

## Where it comes from

The founder's first product was built from June to October 2026 with many parallel Claude
sessions: 5,410 commits in under five months, with no real users yet. Its history showed four
costs, each of which this team is shaped to prevent:

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
| | **Builders** (2–4) | in parallel, one worktree each | the change, with tests written first from the visible edge-case fixtures | their own worktree; never the holdouts |
| | **Edge-case QA** | every change, before merge | the failure checklist: empty and one-item, other data and account shapes, other language, phone width, failed read, second user, time zones; run against the visible fixtures and the holdout scenarios builders never see | read and run; the only role that reads the holdouts |
| Check | **Code reviewer** | every change | correctness and simplification; sees the diff, not the builder's reasoning | read only |
| | **Security reviewer** | changes to routes, permissions, storage or model calls | findings | read only |
| | **Optimiser** | weekly | page cost, token cost per merged change, dead code, one thing defined in several places | proposes builder tasks |
| Ship & run | **Integrator** | the only merger | rebase, run checks, gate production, cut releases | `main` and production |
| | **Ops watch** | scheduled | backups, release verdicts, production errors, spend; red reaches the founder | read plus notifications |
| | **Librarian** | after each incident; a weekly prune | a lesson as a test or lint rule; keeps the rules file capped; deletes guards for removed things | tests, lint config, docs |

**Start with five:** product lead, designer, builders, a reviewer combining QA and code review, and
the integrator. Add the others when their kind of work appears — except ops watch, which belongs on
day one.

Each role borrows the practices of a team or person known for that job, such as Airbnb for the
designer and Google SRE for ops watch: [exemplars.md](exemplars.md).

## How a change flows

1. Idea → **product lead** writes the brief → founder decides.
2. **Designer** mocks it up → founder picks.
3. **Architect** writes the plan and cuts it into build issues → **builders** build, each in its own
   worktree.
4. **Edge-case QA** and **code review** run in parallel.
5. **Integrator** merges and gates production → **ops watch** watches it run.

The founder sees steps 1 and 2, and step 3 only when the plan needs a technical decision the brief
left open. Every hand-off is a file, a ticket or a PR, so the next agent
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
10. **Protect the founder's attention.** One decision queue, read once a day; each item carries a
    recommendation, a picture, and what each option costs.

Day-one engineering defaults the architect sets for a new product: one front end (no second
document surface), writes that change only the field that changed, string keys from the first
screen, one design-token source that generates every copy.

## How it maps to Claude Code

- **Roles** → agent files in the plugin's `agents/`, each with its model, effort and tools;
  builders also get their own worktree.
- **Procedures** → skills (edge-case checklist, design review from screenshots, release, `setup`,
  `run-report`).
- **The per-change pipeline** → three saved workflows in the plugin: `propose`, `plan` and `build`.
- **Scheduled roles** (optimiser, librarian) → routines, which `setup` creates in each product
  because a plugin cannot ship them. Ops watch's checks that need no judgement run as GitHub
  Actions schedules instead, which `setup` installs in the product.
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
  instead of starting again; #4 and #6 needed their issues edited by hand to do that. The reviewer
  marks each must-fix that an earlier review raised and is still unfixed as a repeat, and one
  repeat after a builder's fix ends the run for the founder, before a third round: the stalls on #4
  and #6 were the same findings coming back, at 43% of the website's spend. New findings still get
  the three rounds. Every run after its first step then runs the `tidy-worktrees` skill, which
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
- **Mockups: one HTML page per option on a `propose/issue-<n>` branch, with screenshots in the
  issue.** Decided by the founder on 25 Oct 2026. A page shows real content at real lengths and can
  be opened at any width; the phone and desktop screenshots, taken with headless Chrome by the
  `mockup-screenshots` skill, let the founder compare options in the issue without opening
  anything. The branch is never merged, so mockups never become product code by accident.
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
- **Review splits into edge-case QA, code review and security review.** Done on 27 Oct 2026, at
  the founder's request. Each round of `build`, QA and the code reviewer run side by side, each in
  its own worktree and posting its own comment; when the code reviewer says the diff touches
  routes, sign-in, permissions, stored data, secrets, outside input or model calls, the security
  reviewer looks too. The change is approved only when every reviewer approves, and the builder
  gets all their findings, each marked with who raised it. QA is the only role that reads the
  holdouts, so the holdout guard now trusts `founding-agents:qa`. The split's cost: two Opus
  reviewers each round where there was one, and the reviewer was already the largest cost in five
  of six website builds; the optimiser's numbers say whether it pays.
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
- **The researcher prepares and makes sense of conversations; the founder has them.** Built on
  27 Oct 2026, at the founder's request and before any product has users, so it waits for one. It
  is an agent the founder calls on demand, not a workflow step: research has no fixed place in a
  change, and runs when a question comes up. Each question is an issue labelled `research`, holding
  the interview guide, the founder's pasted notes and the synthesis, which keeps what people did
  apart from what is inferred, with names and dates. The product lead reads those issues as the
  strongest evidence a brief can cite. The researcher never contacts anyone, since every message
  sent in the founder's name is the founder's to send.
- **Decision queue: a `needs-founder` issue label.** GitHub's phone app already notifies, and an
  issue holds the recommendation, the mockups and what each option costs. A nicer page comes later
  only if the label proves clumsy.
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
  with the Haiku routine.
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
- **Models: the strongest model plans and judges; cheaper ones build** (principle 3). Today that is
  Opus 5.5 for the product lead, architect, designer, QA, the code and security reviewers and the
  builders, Sonnet 5.5 for the integrator and Haiku 5.5 for ops watch and the workflows' small
  steps.
- **Builders run on Opus, an exception to principle 3.** The founder's choice on 26 Oct 2026, after
  the first website builds on Sonnet; on #5 the Sonnet builder was sent back once and still shipped
  a step status the issue had said to check against the repo. The cost is the shared limit:
  builder and reviewer now draw on the same Opus allowance, so a heavy day of review can stop
  builds. The optimiser's tokens-per-merged-change, by role and model, is the measure that says
  whether it pays.
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
  building before deciding was the costliest of the four costs. Routines run on the plan with no
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
from its first commit, with no history it has to work around. The four costs stay the evidence the
team is shaped by; whether it prevents them shows up in the measures below. The plugin repo stays
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
   weekly routines the same day, and the researcher became an agent the founder calls; none has run
   on the website yet. Every role in the team table now has an agent or a routine.

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
- Holdout scenarios — [StrongDM Software Factory](https://rywalker.com/research/strongdm-factory)
  (a third-party write-up, Sep 2026)
