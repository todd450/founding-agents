---
name: setup
description: Set up a product repo for Founding Agents. Use when adding Founding Agents to a product, when the founder asks to turn on or redo branch protection, to install or update CI or ops watch's nightly site check, to set up ops watch's daily routine, the optimiser's or librarian's weekly routine, the check-backs on shipped briefs, or the holdout scenarios, or to add the product's CLAUDE.md, fixtures folder or labels. Installs CI and ops watch through PRs, and turns on branch protection and creates the private holdout repo after the founder confirms.
---

# Set up a product for Founding Agents

This version covers CI, branch protection, ops watch's site check and daily routine, the
optimiser's and the librarian's weekly routines, the check-backs on shipped briefs, the holdout
scenarios, the product's `CLAUDE.md`
and fixtures, and the labels (`docs/design.md` in the Founding Agents repo, "Build order").

Run everything from the product repo's folder. The scripts sit in this skill's directory.

## CI

Every product gets one CI job, `check`, that runs `./check.sh` on each pull request and on the
default branch. `check.sh` is the product's one command for every check: its tests, and the
standard validators, linters, link and accessibility checkers and browser tests the builder adds.
Branch protection then requires `check`, so nothing merges unless it passes.

1. **Dry run.** `python3 <this skill's directory>/install_kit.py ci` shows the files:
   `.github/workflows/ci.yml`, which setup keeps current, and a starter `check.sh` that runs the
   Python tests in `tests/`. A product that already has `check.sh` keeps its own.
2. **Apply on a branch.** Make a branch, rerun with `--apply`, commit, open a PR, and check the
   `check` job passes on it. A failure there is a real failure the product had all along: fix it in
   its own PR first.
3. **After the merge,** require the check: branch protection below, with `--check check`.

## Branch protection

1. **Dry run.** `python3 <this skill's directory>/protect_branch.py`. It reads the repo, its default
   branch, any protection already in place and the CI check names on the latest commit, and prints
   the plan. It changes nothing.
2. **Tell the founder the plan in plain words**, from the script's output: which branch, that every
   change then needs a pull request, which checks become required (or that there is no CI yet), and
   that admins are included, so even the founder's own sessions stop pushing straight to the
   branch. If protection already exists, show what is there and what would replace it.
3. **Ask for a clear yes.** This changes the repo's settings on GitHub, so it needs the founder's
   explicit approval every time; an earlier yes for another repo does not count.
4. **Apply.** Rerun with `--apply`. Add `--replace` only when protection already exists and the
   founder agreed to replace it after seeing it.
5. **Report** what is now on, and what is still missing: required checks if the repo has no CI yet
   (add CI above, then rerun with `--apply --replace --check check`).

Always name the required check with `--check check` once CI is in. Without it the script requires
every check on the latest commit, and a scheduled job such as ops watch's `site` would then block
every pull request, since it never runs on one.

If GitHub refuses because the repo is private on a free plan, say so and leave the choice to the
founder (a paid plan, or making the repo public). Change neither.

## Ops watch's site check

A nightly GitHub Actions run checks that the deploy is up and that every link on the site resolves,
the site's own pages and the links they make to other sites. For a product on GitHub Pages it asks
the Pages API whether the latest deploy is green. A product served elsewhere sets the repository
variable `OPS_WATCH_URL` to its live address (`gh variable set OPS_WATCH_URL --body <address>`),
and the check then crawls that address instead of asking Pages. A failure opens one `red` issue, which GitHub notifies the founder of; it is
kept current while the check stays red and closed by the next green run. The run passes either
way, and fails only when the check itself cannot run.

1. **Dry run.** `python3 <this skill's directory>/install_kit.py ops-watch` shows which files it
   would write (`.github/workflows/ops-watch.yml` and `.github/ops-watch/check_site.py`) and which
   site it would watch. If Pages is off, tell the founder the check would raise red until it is on,
   and ask before turning Pages on, since that is a setting on GitHub.
2. **Apply on a branch.** Make a branch, rerun with `--apply`, commit the two files and open a PR.
   The default branch is protected, so they reach it only through the PR.
3. **After the merge,** run the workflow once by hand (`gh workflow run ops-watch.yml`) and check
   the run is green, so the first result is not a night away.

Rerun the same steps whenever the plugin's copy in `ops_watch/` changes; the dry run says which
files differ. The scheduled run stops if the repo sees no activity for 60 days, which GitHub does to
every scheduled workflow in a public repo; ops watch cannot raise red about its own silence.

## Ops watch's daily routine

The checks that need judgement run as a daily routine in the cloud, on the founder's plan: that
every scheduled check still runs (ops watch's site check cannot report its own silence), that
`main` passes, that changes merged in the last day are live, and the week's spend against a
budget, then the product's own checks such as backups. A red opens one `red` issue per check and
the next green run closes it. Routines do not load plugins, so the instructions live in the
product: `.github/ops-watch/routine.md`, which setup keeps current, and the product's own
`.github/ops-watch/watch.md`.

The same run checks back on shipped briefs. Two weeks after a brief's last issue closes (or as
long as the brief says), it posts on the brief what "how we'll know" said, what actually happened
and a verdict: worked, didn't, or can't tell yet. A "didn't" opens a `needs-founder` item asking
whether to keep, change or remove what was built; it is never red, since it must not stop merges.
`.github/ops-watch/check_back.py`, which setup keeps current, finds what is due, posts every
check-back in the same shape and counts the share of shipped briefs that worked; the routine
only reads the evidence and judges.

1. **Dry run.** `python3 <this skill's directory>/install_kit.py ops-routine` shows the three
   files.
2. **Fill in `watch.md` with the founder:** the product's address, a weekly budget if they want
   one, and a check for each thing the product has that can quietly fail (backups, production
   errors, a release). Then the one metric and any other evidence of use, and where in the repo to
   read them: the routine reaches only this repo, so a number kept elsewhere counts once the
   founder copies it in. With none yet, every check-back says "can't tell yet", which is the honest
   answer. Leave out what the product does not have.
3. **Apply on a branch.** Rerun with `--apply`, commit, open a PR, and wait for the merge.
4. **Ask for a clear yes** to create the routine, since it runs every day on the founder's plan.
5. **Create it** with the `schedule` skill: a daily task on this repo, at an odd minute such as
   7:23, on Haiku (or the cheapest model the model selector offers; say which), with the prompt
   "Follow .github/ops-watch/routine.md in this repo." Use the cloud environment, the tools
   `Bash`, `Read`, `Glob` and `Grep` only, and no connectors: a routine created through the API
   gets every claude.ai connector the founder has (mail, drive and the rest) unless they are
   cleared, and ops watch needs none of them. It needs the founder's GitHub connection for the
   repo, from the Claude GitHub App or `/web-setup`.
6. **Run it once now** and read its last lines: one per check, green, red or not run, then any
   check-backs and the score. A check that could not run is a setup problem to fix, not a red.

Rerun step 1 whenever the plugin's copy changes; the routine reads the file, so it needs no
change itself.

## The optimiser's and the librarian's weekly routines

Two more routines, each once a week. The optimiser measures tokens per merged change from the run
reports, by role and model, and what the product costs to run, posts the numbers on one issue and
proposes at most three savings. The librarian turns the week's incidents (red issues, changes sent
back again and again, fixes for what a merge broke) into guards, and proposes removing guards and
rules that guard nothing. Each files what it wants built as a `needs-founder` issue; the founder
adds `decided` to the ones to build. Neither changes the product itself.

1. **Dry run.** `python3 <this skill's directory>/install_kit.py optimiser`, then `librarian`.
2. **Apply on a branch.** Rerun each with `--apply`, commit both, open one PR, and wait for the
   merge.
3. **Ask for a clear yes** to create the two routines, since each runs every week on the founder's
   plan.
4. **Create them** with the `schedule` skill: weekly tasks on this repo, early on a Monday at odd
   minutes a few hours apart, on Sonnet, with the prompts "Follow .github/optimiser/routine.md in
   this repo." and "Follow .github/librarian/routine.md in this repo." Use the cloud environment,
   the tools `Bash`, `Read`, `Glob` and `Grep` only, and no connectors, as for ops watch.
5. **Run each once now** and read its last lines. A measure it could not take is a setup problem
   to fix.

## Holdout scenarios

Edge-case scenarios the builders never see, so a change that passes every visible test still has
to handle each failure class. They live in a private `<product>-holdouts` repo, cloned to
`~/.founding-agents/holdouts/<owner>/<name>`, outside every product folder and worktree. Only
edge-case QA reads them; the plugin's `guard_holdouts` hook blocks every other agent.

1. **Dry run.** `python3 <this skill's directory>/holdouts.py` says whether the repo and its clone
   exist and what it would do.
2. **Ask for a clear yes.** Creating a repo on GitHub needs the founder's approval each time.
3. **Apply.** Rerun with `--apply`. It creates the repo if missing, clones it (or pulls an existing
   clone), and seeds a README with the scenario format and one folder per failure class.
4. **Tell the founder** the scenarios are theirs to write: a few per class that matter for this
   product, in the format the README gives. QA adds more where a change touches a class
   with none. Write them in the founder's own session, never through an agent, so no builder's
   context ever holds them.

Rerunning it on another machine clones the same repo there.

## The map and the fixtures

Every product gets a short `CLAUDE.md`, the map every session loads, and a `fixtures/` folder for
the visible edge-case scenarios builders write their tests from.

1. **Dry run.** `python3 <this skill's directory>/install_kit.py basics` shows the two starter
   files. A product that already has either keeps its own; for an existing `CLAUDE.md`, suggest to
   the founder what the starter adds, rather than changing it.
2. **Fill in the starter `CLAUDE.md` with the founder:** one paragraph on what the product is and
   who it is for, and the product's own rules with the check that holds each. Keep it short; a
   rule worth keeping becomes a check, not a paragraph. Two facts every product states:
   - **Whether merging to `main` deploys to production.** Check rather than assume:
     `gh api repos/<owner>/<repo>/deployments --jq '[.[].environment] | unique'` lists
     `Production`, `production` or `github-pages` when it does. Where it does, the founder merges
     every PR, since the merge is the release; tell the founder so, and that a product which
     deploys from a step the founder starts (a promoted release, a staging branch) lets the
     integrator merge again.
   - **The local preview command,** bound to this machine (`python3 -m http.server 0 --bind
     127.0.0.1`, with `--directory` for the web root). Then list the folder it serves, dotfiles
     included (`ls -a`), and look for secrets: `.env*`, `.vercel/`, a key. If one is there, tell the
     founder before anything else and recommend moving it out of the web root; a static server
     hands any file in its folder to whoever asks. The plugin's `guard_serve` hook refuses an
     unbound server or one whose folder holds a secret.
3. **Apply on a branch.** Rerun with `--apply`, commit, and open a PR.

## Labels

`build` takes only issues labelled `decided`, the founder's yes; `needs-founder` is the decision
queue; an open `red` issue stops merges; `research` holds what users said and did; `librarian`
holds a finding `build` saw come back unfixed, for the librarian to turn into a check. Create them once, skipping any that exist:

```
gh label create needs-founder --color FBCA04 --description "Waiting on the founder's decision"
gh label create decided --color 0E8A16 --description "The founder said yes; ready to build"
gh label create red --color B60205 --description "A scheduled check failed; nothing merges until it is fixed"
gh label create research --color 5319E7 --description "A question about users, with the researcher's guide and synthesis"
gh label create librarian --color 1D76DB --description "A mistake a run made twice, for the librarian to turn into a check"
```

## Needs

The plugin's hooks need `python3` on the machine. The merge guard (`hooks/guard_main.py`) blocks
every agent but the integrator from pushing to `main` or merging; branch protection is the hard
gate behind it. The holdout guard (`hooks/guard_holdouts.py`) blocks every agent but QA
from the holdout scenarios. The serve guard (`hooks/guard_serve.py`) blocks a local
`python3 -m http.server` that is not bound to `127.0.0.1`, or whose folder holds a secret.
