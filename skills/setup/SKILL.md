---
name: setup
description: Set up a product repo for Founding Agents. Use when adding Founding Agents to a product, or when the founder asks to turn on or redo branch protection. Turns on branch protection for the default branch after the founder confirms.
---

# Set up a product for Founding Agents

This first version covers branch protection only. Routines, labels and fixtures arrive with the
build steps that use them (`docs/design.md` in the Founding Agents repo, "Build order").

Run everything from the product repo's folder. `protect_branch.py` sits in this skill's directory.

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

The plugin's merge guard (`hooks/guard_main.py`) needs `python3` on the machine. It blocks every
agent but the integrator from pushing to `main` or merging; this branch protection is the hard gate
behind it.
