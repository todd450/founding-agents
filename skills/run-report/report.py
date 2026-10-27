#!/usr/bin/env python3
"""Report a run's time, tokens and cost by role, from Claude Code's session logs.

`report.py --workflow build --issue 10` finds the newest session in this product that ran
`/founding-agents:build 10` and prints a Markdown table; `--post` also comments it on the issue.
Costs are API-equivalent at list prices: on a Pro or Max plan the run uses the weekly limit, not
dollars, so the figure is for comparing runs and roles, not a bill.
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# $ per million tokens: input, output, cache write (5 min), cache write (1 hour), cache read.
# List prices as of 6 Oct 2026; Haiku's double above 100K-token prompts, which these runs stay under.
PRICES = {
    "opus": (4.00, 20.00, 5.00, 8.00, 0.20),
    "sonnet": (2.00, 10.00, 2.50, 4.00, 0.20),
    "haiku": (0.10, 0.50, 0.125, 0.20, 0.01),
}


def family(model):
    return next((name for name in PRICES if name in (model or "")), "other")


def cost(model, usage):
    prices = PRICES.get(family(model))
    if not prices:
        return 0.0
    w1h = (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
    w5m = usage.get("cache_creation_input_tokens", 0) - w1h
    counts = (usage.get("input_tokens", 0), usage.get("output_tokens", 0), w5m, w1h,
              usage.get("cache_read_input_tokens", 0))
    return sum(n * p for n, p in zip(counts, prices)) / 1e6


def records(path):
    with open(path, encoding="utf-8") as lines:
        for line in lines:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def calls(path):
    """One (timestamp, model, usage) per model call; a call logged on several lines counts once."""
    last = {}
    for record in records(path):
        message = record.get("message") or {}
        if record.get("type") == "assistant" and message.get("usage") and message.get("id"):
            last[message["id"]] = (record.get("timestamp"), message.get("model"), message["usage"])
    return list(last.values())


def transcripts(session):
    """The session's own log, then each subagent's, with the role it ran as."""
    yield session, "main session"
    for meta in sorted(session.with_suffix("").glob("subagents/**/agent-*.meta.json")):
        role = json.loads(meta.read_text()).get("agentType") or "subagent"
        role = role.replace("founding-agents:", "").replace("workflow-subagent", "workflow step")
        yield meta.with_name(meta.name.replace(".meta.json", ".jsonl")), role


def summarise(session):
    rows = defaultdict(lambda: {"calls": 0, "new": 0, "cached": 0, "out": 0, "cost": 0.0, "stamps": []})
    for path, role in transcripts(session):
        if not path.exists():
            continue
        for stamp, model, usage in calls(path):
            row = rows[(role, family(model))]
            row["calls"] += 1
            row["new"] += usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            row["cached"] += usage.get("cache_read_input_tokens", 0)
            row["out"] += usage.get("output_tokens", 0)
            row["cost"] += cost(model, usage)
            if stamp:
                row["stamps"].append(stamp)
    return rows


def minutes(stamps):
    times = [datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps]
    return (max(times) - min(times)).total_seconds() / 60 if times else 0.0


def tokens(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K"


def table(rows, title, budget=None):
    stamps = [s for row in rows.values() for s in row["stamps"]]
    total = sum(row["cost"] for row in rows.values())
    lines = [f"**Run report** · {title} · {minutes(stamps):.0f} min · ${total:.2f} at API prices", "",
             "| Role | Model | Time | Calls | Input, new | Input, cached | Output | Cost |",
             "|---|---|---|---|---|---|---|---|"]
    if budget is not None and total > budget:
        lines[1:1] = ["", f"**Over budget:** ${total:.2f} against ${budget:.2f} for one run. Look at which role "
                          "took it before the next run of this kind."]
    for (role, model), row in sorted(rows.items(), key=lambda kv: -kv[1]["cost"]):
        lines.append(f"| {role} | {model} | {minutes(row['stamps']):.0f} min | {row['calls']} | "
                     f"{tokens(row['new'])} | {tokens(row['cached'])} | {tokens(row['out'])} | ${row['cost']:.2f} |")
    sums = {key: sum(row[key] for row in rows.values()) for key in ("calls", "new", "cached", "out")}
    lines.append(f"| **Total** | | {minutes(stamps):.0f} min | {sums['calls']} | {tokens(sums['new'])} | "
                 f"{tokens(sums['cached'])} | {tokens(sums['out'])} | **${total:.2f}** |")
    lines += ["", "Cost is API-equivalent at list prices; on a Pro or Max plan the run uses the weekly "
                  "limit instead. Time is from each role's first to last model call. The step that "
                  "posts this report is not in it."]
    return "\n".join(lines)


def project_logs(folder):
    """Claude Code keeps a project's sessions under ~/.claude/projects/, named from its path."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(folder))


def first_prompt(session):
    for record in records(session):
        if record.get("type") == "user":
            content = (record.get("message") or {}).get("content")
            return content if isinstance(content, str) else json.dumps(content)
    return ""


def find_session(logs, workflow, issue):
    """The newest session whose first prompt ran this workflow on this issue."""
    wanted = re.compile(rf"founding-agents:{workflow}\b.*?(?:<command-args>|\s)#?{issue}\b", re.S)
    for session in sorted(logs.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        if wanted.search(first_prompt(session)):
            return session
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflow", choices=["build", "plan", "propose"], help="the workflow the run was")
    parser.add_argument("--issue", type=int, help="the issue it ran on")
    parser.add_argument("--session", type=Path, help="a session log to report on instead of finding one")
    parser.add_argument("--post", action="store_true", help="comment the report on the issue")
    parser.add_argument("--budget", type=float, help="dollars one run should stay under; the report flags a run over it")
    args = parser.parse_args(argv)

    if args.session:
        session = args.session
    else:
        if not (args.workflow and args.issue):
            parser.error("give --workflow and --issue, or --session")
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        folder = Path(top.stdout.strip()) if top.returncode == 0 else Path.cwd()
        session = find_session(project_logs(folder), args.workflow, args.issue)
        if not session:
            print(f"No session in {project_logs(folder)} ran {args.workflow} on #{args.issue}.", file=sys.stderr)
            return 1

    title = f"`{args.workflow}` #{args.issue}" if args.workflow else session.stem
    report = table(summarise(session), title, args.budget)
    print(report)
    if args.post:
        if not args.issue:
            parser.error("--post needs --issue")
        posted = subprocess.run(["gh", "issue", "comment", str(args.issue), "--body-file", "-"],
                                input=report, capture_output=True, text=True)
        if posted.returncode != 0:
            print(f"Could not post the report: {posted.stderr.strip()}", file=sys.stderr)
            return 1
        print(posted.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
