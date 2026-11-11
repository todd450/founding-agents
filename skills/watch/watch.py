#!/usr/bin/env python3
"""Show what the agents of a build or propose run did: a timeline of the run, a close-up of each
agent, and with --live a board of who is working now.

Claude Code keeps a record of every workflow run on this machine, one file per agent, under
`~/.claude/projects/<the product's folder>/<session>/subagents/workflows/wf_<run>/`. This reads
that record and nothing else, so watching a run costs no tokens and no agent reports anything.

The page shows when each step ran, what kind it was, the short description the agent gave it and
whether it failed. It never shows a command's text or its output, which can hold a secret. The
live board is a server of its own that answers two addresses, the page and the run's data, on
this machine only; it serves no file from any folder.
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "page.html"
BRIEF = 200  # characters of an agent's instructions the page shows
SUBJECT = re.compile(r"\b(issue|PR) #(\d+)")


def records(product, home=None):
    """Where Claude Code keeps its record of sessions run in this product's folder."""
    home = Path(home or os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return home / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(Path(product).resolve()))


def last_touched(folder):
    return max((f.stat().st_mtime for f in folder.glob("agent-*.jsonl")), default=0)


def runs(product, home=None):
    """Each workflow run recorded for this product, newest first."""
    found = [f for f in records(product, home).glob("*/subagents/workflows/wf_*") if any(f.glob("agent-*.jsonl"))]
    return sorted(found, key=last_touched, reverse=True)


def rows(path):
    """A record's lines. A run still going can leave its last line half written; that line waits."""
    out = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return [row for row in out if isinstance(row, dict)]


def when(row):
    try:
        return datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError, AttributeError):
        return None


def text_of(content):
    if isinstance(content, str):
        return content
    return next((part.get("text", "") for part in content or [] if part.get("type") == "text"), "")


def subject(brief):
    """The issue an agent worked on, or its PR when its instructions name no issue."""
    found = dict((kind, number) for kind, number in reversed(SUBJECT.findall(brief[:600])))
    if "issue" in found:
        return f"Issue #{found['issue']}"
    return f"PR #{found['PR']}" if "PR" in found else ""


def describe(tool, given):
    """What a step was, in the agent's own few words. Never the command itself."""
    if given.get("description"):
        return str(given["description"])[:90]
    if given.get("file_path"):
        return Path(str(given["file_path"])).name
    return str(given.get("skill") or given.get("pattern") or "")[:90]


def read_agent(path):
    lines = [row for row in rows(path) if when(row) is not None]
    if not lines:
        return None
    try:
        meta = json.loads(path.with_name(path.name.replace(".jsonl", ".meta.json")).read_text())
    except (OSError, ValueError):
        meta = {}
    steps, by_id = [], {}
    for row in lines:
        content = (row.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if row.get("type") == "assistant" and part.get("type") == "tool_use":
                step = {"t": when(row), "k": part.get("name", ""), "d": describe(part.get("name"), part.get("input") or {}), "x": 0}
                steps.append(step)
                by_id[part.get("id")] = step
            elif part.get("type") == "tool_result" and part.get("is_error") and part.get("tool_use_id") in by_id:
                by_id[part["tool_use_id"]]["x"] = 1
    # What the agent was told is the last thing said to it before it first answers: a newer Claude
    # Code puts a note of its own ahead of the workflow's instructions.
    told = lines[0]
    for row in lines:
        if row.get("type") != "user":
            break
        told = row
    said = text_of((told.get("message") or {}).get("content"))
    if said.startswith("[Workflow harness"):
        said = said.partition("\n")[2]  # that note is one line; the instructions follow it
    brief = " ".join(said.split())
    return {
        "id": path.stem[len("agent-"):],
        "role": str(meta.get("agentType") or "workflow-subagent").split(":")[-1],
        "model": meta.get("pickedEffortModel") or meta.get("model") or "",
        # The step's name and phase in the workflow, which Claude Code records from version 2.1.3xx.
        "label": meta.get("description") or "",
        "phase": meta.get("workflowPhase") or "",
        "s": when(lines[0]),
        "e": when(lines[-1]),
        "subject": subject(brief),
        "brief": brief[:BRIEF],
        "steps": steps,
    }


def read_run(folder, now=None):
    """One run as the page draws it: every time in whole seconds from the run's first moment."""
    folder = Path(folder)
    agents = sorted(filter(None, (read_agent(path) for path in folder.glob("agent-*.jsonl"))), key=lambda a: a["s"])
    journal = folder / "journal.jsonl"
    finished = {row.get("agentId") for row in rows(journal) if row.get("type") == "result"} if journal.exists() else None
    start = agents[0]["s"] if agents else 0
    for agent in agents:
        # With no journal there is nothing to say an agent is still going, so it counts as finished.
        agent["done"] = finished is None or agent["id"] in finished
        agent["s"], agent["e"] = round(agent["s"] - start), round(agent["e"] - start)
        for step in agent["steps"]:
            step["t"] = round(step["t"] - start)
    return {
        "id": folder.name,
        "started": datetime.fromtimestamp(start).strftime("%-d %b %Y, %H:%M") if agents else "",
        "now": round((now if now is not None else time.time()) - start),
        "agents": agents,
    }


def page(run, product, live=False):
    """The page with a run written into it. A live page starts empty and asks the server."""
    data = {"product": Path(product).resolve().name, "live": live, "run": run}
    # `</` would end the script the data sits in.
    return PAGE.read_text().replace("__DATA__", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))


def server(product, home=None, port=0):
    """The live board's server: the page, and the newest run's data read fresh on each ask."""

    class Board(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self.answer(page(None, product, live=True), "text/html; charset=utf-8")
            elif self.path == "/run.json":
                found = runs(product, home)
                self.answer(json.dumps(read_run(found[0]) if found else None), "application/json")
            else:
                self.send_error(404)

        def answer(self, body, kind):
            body = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Board)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--product", default=".", help="the product repo's folder (default: this one)")
    parser.add_argument("--run", help="a run's id, as --list prints it (default: the newest)")
    parser.add_argument("--list", action="store_true", help="list the recorded runs and stop")
    parser.add_argument("--live", action="store_true", help="serve a board of the run going on now, until stopped")
    parser.add_argument("--open", action="store_true", help="open the page in the browser")
    args = parser.parse_args()

    if args.live:
        board = server(args.product)
        url = f"http://127.0.0.1:{board.server_address[1]}/"
        print(f"Live board: {url} (this machine only; stop it with Ctrl-C)", flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            board.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    found = runs(args.product)
    if not found:
        print(f"No workflow run is recorded for {Path(args.product).resolve()}. Run this from the product's folder, "
              "on the machine the run was on.", file=sys.stderr)
        return 1
    if args.list:
        for folder in found:
            run = read_run(folder)
            length = max((a["e"] for a in run["agents"]), default=0)
            print(f"{run['id']}  {run['started']}  {len(run['agents'])} agents  {length // 60} min")
        return 0
    folder = next((f for f in found if f.name == args.run), None) if args.run else found[0]
    if not folder:
        print(f"No run named {args.run}. --list prints the ones there are.", file=sys.stderr)
        return 1
    out = Path(tempfile.gettempdir()) / "founding-agents-watch" / f"{folder.name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(read_run(folder), args.product))
    print(out)
    if args.open:
        webbrowser.open(out.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
