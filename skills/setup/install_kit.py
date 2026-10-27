#!/usr/bin/env python3
"""Install one of setup's kits in a product repo: `basics`, `ci`, `ops-watch`,
`ops-routine`, `optimiser` or `librarian`. Prints the plan by default;
writes nothing without --apply.

Kits are copied, not referenced, because a product's workflow cannot read the private plugin repo.
Rerunning brings the product's copies of setup's own files up to date. A starter file, such as
`check.sh` or `CLAUDE.md`, is written only when the product has none: the product owns it from then on.
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Each kit: (source, where it goes in the product, whether setup keeps it current).
KITS = {
    "basics": [
        (HERE / "basics" / "CLAUDE.md", Path("CLAUDE.md"), False),
        (HERE / "basics" / "fixtures" / "README.md", Path("fixtures/README.md"), False),
    ],
    "ci": [
        (HERE / "ci" / "ci.yml", Path(".github/workflows/ci.yml"), True),
        (HERE / "ci" / "check.sh", Path("check.sh"), False),
    ],
    "ops-watch": [
        (HERE / "ops_watch" / "check_site.py", Path(".github/ops-watch/check_site.py"), True),
        (HERE / "ops_watch" / "ops-watch.yml", Path(".github/workflows/ops-watch.yml"), True),
    ],
    "ops-routine": [
        (HERE / "ops_watch" / "routine.md", Path(".github/ops-watch/routine.md"), True),
        (HERE / "ops_watch" / "check_back.py", Path(".github/ops-watch/check_back.py"), True),
        (HERE / "ops_watch" / "watch.md", Path(".github/ops-watch/watch.md"), False),
    ],
    "optimiser": [
        (HERE / "optimiser" / "routine.md", Path(".github/optimiser/routine.md"), True),
    ],
    "librarian": [
        (HERE / "librarian" / "routine.md", Path(".github/librarian/routine.md"), True),
    ],
}


def plan(root, kit):
    """Each file to install, where it goes, and whether that is new, a change or already there."""
    steps = []
    for source, target, managed in KITS[kit]:
        path = root / target
        if not path.exists():
            state = "new"
        elif not managed:
            state = "kept: the product's own"
        elif path.read_bytes() == source.read_bytes():
            state = "already up to date"
        else:
            state = "replaces the product's different copy"
        steps.append((source, target, state))
    return steps


def install(root, steps):
    for source, target, state in steps:
        if state in ("new", "replaces the product's different copy"):
            (root / target).parent.mkdir(parents=True, exist_ok=True)
            (root / target).write_bytes(source.read_bytes())
            (root / target).chmod(source.stat().st_mode & 0o777)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kit", choices=sorted(KITS))
    parser.add_argument("--apply", action="store_true", help="write the files instead of printing the plan")
    args = parser.parse_args(argv)

    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        print("Run this from the product repo's folder.", file=sys.stderr)
        return 1
    root = Path(top.stdout.strip())

    steps = plan(root, args.kit)
    print(f"{args.kit} for {root.name}:")
    for _, target, state in steps:
        print(f"- {target}: {state}")
    if args.kit == "ops-watch":
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
    print("\nWritten. Commit them on a branch and open a PR; they take effect once merged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
