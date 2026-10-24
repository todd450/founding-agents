#!/usr/bin/env python3
"""Turn on branch protection for a repo's default branch, so nothing reaches it without a PR and
passing checks. Prints the plan by default; changes nothing without --apply.

Admins are included on purpose: agents act with the founder's token, which is an admin's, so a
rule that admins can bypass would not stop them.
"""

import argparse
import json
import subprocess
import sys


def gh(*args, payload=None):
    result = subprocess.run(
        ["gh", *args],
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def build_protection(checks):
    return {
        "required_status_checks": (
            {"strict": True, "checks": [{"context": name} for name in checks]} if checks else None
        ),
        "enforce_admins": True,
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }


def describe(repo, branch, checks):
    lines = [
        f"Branch protection for {repo} on {branch}:",
        "- every change arrives through a pull request (no approvals needed: one founder)",
        f"- required checks, run on an up-to-date branch: {', '.join(checks)}"
        if checks
        else "- no required checks: the repo has no CI yet, so only the pull request is required",
        "- admins included, so no session, agent or person pushes straight to the branch",
        "- no force-pushes and no deleting the branch",
    ]
    return "\n".join(lines)


def check_names(repo, branch):
    names = set()
    code, out, _ = gh("api", f"repos/{repo}/commits/{branch}/check-runs", "--jq", ".check_runs[].name")
    if code == 0:
        names.update(filter(None, out.splitlines()))
    code, out, _ = gh("api", f"repos/{repo}/commits/{branch}/status", "--jq", ".statuses[].context")
    if code == 0:
        names.update(filter(None, out.splitlines()))
    return sorted(names)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="owner/name; defaults to the repo in the current folder")
    parser.add_argument("--check", action="append", help="a required check name; repeat for more")
    parser.add_argument("--apply", action="store_true", help="make the change instead of printing it")
    parser.add_argument("--replace", action="store_true", help="replace protection already in place")
    args = parser.parse_args(argv)

    view = ["repo", "view", "--json", "nameWithOwner,defaultBranchRef"] + ([args.repo] if args.repo else [])
    code, out, err = gh(*view)
    if code != 0:
        print(f"Could not read the repo: {err}", file=sys.stderr)
        return 1
    info = json.loads(out)
    repo, branch = info["nameWithOwner"], info["defaultBranchRef"]["name"]

    code, current, err = gh("api", f"repos/{repo}/branches/{branch}/protection")
    if code == 0:
        print(f"{repo} already protects {branch}:\n{current}\n")
        if not args.replace:
            print("Nothing changed. Rerun with --replace to replace these rules with the plan below.")
    elif "Branch not protected" not in err:
        print(f"GitHub will not protect {branch} on {repo}: {err}", file=sys.stderr)
        print("A private repo needs a paid GitHub plan for branch protection.", file=sys.stderr)
        return 1

    checks = args.check or check_names(repo, branch)
    protection = build_protection(checks)
    print(describe(repo, branch, checks))
    if not args.apply or (code == 0 and not args.replace):
        print("\nDry run: nothing changed. Rerun with --apply to turn this on.")
        return 0

    code, _, err = gh("api", "-X", "PUT", f"repos/{repo}/branches/{branch}/protection", "--input", "-",
                      payload=protection)
    if code != 0:
        print(f"GitHub refused the change: {err}", file=sys.stderr)
        return 1
    print(f"\nBranch protection is on for {branch}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
