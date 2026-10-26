#!/usr/bin/env python3
"""Install ops watch's nightly site check in a product repo. Prints the plan by default; writes
nothing without --apply.

The check is copied, not referenced, because a product's workflow cannot read the private plugin
repo. Rerunning this after the plugin's copy changes brings the product's copy up to date.
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "ops_watch"
FILES = {
    HERE / "check_site.py": Path(".github/ops-watch/check_site.py"),
    HERE / "ops-watch.yml": Path(".github/workflows/ops-watch.yml"),
}


def plan(root):
    """Each file to install, where it goes, and whether that is new, a change or already there."""
    steps = []
    for source, target in FILES.items():
        path = root / target
        if not path.exists():
            state = "new"
        elif path.read_bytes() == source.read_bytes():
            state = "already up to date"
        else:
            state = "replaces the product's different copy"
        steps.append((source, target, state))
    return steps


def install(root, steps):
    for source, target, state in steps:
        if state != "already up to date":
            (root / target).parent.mkdir(parents=True, exist_ok=True)
            (root / target).write_bytes(source.read_bytes())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the files instead of printing the plan")
    args = parser.parse_args(argv)

    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        print("Run this from the product repo's folder.", file=sys.stderr)
        return 1
    root = Path(top.stdout.strip())

    steps = plan(root)
    print(f"Ops watch for {root.name}:")
    for _, target, state in steps:
        print(f"- {target}: {state}")
    pages = subprocess.run(["gh", "api", "repos/{owner}/{repo}/pages", "--jq", ".html_url"],
                           cwd=root, capture_output=True, text=True)
    if pages.returncode == 0:
        print(f"- it will watch {pages.stdout.strip()}")
    else:
        print("- GitHub Pages is not on for this repo, so the first run will raise red until it is")

    if not args.apply:
        print("\nDry run: nothing written. Rerun with --apply to write the files.")
        return 0
    install(root, steps)
    print("\nWritten. Commit them on a branch and open a PR; the check runs nightly once merged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
