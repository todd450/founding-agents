#!/usr/bin/env python3
"""Remove the worktrees workflow agents left under .claude/worktrees/ once their work is on GitHub.
Prints the plan by default; removes nothing without --apply.

A worktree goes only when it has no uncommitted change (Python's and Node's caches aside) and its
commit is on a branch at origin, so removing it loses nothing: the work is on the remote branch and
its PR. Its local branch goes with it. Anything else is kept and named, for a person to look at.

Only a workflow agent's worktree, named `wf_...`, is touched. A Claude Code session's own worktree
sits in the same folder under another name, and may be in use.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Untracked files a run leaves behind that hold no work.
LITTER = ("__pycache__/", ".pytest_cache/", "node_modules/", "test-results/", "playwright-report/")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def worktrees(root):
    """(path, branch or None) for each worktree a workflow agent made under .claude/worktrees/."""
    found, path, branch = [], None, None
    for line in git("worktree", "list", "--porcelain", cwd=root).stdout.splitlines() + [""]:
        if line.startswith("worktree "):
            path, branch = Path(line[len("worktree "):]), None
        elif line.startswith("branch refs/heads/"):
            branch = line[len("branch refs/heads/"):]
        elif not line and path:
            if path.parent == root / ".claude" / "worktrees" and path.name.startswith("wf_"):
                found.append((path, branch))
            path = None
    return found


def why_kept(path):
    """Why this worktree must stay, or "" when everything in it is on GitHub."""
    changes = [line for line in git("status", "--porcelain", "--untracked-files=all", cwd=path).stdout.splitlines()
               if not (line.startswith("?? ") and any(f"/{litter}" in f"/{line[3:]}" for litter in LITTER))]
    if changes:
        return f"{len(changes)} uncommitted change(s)"
    if not git("branch", "-r", "--contains", "HEAD", cwd=path).stdout.strip():
        return "its commit is on no branch at origin"
    return ""


def plan(root):
    return [(path, branch, why_kept(path)) for path, branch in worktrees(root)]


def tidy(root, steps):
    for path, branch, kept in steps:
        if kept:
            continue
        git("worktree", "remove", "--force", str(path), cwd=root)
        if branch:
            git("branch", "-D", branch, cwd=root)
    git("worktree", "prune", cwd=root)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="remove them instead of printing the plan")
    args = parser.parse_args(argv)

    top = git("rev-parse", "--show-toplevel", cwd=Path.cwd())
    if top.returncode != 0:
        print("Run this from the product repo's folder.", file=sys.stderr)
        return 1
    root = Path(top.stdout.strip())
    git("fetch", "--quiet", "--prune", "origin", cwd=root)

    steps = plan(root)
    if not steps:
        print("No agent worktrees to tidy.")
        return 0
    for path, branch, kept in steps:
        print(f"- {path.name} ({branch or 'detached'}): {'kept, ' + kept if kept else 'remove'}")
    if not args.apply:
        print("\nDry run: nothing removed. Rerun with --apply to remove them.")
        return 0
    tidy(root, steps)
    print(f"\nRemoved {sum(1 for *_, kept in steps if not kept)}; kept {sum(1 for *_, kept in steps if kept)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
