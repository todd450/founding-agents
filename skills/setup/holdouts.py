#!/usr/bin/env python3
"""Set up a product's holdout scenarios: a private `<product>-holdouts` repo, cloned under
~/.founding-agents/holdouts/<owner>/<name> where no product folder or worktree holds it. Prints the
plan by default; changes nothing without --apply.

Only the reviewer reads the holdouts; the plugin's guard_holdouts hook blocks other agents.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# The failure classes of the edge-case checklist (docs/design.md, "The team"), one folder each.
CLASSES = {
    "empty-and-one": "no items, one item, and the most there can be",
    "data-and-account-shapes": "other shapes of data and account than the usual one",
    "other-language": "every language the product ships, and the longest text",
    "phone-width": "a phone-width screen, and the widest",
    "failed-read": "a read or write that fails, is slow, or happens twice",
    "second-user": "a second person, and someone who should not see it",
    "time-zones": "other time zones, midnight, month ends and daylight saving",
}

README = """# Holdout scenarios

Edge-case scenarios for {repo} that its builders never see. Only the Founding Agents reviewer reads
them, and a plugin hook blocks every other agent. A change that passes every visible fixture and
fails one of these is what they exist to catch.

One Markdown file per scenario, in the folder of its failure class:

{classes}

Each file:

```
# <what it checks, in a few words>

## Setup
<the data, account and settings it needs>

## Steps
<what to do, in order>

## Expected
<what must be true afterwards>
```

When a holdout fails, the reviewer tells the builder its class and what went wrong, never the
scenario. A scenario a builder has seen anyway moves to the product's visible `fixtures/`, and a
new one takes its place here.
"""


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def holdout_repo(repo):
    return f"{repo}-holdouts"


def holdout_path(repo, home=None):
    owner, name = repo.split("/")
    return Path(home or Path.home()) / ".founding-agents" / "holdouts" / owner / name


def seed(folder, repo):
    """Write the README and one folder per class into an empty clone; returns the files written."""
    written = []
    readme = folder / "README.md"
    if not readme.exists():
        classes = "\n".join(f"- `{slug}/`: {what}" for slug, what in CLASSES.items())
        readme.write_text(README.format(repo=repo, classes=classes))
        written.append(readme)
    for slug in CLASSES:
        keep = folder / slug / ".gitkeep"
        if not (folder / slug).exists():
            keep.parent.mkdir(parents=True)
            keep.write_text("")
            written.append(keep)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="create, clone and seed the holdout repo")
    args = parser.parse_args(argv)

    code, repo, err = run("gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    if code != 0:
        print(f"Could not read this repo from GitHub: {err}", file=sys.stderr)
        return 1
    holdouts, folder = holdout_repo(repo), holdout_path(repo)
    exists = run("gh", "repo", "view", holdouts, "--json", "name")[0] == 0
    cloned = (folder / ".git").exists()

    print(f"Holdout scenarios for {repo}:")
    print(f"- private repo {holdouts}: {'exists' if exists else 'to create'}")
    print(f"- clone at {folder}: {'exists, to update' if cloned else 'to clone'}")
    print(f"- one folder per failure class: {', '.join(CLASSES)}")
    if not args.apply:
        return 0

    if not exists:
        code, _, err = run("gh", "repo", "create", holdouts, "--private",
                           "--description", f"Holdout scenarios for {repo}; only the reviewer reads them")
        if code != 0:
            print(f"Could not create {holdouts}: {err}", file=sys.stderr)
            return 1
    if cloned:
        code, _, err = run("git", "pull", "--ff-only", cwd=folder)
    else:
        folder.parent.mkdir(parents=True, exist_ok=True)
        code, _, err = run("gh", "repo", "clone", holdouts, str(folder))
    if code != 0:
        print(f"Could not fetch {holdouts}: {err}", file=sys.stderr)
        return 1

    if seed(folder, repo):
        for step in (("git", "add", "-A"), ("git", "commit", "-m", "Set up the holdout scenarios"),
                     ("git", "push", "-u", "origin", "HEAD")):
            code, _, err = run(*step, cwd=folder)
            if code != 0:
                print(f"Could not push the first commit to {holdouts}: {err}", file=sys.stderr)
                return 1
    print(f"Ready: {folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
