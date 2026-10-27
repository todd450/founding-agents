---
name: tidy-worktrees
description: Remove the git worktrees Founding Agents' workflow builders, reviewers and designers left under .claude/worktrees/, once everything in them is on GitHub. Use at the end of a build or propose run, or when the founder asks to clean up worktrees.
---

# Tidy worktrees

Each builder, reviewer and designer works in its own worktree under `.claude/worktrees/`, and a
worktree that holds commits stays after the agent finishes. Run from the product repo's folder:

- `python3 <this skill's directory>/tidy.py` prints each agent worktree and whether it would go.
- Add `--apply` to remove them.

A worktree goes only when it has no uncommitted change (Python's and Node's caches aside) and its
commit is on a branch at origin, so nothing is lost: the work is on the remote branch and its PR.
Its local branch goes with it. Only worktrees a workflow made, named `wf_...`, are touched; a Claude
Code session's own worktree in the same folder may be in use and is left alone. Report what the
script printed; never remove a kept worktree by hand, since it holds work that is not on GitHub.

Runs go one at a time today. Once builders run in parallel, a clean, pushed worktree of a run still
going could be removed under it, so this then needs to run only when no other run is going.
