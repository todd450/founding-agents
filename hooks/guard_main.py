#!/usr/bin/env python3
"""PreToolUse hook: no session or agent pushes to main or merges a PR itself; GitHub merges.

Reads the hook event on stdin. When a Bash command would push to a protected branch or merge a PR,
it exits 2 with the reason on stderr, which blocks the call and tells the agent why. One merge
passes: `gh pr merge --auto`, which asks GitHub to merge once the PR's required checks pass, from
a session or a workflow's own step. The team's roles (the builder, the reviewers and the rest) are
never let through, so whoever writes or reviews a change does not ship it. This is best-effort
parsing of shell commands; GitHub branch protection is the hard gate (docs/design.md, "The gate").
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTECTED = {"main", "master"}
ROLES = {path.stem for path in (Path(__file__).resolve().parent.parent / "agents").glob("*.md")}

SEGMENT_BREAKS = re.compile(r"&&|\|\||[;|\n]")
MERGE_API = re.compile(r"pulls/\d+/merge\b|/merges\b")
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
PUSH_OPTIONS_WITH_VALUE = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}


def git(cwd, *args):
    result = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def protected_branches(cwd):
    default = git(cwd, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    return PROTECTED | ({default.split("/", 1)[1]} if "/" in default else set())


def push_target(spec, cwd):
    """The branch a refspec writes to: `main`, `+main`, `HEAD:main`, `:main`, `refs/heads/main`."""
    target = spec.lstrip("+").split(":")[-1]
    if target == "HEAD":
        target = git(cwd, "branch", "--show-current")
    return target.removeprefix("refs/heads/")


def default_push_target(cwd):
    """Where a bare `git push` goes: the current branch's push destination, else the branch."""
    upstream = git(cwd, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{push}")
    return upstream.split("/", 1)[1] if "/" in upstream else git(cwd, "branch", "--show-current")


def pushed_protected_branch(args, cwd):
    """For `git ...` arguments, the protected branch a push would write to, or None."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            cwd = os.path.join(cwd, os.path.expanduser(args[i + 1]))
        i += 2 if args[i] in GIT_OPTIONS_WITH_VALUE else 1
    if args[i:i + 1] != ["push"]:
        return None

    positional, rest, j = [], args[i + 1:], 0
    while j < len(rest):
        arg = rest[j]
        if arg in ("--all", "--mirror", "--branches"):
            return "every branch"
        if arg == "--":
            positional += rest[j + 1:]
            break
        if arg in PUSH_OPTIONS_WITH_VALUE:
            j += 1
        elif not arg.startswith("-"):
            positional.append(arg)
        j += 1

    protected = protected_branches(cwd)
    refspecs = positional[1:]
    targets = [push_target(spec, cwd) for spec in refspecs] or [default_push_target(cwd)]
    return next((target for target in targets if target in protected), None)


def asks_github_to_merge(words):
    """True for `gh pr merge --auto`: GitHub merges once the required checks pass. `--admin` merges
    around them, so it never counts."""
    return "--auto" in words and "--admin" not in words


def violations(command, cwd, role=False):
    for segment in SEGMENT_BREAKS.split(command):
        try:
            words = shlex.split(segment, comments=True)
        except ValueError:
            words = segment.split()
        while words and re.match(r"^\w+=", words[0]):
            words = words[1:]
        if not words:
            continue
        if words[0] == "cd" and len(words) > 1:
            cwd = os.path.join(cwd, os.path.expanduser(words[1]))
        elif words[0] == "git":
            branch = pushed_protected_branch(words[1:], cwd)
            if branch:
                yield f"git push to {branch}"
        elif words[0] == "gh" and words[1:3] == ["pr", "merge"]:
            if role or not asks_github_to_merge(words[3:]):
                yield "gh pr merge"
        elif words[0] == "gh" and words[1:2] == ["api"] and MERGE_API.search(segment):
            yield "a merge through gh api"


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if "push" not in command and "merge" not in command:
        return 0

    agent = event.get("agent_type")
    role = str(agent or "").split(":")[-1] in ROLES
    found = next(violations(command, event.get("cwd") or os.getcwd(), role), None)
    if not found:
        return 0
    caller = f"the {agent} agent" if agent else "this session"
    way = ("The founder merges, or `build` asks GitHub to once the reviewers approve." if role else
           "Ask GitHub to merge once the required checks pass, with `gh pr merge <number> --auto --squash`, "
           "or leave the PR for the founder.")
    print(
        f"Blocked {found} by {caller}. No session or agent pushes to main, merges a PR itself, or "
        f"merges around its checks. {way}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
