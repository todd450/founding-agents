#!/usr/bin/env python3
"""Report a run's time, tokens and cost by role, from Claude Code's session logs.

`report.py --workflow build --issue 10` finds the newest session in this product that ran
`/founding-agents:build 10` and prints a Markdown table; `--post` also comments it on the issue.
`report.py --runs` reads every `build` run report on the repo and gives the share that ended in a
merge without the founder, and the share that stopped.
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

# $ per million tokens: input, output, cache write (5 min), cache write (1 hour), cache read, by the
# model a call names, longest prefix first. A model alias such as `opus` resolves to whichever model
# Claude Code picks, so a run is priced by the model it actually ran: on 27 Oct 2026 a headless
# `build` asked for `opus` and ran `claude-opus-5`, and pricing every Opus call at Opus 5.5's rate
# reported $7.08 where Claude Code counted $11.10. These match Claude Code's own `total_cost_usd`
# for that run to the cent (Sonnet 5 included, at $3/$15). Haiku 5.5 doubles above 100K-token
# prompts, which these runs stay under.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 5.00, 8.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 6.25, 10.00, 0.50),
    "claude-opus-4": (5.00, 25.00, 6.25, 10.00, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00, 2.50, 4.00, 0.20),
    "claude-sonnet-5": (3.00, 15.00, 3.75, 6.00, 0.30),
    "claude-sonnet-4": (3.00, 15.00, 3.75, 6.00, 0.30),
    "claude-haiku-5-5": (0.10, 0.50, 0.125, 0.20, 0.01),
    "claude-haiku-4-5": (1.00, 5.00, 1.25, 2.00, 0.10),
}


def priced(model):
    """The PRICES key for a model id, or None for a model the table does not know."""
    return next((key for key in sorted(PRICES, key=len, reverse=True) if (model or "").startswith(key)), None)


def family(model):
    """The model as the table shows it: `opus-5`, `sonnet-5-5`; the id itself when it is not priced."""
    key = priced(model)
    return key.removeprefix("claude-") if key else (model or "other")


def cost(model, usage):
    prices = PRICES.get(priced(model))
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
    rows = defaultdict(lambda: {"calls": 0, "new": 0, "cached": 0, "out": 0, "cost": 0.0, "stamps": [], "priced": True})
    for path, role in transcripts(session):
        if not path.exists():
            continue
        for stamp, model, usage in calls(path):
            row = rows[(role, family(model))]
            row["priced"] = row["priced"] and priced(model) is not None
            row["calls"] += 1
            row["new"] += usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            row["cached"] += usage.get("cache_read_input_tokens", 0)
            row["out"] += usage.get("output_tokens", 0)
            row["cost"] += cost(model, usage)
            if stamp:
                row["stamps"].append(stamp)
    return rows


def spent_on(session, issue):
    """Dollars a run's agents have spent on one issue so far. Every task `build` gives an agent for an
    issue names it ("issue #12"), so an agent counts when its first prompt does; a brief's run builds
    several issues in one session, and this tells them apart."""
    names = re.compile(rf"\bissue #{issue}\b")
    total = 0.0
    for path, role in transcripts(session):
        if role != "main session" and path.exists() and names.search(first_prompt(path)):
            total += sum(cost(model, usage) for _, model, usage in calls(path))
    return total


def minutes(stamps):
    times = [datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps]
    return (max(times) - min(times)).total_seconds() / 60 if times else 0.0


def tokens(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K"


# How a run ended, as its report says it. A run is ready when every change it built was approved
# and only the founder's merge is left, as where a merge deploys to production.
OUTCOMES = {"merged": "merged", "ready": "ready for the founder's merge", "stopped": "stopped for the founder"}


def table(rows, title, budget=None, outcome=None):
    stamps = [s for row in rows.values() for s in row["stamps"]]
    total = sum(row["cost"] for row in rows.values())
    lines = [f"**Run report** · {title} · {minutes(stamps):.0f} min · ${total:.2f} at API prices", "",
             "| Role | Model | Time | Calls | Input, new | Input, cached | Output | Cost |",
             "|---|---|---|---|---|---|---|---|"]
    if budget is not None and total > budget:
        lines[1:1] = ["", f"**Over budget:** ${total:.2f} against ${budget:.2f} for one run. Look at which role "
                          "took it before the next run of this kind."]
    unpriced = sorted({model for (_, model), row in rows.items() if not row["priced"]})
    if unpriced:
        lines[1:1] = ["", f"**Not priced:** {', '.join(unpriced)}. The run-report skill has no price for "
                          "this model, so its calls are counted but left out of the cost."]
    if outcome:
        lines[1:1] = ["", f"**Outcome:** {OUTCOMES[outcome]}"]
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


BUILD_REPORT = re.compile(r"\*\*Run report\*\* · `build` #(\d+)")
OUTCOME = re.compile(r"^\*\*Outcome:\*\* (merged|ready|stopped)", re.M)


def build_runs(comments):
    """Counts `build` runs by how they ended, oldest first. A run merged without the founder when it
    merged and was the first run on its issue: a merged run closes its issue, so a second run means
    the founder stepped in after the first one stopped."""
    counts = {"merged alone": 0, "merged after a stop": 0, "ready": 0, "stopped": 0, "unrecorded": 0}
    seen = set()
    for comment in sorted(comments, key=lambda c: c["created_at"]):
        run = BUILD_REPORT.match(comment["body"])
        if not run:
            continue
        issue, ended = run.group(1), OUTCOME.search(comment["body"])
        if not ended:
            counts["unrecorded"] += 1
        elif ended.group(1) in ("stopped", "ready"):
            counts[ended.group(1)] += 1
        else:
            counts["merged after a stop" if issue in seen else "merged alone"] += 1
        seen.add(issue)
    return counts


def runs_table(counts, since=None):
    total = counts["merged alone"] + counts["merged after a stop"] + counts["ready"] + counts["stopped"]
    when = f" since {since}" if since else ""
    left_out = (f" {counts['unrecorded']} report(s) from before outcomes were recorded are left out."
                if counts["unrecorded"] else "")
    if not total:
        return f"**Build runs**{when} · none with a recorded outcome yet.{left_out}"
    share = lambda n: f"{100 * n / total:.0f}%"
    lines = [f"**Build runs**{when} · {total} with a recorded outcome", "",
             "| Ended | Runs | Share |", "|---|---|---|",
             f"| Merged without the founder | {counts['merged alone']} | {share(counts['merged alone'])} |",
             f"| Merged after an earlier run stopped | {counts['merged after a stop']} | {share(counts['merged after a stop'])} |",
             f"| Ready, left for the founder's merge | {counts['ready']} | {share(counts['ready'])} |",
             f"| Stopped for the founder | {counts['stopped']} | {share(counts['stopped'])} |", "",
             f"A run merged without the founder when it merged and was the first `build` run on its issue.{left_out}"]
    return "\n".join(lines)


def run_reports(since=None):
    """Every `build` run report commented on this repo, through REST so it also works in the cloud."""
    path = "repos/{owner}/{repo}/issues/comments?per_page=100" + (f"&since={since}" if since else "")
    pick = '.[] | select(.body | startswith("**Run report** · `build`")) | {created_at, body} | @json'
    out = subprocess.run(["gh", "api", "--paginate", path, "--jq", pick], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return [json.loads(line) for line in out.stdout.splitlines() if line.strip()]


def project_logs(folder):
    """Claude Code keeps a project's sessions under ~/.claude/projects/, named from its path."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(folder))


def first_prompt(session):
    for record in records(session):
        if record.get("type") == "user":
            content = (record.get("message") or {}).get("content")
            return content if isinstance(content, str) else json.dumps(content)
    return ""


def asked_for_this_report(session, workflow, issue):
    """Whether one of the session's steps was asked to post this report. A run started on an idea in
    words names no issue in its first prompt: `propose` opens the issue partway through, so only the
    report step's own prompt ties the session to it."""
    asked = re.compile(rf"--workflow {workflow} --issue {issue}\b")
    for path in session.with_suffix("").glob("subagents/**/agent-*.jsonl"):
        if asked.search(first_prompt(path)):
            return True
    return False


def find_session(logs, workflow, issue):
    """The newest session whose first prompt ran this workflow on this issue, or that ran this
    workflow and asked for this report. A sweep names a kind, not an issue, so for a sweep it is the
    newest session that ran one."""
    ran = re.compile(rf"founding-agents:{workflow}\b")
    on_issue = re.compile(rf"founding-agents:{workflow}\b.*?(?:<command-args>|\s)#?{issue}\b", re.S)
    for session in sorted(logs.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        prompt = first_prompt(session)
        if not ran.search(prompt):
            continue
        if workflow == "sweep" or on_issue.search(prompt) or asked_for_this_report(session, workflow, issue):
            return session
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflow", choices=["build", "plan", "propose", "sweep"], help="the workflow the run was")
    parser.add_argument("--issue", type=int, help="the issue it ran on")
    parser.add_argument("--session", type=Path, help="a session log to report on instead of finding one")
    parser.add_argument("--post", action="store_true", help="comment the report on the issue")
    parser.add_argument("--budget", type=float, help="dollars one run should stay under; the report flags a run over it")
    parser.add_argument("--outcome", choices=sorted(OUTCOMES), help="how the run ended, recorded in the report")
    parser.add_argument("--spent-on", type=int, metavar="ISSUE",
                        help="print only the dollars the run has spent on this issue so far")
    parser.add_argument("--runs", action="store_true",
                        help="the share of build runs that merged without the founder, and that stopped")
    parser.add_argument("--since", help="with --runs, only reports from this date (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    if args.runs:
        try:
            print(runs_table(build_runs(run_reports(args.since)), args.since))
        except RuntimeError as error:
            print(f"Could not read the run reports: {error}", file=sys.stderr)
            return 1
        return 0
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

    if args.spent_on:
        print(f"{spent_on(session, args.spent_on):.2f}")
        return 0
    title = f"`{args.workflow}` #{args.issue}" if args.workflow else session.stem
    report = table(summarise(session), title, args.budget, args.outcome)
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
