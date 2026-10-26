---
name: setup
description: Set up a product repo for Founding Agents. Use when adding Founding Agents to a product, when the founder asks to turn on or redo branch protection, or to install or update ops watch's nightly site check. Turns on branch protection for the default branch after the founder confirms, and installs ops watch through a PR.
---

# Set up a product for Founding Agents

This version covers branch protection and ops watch's site check. The other routines, labels and
fixtures arrive with the build steps that use them (`docs/design.md` in the Founding Agents repo,
"Build order").

Run everything from the product repo's folder. The scripts sit in this skill's directory.

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
   (add CI, then rerun with `--apply --replace`).

If GitHub refuses because the repo is private on a free plan, say so and leave the choice to the
founder (a paid plan, or making the repo public). Change neither.

## Ops watch's site check

For a product served by GitHub Pages. A nightly GitHub Actions run checks that the latest Pages
deploy is green and that every link on the site resolves, the site's own pages and the links they
make to other sites. A failure opens one `red` issue, which GitHub notifies the founder of; it is
kept current while the check stays red and closed by the next green run. The run passes either
way, and fails only when the check itself cannot run.

1. **Dry run.** `python3 <this skill's directory>/install_ops_watch.py` shows which files it would
   write (`.github/workflows/ops-watch.yml` and `.github/ops-watch/check_site.py`) and which site it
   would watch. If Pages is off, tell the founder the check would raise red until it is on, and ask
   before turning Pages on, since that is a setting on GitHub.
2. **Apply on a branch.** Make a branch, rerun with `--apply`, commit the two files and open a PR.
   The default branch is protected, so they reach it only through the PR.
3. **After the merge,** run the workflow once by hand (`gh workflow run ops-watch.yml`) and check
   the run is green, so the first result is not a night away.

Rerun the same steps whenever the plugin's copy in `ops_watch/` changes; the dry run says which
files differ. The scheduled run stops if the repo sees no activity for 60 days, which GitHub does to
every scheduled workflow in a public repo; ops watch cannot raise red about its own silence.

## Needs

The plugin's merge guard (`hooks/guard_main.py`) needs `python3` on the machine. It blocks every
agent but the integrator from pushing to `main` or merging; this branch protection is the hard gate
behind it.
