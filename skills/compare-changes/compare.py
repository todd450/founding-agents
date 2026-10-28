#!/usr/bin/env python3
"""Compare changes made with Founding Agents against changes made without it, from merged PRs.

A merged PR is with the plugin when it has the `with-plugin` label or came from `build`'s branch
(`build/issue-<n>`), and without it when it has the `without-plugin` label. Any other PR is left out
of both groups, though it can still be the follow-up fix to one of them.

For each change it reads:
- cost: the run reports (`run-report`) posted on the PR and on the issues it closes, so a change
  built with `propose` and `build` counts both runs. A change with no report has no cost.
- time to merge: from the PR's first commit to its merge.
- fixed later: a later merged PR that changed one of its files within two weeks of its merge, and
  is a fix (a `bug` or `fix` label, or "fix" or "revert" in its title). A change merged under two
  weeks ago is still open to one, so it is counted apart.
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
from datetime import datetime, timedelta, timezone

WINDOW = timedelta(days=14)
BUILD_BRANCH = re.compile(r"^build/issue-\d+$")
FIX_TITLE = re.compile(r"\b(fix|fixes|fixed|revert|reverts)\b", re.I)
FIX_LABELS = {"bug", "fix"}
# The first line of a run report: **Run report** · `build` #12 · 29 min · $6.19 at API prices
RUN_COST = re.compile(r"^\*\*Run report\*\* · .* · \$([\d.]+) at API prices", re.M)
# Its own query because `gh pr list --json commits` asks for every commit's authors, which passes
# GitHub's node limit at 200 PRs. A PR's commits come oldest first, so the first one is enough.
QUERY = """query($owner: String!, $name: String!, $size: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: $size, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title headRefName createdAt mergedAt
        labels(first: 20) { nodes { name } }
        files(first: 100) { nodes { path } }
        commits(first: 1) { nodes { commit { authoredDate } } }
        closingIssuesReferences(first: 10) { nodes { number } }
      }
    }
  }
}"""


def when(stamp):
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def labels(pr):
    return {label["name"] for label in pr.get("labels") or []}


def group(pr):
    """'with', 'without' or None for a PR in neither group."""
    if "with-plugin" in labels(pr):
        return "with"
    if "without-plugin" in labels(pr):
        return "without"
    if BUILD_BRANCH.match(pr.get("headRefName") or ""):
        return "with"
    return None


def files(pr):
    return {f["path"] for f in pr.get("files") or []}


def is_fix(pr):
    return bool(labels(pr) & FIX_LABELS) or bool(FIX_TITLE.search(pr.get("title") or ""))


def follow_ups(pr, merged):
    """The later merged PRs that fixed one of this PR's files within two weeks of its merge."""
    end, touched = when(pr["mergedAt"]), files(pr)
    return [other["number"] for other in merged
            if other["number"] != pr["number"] and is_fix(other) and files(other) & touched
            and end < when(other["mergedAt"]) <= end + WINDOW]


def hours_to_merge(pr):
    commits = [c["authoredDate"] for c in pr.get("commits") or [] if c.get("authoredDate")]
    start = min(map(when, commits)) if commits else when(pr["createdAt"])
    return (when(pr["mergedAt"]) - start).total_seconds() / 3600


def run_costs(bodies):
    return [float(cost) for body in bodies for cost in RUN_COST.findall(body)]


def change(pr, merged, comments, now):
    """One row for the report; comments(n) gives the comment bodies on issue or PR n."""
    numbers = [pr["number"]] + [issue["number"] for issue in pr.get("closingIssuesReferences") or []]
    costs = run_costs(body for n in dict.fromkeys(numbers) for body in comments(n))
    return {"number": pr["number"], "title": pr["title"], "group": group(pr),
            "cost": sum(costs) if costs else None, "hours": hours_to_merge(pr),
            "settled": when(pr["mergedAt"]) + WINDOW <= now, "fixes": follow_ups(pr, merged)}


def duration(hours):
    return f"{hours * 60:.0f} min" if hours < 1 else f"{hours:.1f} h" if hours < 48 else f"{hours / 24:.1f} days"


def summary(rows):
    costs = [row["cost"] for row in rows if row["cost"] is not None]
    settled = [row for row in rows if row["settled"]]
    fixed = [row for row in settled if row["fixes"]]
    cost = f"${statistics.median(costs):.2f} ({len(costs)} of {len(rows)} reported)" if costs else "none reported"
    later = f"{len(fixed)} of {len(settled)}" if settled else "none past two weeks yet"
    waiting = len(rows) - len(settled)
    if waiting:
        later += f" ({waiting} merged under two weeks ago)"
    return cost, duration(statistics.median(row["hours"] for row in rows)), later


def report(rows, repo):
    lines = [f"**With and without Founding Agents** · {repo}", "",
             "| | Changes | Median cost | Median time to merge | Fixed later |", "|---|---|---|---|---|"]
    for key, name in (("with", "With the plugin"), ("without", "Without it")):
        chosen = [row for row in rows if row["group"] == key]
        if chosen:
            lines.append(f"| {name} | {len(chosen)} | " + " | ".join(summary(chosen)) + " |")
        else:
            lines.append(f"| {name} | 0 | | | |")
    lines += ["", "| PR | Group | Cost | Time to merge | Fixed later by |", "|---|---|---|---|---|"]
    for row in sorted(rows, key=lambda row: row["number"], reverse=True):
        cost = f"${row['cost']:.2f}" if row["cost"] is not None else "not reported"
        fixes = ", ".join(f"#{n}" for n in row["fixes"]) or ("none" if row["settled"] else "none yet")
        lines.append(f"| #{row['number']} {row['title']} | {row['group']} | {cost} | "
                     f"{duration(row['hours'])} | {fixes} |")
    lines += ["", "Cost is the run reports posted on the PR and the issues it closes, API-equivalent at list "
                  "prices. Time to merge runs from the PR's first commit. A fix later is a merged PR within two "
                  "weeks that changed one of the same files and is labelled `bug` or `fix` or says fix or revert "
                  "in its title, so check the ones listed before reading much into the count."]
    return "\n".join(lines)


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout


def merged_prs(repo, limit):
    """The latest merged PRs, shaped like `gh pr list --json` output."""
    owner, name = repo.split("/")
    prs, cursor = [], None
    while len(prs) < limit:
        args = ["api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={owner}", "-f", f"name={name}",
                "-F", f"size={min(50, limit - len(prs))}"]
        if cursor:
            args += ["-f", f"cursor={cursor}"]
        page = json.loads(gh(*args))["data"]["repository"]["pullRequests"]
        for node in page["nodes"]:
            prs.append({**node, "labels": node["labels"]["nodes"], "files": node["files"]["nodes"],
                        "commits": [c["commit"] for c in node["commits"]["nodes"]],
                        "closingIssuesReferences": node["closingIssuesReferences"]["nodes"]})
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return prs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="owner/name; defaults to the repo in this folder")
    parser.add_argument("--limit", type=int, default=200, help="how many of the latest merged PRs to read")
    parser.add_argument("--since", help="only changes merged on or after this date, YYYY-MM-DD")
    args = parser.parse_args(argv)

    repo = args.repo or gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner").strip()
    merged = merged_prs(repo, args.limit)
    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc) if args.since else None
    chosen = [pr for pr in merged if group(pr) and (not since or when(pr["mergedAt"]) >= since)]
    if not chosen:
        print(f"No merged PR in {repo} is labelled `with-plugin` or `without-plugin` or came from a "
              "`build/issue-<n>` branch.", file=sys.stderr)
        return 1

    def comments(number):
        out = gh("api", f"repos/{repo}/issues/{number}/comments", "--paginate", "--jq", ".[].body | @json")
        return [json.loads(line) for line in out.splitlines() if line]

    now = datetime.now(timezone.utc)
    print(report([change(pr, merged, comments, now) for pr in chosen], repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
