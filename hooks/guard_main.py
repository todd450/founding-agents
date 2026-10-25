#!/usr/bin/env python3
"""PreToolUse hook: only the integrator pushes to main or merges a PR.

Reads the hook event on stdin. When a Bash command would push to a protected branch or merge a PR
and the calling agent is not the integrator, it exits 2 with the reason on stderr, which blocks
the call and tells the agent why. This is best-effort parsing of shell commands; GitHub branch
protection is the hard gate (docs/design.md, "The gate").
"""

import json
import os
import re
import shlex
import subprocess
import sys

# Hooks see a plugin agent's name with the plugin prefix (tests/e2e_guard.sh, docs/design.md "The
# gate"), so another agent that is merely called `integrator` does not pass.
INTEGRATOR = "agent-team:integrator"
PROTECTED = {"main", "master"}

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


def violations(command, cwd):
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
            yield "gh pr merge"
        elif words[0] == "gh" and words[1:2] == ["api"] and MERGE_API.search(segment):
            yield "a merge through gh api"


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if event.get("tool_name") != "Bash" or event.get("agent_type") == INTEGRATOR:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if "push" not in command and "merge" not in command:
        return 0

    found = next(violations(command, event.get("cwd") or os.getcwd()), None)
    if not found:
        return 0
    agent = event.get("agent_type")
    caller = f"the {agent} agent" if agent else "a session that is not the integrator"
    print(
        f"Blocked {found} by {caller}. Only the agent-team integrator pushes to main or merges. "
        "Push your own branch and open a PR instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
