---
name: setup
description: Set up a product repo for Founding Agents. Use when adding Founding Agents to a product, when the founder asks to turn on or redo branch protection, to install or update CI or ops watch's nightly site check, or to set up the holdout scenarios. Installs CI and ops watch through PRs, and turns on branch protection and creates the private holdout repo after the founder confirms.
---

# Set up a product for Founding Agents

This version covers CI, branch protection, ops watch's site check and the holdout scenarios. The
other routines, labels and fixtures arrive with the build steps that use them (`docs/design.md` in the Founding Agents
repo, "Build order").

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

For a product served by GitHub Pages. A nightly GitHub Actions run checks that the latest Pages
deploy is green and that every link on the site resolves, the site's own pages and the links they
make to other sites. A failure opens one `red` issue, which GitHub notifies the founder of; it is
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

## Holdout scenarios

Edge-case scenarios the builders never see, so a change that passes every visible test still has
to handle each failure class. They live in a private `<product>-holdouts` repo, cloned to
`~/.founding-agents/holdouts/<owner>/<name>`, outside every product folder and worktree. Only the
reviewer reads them; the plugin's `guard_holdouts` hook blocks every other agent.

1. **Dry run.** `python3 <this skill's directory>/holdouts.py` says whether the repo and its clone
   exist and what it would do.
2. **Ask for a clear yes.** Creating a repo on GitHub needs the founder's approval each time.
3. **Apply.** Rerun with `--apply`. It creates the repo if missing, clones it (or pulls an existing
   clone), and seeds a README with the scenario format and one folder per failure class.
4. **Tell the founder** the scenarios are theirs to write: a few per class that matter for this
   product, in the format the README gives. The reviewer adds more where a change touches a class
   with none. Write them in the founder's own session, never through an agent, so no builder's
   context ever holds them.

Rerunning it on another machine clones the same repo there.

## Labels

`build` takes only issues labelled `decided`, the founder's yes. Create the queue's labels once,
skipping any that exist:

```
gh label create needs-founder --color FBCA04 --description "Waiting on the founder's decision"
gh label create decided --color 0E8A16 --description "The founder said yes; ready to build"
```

Ops watch creates `red` itself the first time a check fails.

## Needs

The plugin's hooks need `python3` on the machine. The merge guard (`hooks/guard_main.py`) blocks
every agent but the integrator from pushing to `main` or merging; branch protection is the hard
gate behind it. The holdout guard (`hooks/guard_holdouts.py`) blocks every agent but the reviewer
from the holdout scenarios.
