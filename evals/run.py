#!/usr/bin/env python3
"""Run the eval tasks against the team's agents and report pass rate, pass^k, tokens and cost.

`python3 evals/run.py` runs every task three times. Each trial takes the real prompt the workflow
sends that step (by running the workflow with scripted replies up to it), runs it with `claude -p`
as the step's agent and model, in a fresh throwaway repo with the `gh` stand-in, then grades what
the agent returned, posted and pushed. Costs come from the session logs, priced by `run-report`.

    python3 evals/run.py --role builder --trials 5         # one role's tasks
    python3 evals/run.py --task 09 --model qa=sonnet       # one task, on another model
    python3 evals/run.py --dry-run                         # show each task's step; run nothing
    python3 evals/run.py --report a/results.json b/results.json   # one report from several runs
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

EVALS = Path(__file__).resolve().parent
PLUGIN = EVALS.parent
sys.path[:0] = [str(EVALS), str(PLUGIN / "tests"), str(PLUGIN / "skills" / "run-report")]
import trial  # noqa: E402
from report import summarise, tokens  # noqa: E402
from workflow_harness import run_workflow  # noqa: E402

TOOLS = "Bash,Read,Edit,Write,Grep,Glob,Skill"
TIMEOUT = 25 * 60
BUDGET = 5  # dollars at API prices one trial may spend before claude stops it
SECRETS = {"ANTHROPIC_API_KEY", "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}
GITHUB = ("https://github.com/", "http://github.com/", "git@github.com:", "ssh://git@github.com/", "git://github.com/")
FENCE = {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [
    {"type": "command", "command": f"python3 {shlex.quote(str(EVALS / 'fence.py'))}"}]}]}}


def replies(task):
    """Scripted replies that carry the workflow up to the task's step, from the task's own issue."""
    step, github = task["step"], task["github"]
    issue = next(i for i in github["issues"] if i["number"] == step["args"])
    if step["workflow"] == "plan":
        return {"check": [{"ready": True, "reason": "", "repo": github["repo"], "title": issue["title"],
                           "decision": step.get("decision", "")}]}
    if step["workflow"] == "propose":
        return {}
    ticket = {"ready": True, "reason": "", "repo": github["repo"], "title": issue["title"], "body": issue["body"],
              "decision": "", "unseen": [], "open_pr": 0, "parts": [], **step.get("ticket", {})}
    pr = step.get("pr", 0)
    built = {"pr_number": pr, "pr_url": f"https://github.com/{github['repo']}/pull/{pr}", "stopped_because": ""}
    approve = {"verdict": "approve", "findings": []}
    return {"check": [ticket] * 3, "builder": [built] * 3, "qa": [approve] * 3,
            "code review": [{**approve, "security": False}] * 3}


def capture(task):
    """The prompt, agent, model, effort and schema the workflow gives the task's step."""
    run = run_workflow(task["step"]["workflow"], replies(task), task["step"]["args"])
    call = next((c for c in run["calls"] if c["label"].startswith(task["step"]["label"])), None)
    if not call:
        raise RuntimeError(f"{task['name']}: the {task['step']['workflow']} workflow never reached '{task['step']['label']}'")
    return call


# Claude Code gives a session started with --agent only the tools in the agent file, so it cannot
# return --json-schema's structured output (tested on 27 Oct 2026). Such a step is asked to end its
# reply with the result as JSON instead, and a Haiku step turns the reply into it when that fails.
ASK_FOR_JSON = "\n\nWhen you have finished, end your reply with your result as one JSON object in a ```json block, matching this JSON Schema:\n```json\n{}\n```"


def prompt(call):
    return call["prompt"] + (ASK_FOR_JSON.format(json.dumps(call["schema"])) if call["agentType"] else "")


def returned(text, schema):
    """The last JSON block in an agent's reply, when it has every field the schema requires."""
    for block in reversed(re.findall(r"```json\s*(\{.*?\})\s*```", text or "", re.S)):
        try:
            value = json.loads(block)
        except ValueError:
            continue
        if isinstance(value, dict) and all(key in value for key in schema.get("required", [])):
            return value
    return None


def extract(text, schema, env):
    """Haiku turns an agent's final reply into the step's result, adding nothing the reply does not say."""
    ask = ("Below is an agent's final report. Return what it says as the structured result. Change and add nothing: "
           "where the report says nothing about a field, use false, 0 or empty.\n\n" + (text or "(no report)"))
    done = subprocess.run(["claude", "-p", ask, "--model", "haiku", "--output-format", "json", "--json-schema",
                           json.dumps(schema), "--setting-sources", "project,local", "--tools", ""],
                          capture_output=True, text=True, env=env, timeout=300)
    try:
        result = json.loads(done.stdout)
    except ValueError:
        return None, ""
    return result.get("structured_output"), result.get("session_id", "")


def command(call, model):
    cmd = ["claude", "-p", prompt(call), "--output-format", "json", "--json-schema", json.dumps(call["schema"]),
           "--model", model, "--plugin-dir", str(PLUGIN), "--setting-sources", "project,local",
           "--allowedTools", TOOLS, "--max-budget-usd", str(BUDGET), "--settings", json.dumps(FENCE)]
    if call["agentType"]:
        cmd += ["--agent", call["agentType"]]
    if call["effort"]:
        cmd += ["--effort", call["effort"]]
    return cmd


# The models setup pins in each product, so a trial runs the model a product would.
PINNED = json.loads((EVALS.parent / "skills" / "setup" / "basics" / "settings.json").read_text())["env"]


def environment(folder):
    """The trial's environment: the gh stand-in first on PATH, an empty GitHub login, and never an API key.

    git sends every GitHub address to a folder that does not exist and forgets the founder's saved
    logins, so nothing the agent pushes or clones can reach GitHub: on 27 Oct 2026 trial QA pushed
    to the website's real holdouts repo with `git push`, which the gh stand-in never sees."""
    env = {k: v for k, v in os.environ.items() if k not in SECRETS and not k.startswith("GIT_CONFIG")}
    env.update({"PATH": f"{EVALS / 'bin'}:{env.get('PATH', '')}", "EVAL_GH_STATE": str(folder / "github.json"),
                "GH_CONFIG_DIR": str(folder / "gh-config"), "GH_PROMPT_DISABLED": "1", "TMPDIR": str(folder / "tmp"),
                "GIT_TERMINAL_PROMPT": "0"})
    env.update(PINNED)
    nowhere = (folder / "no-github").as_uri() + "/"
    config = [("credential.helper", "")] + [(f"url.{nowhere}.insteadOf", url) for url in GITHUB]
    env["GIT_CONFIG_COUNT"] = str(len(config))
    for i, (key, value) in enumerate(config):
        env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = key, value
    return env


def numbers(task):
    """The issue and PR numbers a task's trials work on. Agents name scratch paths after them
    (`/tmp/qa-pr8`), so two trials that share one must not run at once (seen on 27 Oct 2026)."""
    github = task["github"]
    return {item["number"] for item in github["issues"] + github["prs"]}


def schedule(jobs, parallel, run):
    """Run jobs `parallel` at a time, never two whose tasks share an issue or PR number, and yield
    each result as it finishes. Jobs are taken in turn across tasks, so one task's trials spread out."""
    pending, running = list(jobs), {}
    with ThreadPoolExecutor(parallel) as pool:
        while pending or running:
            busy = set().union(*(numbers(job[0]) for job in running.values()))
            for job in list(pending):
                if len(running) >= parallel:
                    break
                if not numbers(job[0]) & busy:
                    pending.remove(job)
                    running[pool.submit(run, *job)] = job
                    busy |= numbers(job[0])
            done = next(as_completed(running))
            del running[done]
            yield done.result()


def session_log(session_id):
    found = list((Path.home() / ".claude" / "projects").glob(f"*/{session_id}.jsonl"))
    return found[0] if found else None


FIXED = re.compile(r"(?<![\w$}/.-])/tmp/[\w.-]+|http\.server\s+(?!0\b)\d{2,5}\b")
# Killing by a pattern (`pkill -f "http.server 0"`) also stops every other run's process that matches.
KILLS = re.compile(r"""\b(?:pkill|killall)(?:\s+-\w+)*\s+(?:"[^"]*"|'[^']*'|[^\s;&|)]+)"""
                   r"|\bkill\b[^;&|\n]*\$\(\s*(?:pgrep|pidof)\b[^)]*\)|\b(?:pgrep|pidof)\b[^;&|\n]*\|\s*xargs\s+kill\b")


def shared(log):
    """Fixed /tmp paths, fixed ports and pattern kills the trial's agent used: things another run also has."""
    if not log:
        return []
    found, kills = set(), set()
    for record in summarise_records(log):
        found |= set(FIXED.findall(record))
        kills |= set(KILLS.findall(str((json.loads(record) or {}).get("command") or "")))
    # A mktemp template, or the random name mktemp made from it, is the agent's own.
    return sorted({f for f in found if not re.search(r"XXX|[-.][A-Za-z0-9]{6,}$|^/tmp/\.+$", f)} | kills)


def summarise_records(log):
    for line in open(log, encoding="utf-8"):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("type") == "assistant":
            for part in (record.get("message") or {}).get("content") or []:
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    yield json.dumps(part.get("input"))


def usage(session_id):
    """Calls, tokens and cost for one trial, priced by run-report across the session and its subagents."""
    log = session_log(session_id) if session_id else None
    rows = summarise(log).values() if log else []
    totals = {key: sum(row[key] for row in rows) for key in ("calls", "new", "cached", "out", "cost")}
    return {**totals, "log": str(log) if log else ""}


def run_trial(task, call, model, folder):
    trial.make(task, folder)
    (folder / "tmp").mkdir()
    started = time.time()
    try:
        done = subprocess.run(command(call, model), cwd=folder / "work", env=environment(folder),
                              capture_output=True, text=True, timeout=TIMEOUT)
        result = json.loads(done.stdout or "{}")
        error = "" if done.returncode == 0 else (result.get("result") or done.stderr.strip())[:300]
    except subprocess.TimeoutExpired:
        result, error = {}, f"timed out after {TIMEOUT // 60} minutes"
    except ValueError:
        result, error = {}, f"claude printed no JSON: {done.stderr.strip()[:300]}"
    output, extracted, extra = result.get("structured_output"), False, {}
    if output is None and result.get("result"):
        output = returned(result["result"], call["schema"])
        if output is None:
            output, session = extract(result["result"], call["schema"], environment(folder))
            extracted, extra = True, usage(session)
    (folder / "output.json").write_text(json.dumps(output))
    checks = trial.grade(task, folder)
    if error:
        checks.insert(0, (f"the agent finished ({error})", False))
    return {"task": task["name"], "role": task["role"], "model": model, "kind": task["kind"],
            "passed": all(ok for _, ok in checks), "checks": checks, "minutes": (time.time() - started) / 60,
            "session": result.get("session_id", ""), "folder": str(folder), "extracted": extracted,
            "shared": shared(session_log(result.get("session_id")) if result.get("session_id") else None),
            **add(usage(result.get("session_id")), extra)}


def add(spent, extra):
    return {**spent, **{key: spent[key] + extra.get(key, 0) for key in ("calls", "new", "cached", "out", "cost")}}


def summary(results):
    """Per role and model: pass rate over trials, pass^k over tasks, and tokens and cost."""
    by_task = defaultdict(list)
    for r in results:
        by_task[(r["role"], r["model"], r["task"])].append(r)
    groups = defaultdict(lambda: {"tasks": 0, "all_passed": 0, "trials": 0, "passed": 0, "cost": 0.0,
                                  "new": 0, "cached": 0, "out": 0, "kinds": defaultdict(lambda: [0, 0])})
    for (role, model, _), trials in by_task.items():
        g = groups[(role, model)]
        g["tasks"] += 1
        g["all_passed"] += all(t["passed"] for t in trials)
        for t in trials:
            g["trials"] += 1
            g["passed"] += t["passed"]
            g["kinds"][t["kind"]][0] += t["passed"]
            g["kinds"][t["kind"]][1] += 1
            for key in ("cost", "new", "cached", "out"):
                g[key] += t[key]
    return dict(groups)


def percent(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "–"


def markdown(results, trials):
    groups = summary(results)
    total = sum(r["cost"] for r in results)
    lines = [f"**Eval run** · {len({r['task'] for r in results})} tasks · {len(results)} trials · "
             f"${total:.2f} at API prices", "",
             "| Agent | Model | Tasks | Trials each | Pass rate | pass^k | Regression | Capability | Input, new | Input, cached | Output | Cost | Cost per trial |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (role, model), g in sorted(groups.items()):
        kind = lambda k: percent(*g["kinds"][k]) if g["kinds"][k][1] else "–"
        lines.append(f"| {role} | {model} | {g['tasks']} | {g['trials'] // g['tasks']} | {percent(g['passed'], g['trials'])} | "
                     f"{percent(g['all_passed'], g['tasks'])} | {kind('regression')} | {kind('capability')} | "
                     f"{tokens(g['new'])} | {tokens(g['cached'])} | {tokens(g['out'])} | ${g['cost']:.2f} | "
                     f"${g['cost'] / g['trials']:.2f} |")
    all_tasks = defaultdict(list)
    for r in results:
        all_tasks[(r["task"], r["model"])].append(r)
    passed = sum(r["passed"] for r in results)
    every = sum(all(t["passed"] for t in ts) for ts in all_tasks.values())
    lines.append(f"| **All** | | {len(all_tasks)} | | {percent(passed, len(results))} | {percent(every, len(all_tasks))} | | | "
                 f"{tokens(sum(r['new'] for r in results))} | {tokens(sum(r['cached'] for r in results))} | "
                 f"{tokens(sum(r['out'] for r in results))} | **${total:.2f}** | ${total / max(len(results), 1):.2f} |")
    lines += ["", "| Task | Agent | Model | Kind | Trials | What failed | Cost |", "|---|---|---|---|---|---|---|"]
    for (name, model), ts in sorted(all_tasks.items()):
        marks = " ".join("✓" if t["passed"] else "✗" for t in ts)
        failed = sorted({c for t in ts for c, ok in t["checks"] if not ok})
        lines.append(f"| {name} | {ts[0]['role']} | {model} | {ts[0]['kind']} | {marks} | "
                     f"{'; '.join(failed)[:300] or '–'} | ${sum(t['cost'] for t in ts):.2f} |")
    extracted = sum(r.get("extracted", False) for r in results)
    if extracted:
        lines += ["", f"In {extracted} of {len(results)} trials the agent's reply had no usable JSON block, so Haiku "
                      "read the result from its final report."]
    for what, kill in (("used a fixed /tmp path or port another run could also use", False),
                       ("stopped a process by a pattern another run's process could also match", True)):
        used = [[p for p in r.get("shared") or [] if bool(KILLS.fullmatch(p)) == kill] for r in results]
        if any(used):
            common = defaultdict(int)
            for places in used:
                for place in places:
                    common[place] += 1
            top = ", ".join(f"`{p}`" for p, _ in sorted(common.items(), key=lambda kv: -kv[1])[:5])
            lines += ["", f"{sum(map(bool, used))} of {len(results)} trials {what}: {top}."]
    lines += ["", "Pass rate is the share of trials that passed every check; pass^k is the share of tasks "
                  "where all k trials passed. Regression tasks are ones the team got right on the website "
                  "and should stay near 100%; capability tasks are ones it got wrong. Cost is API-equivalent at "
                  "list prices, from `run-report`; on a Pro or Max plan the run uses the weekly limit instead."]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--task", action="append", default=[], help="a task's name or number prefix; repeat for more")
    parser.add_argument("--role", action="append", default=[], help="only this agent's tasks, e.g. builder or build-check")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--model", action="append", default=[], help="role=model, to run a role on another model; repeat to run it on several")
    parser.add_argument("--trials-for", action="append", default=[], help="role=n, to give one role more trials, e.g. for a model comparison")
    parser.add_argument("--parallel", type=int, default=4, help="trials at once")
    parser.add_argument("--out", type=Path, help="where results go (default evals/runs/<time>)")
    parser.add_argument("--keep", action="store_true", help="keep each trial's folder for reading afterwards")
    parser.add_argument("--dry-run", action="store_true", help="show each task's agent, model and prompt; run nothing")
    parser.add_argument("--regrade", type=Path, help="grade a kept run's trials again, after a grader fix; run nothing")
    parser.add_argument("--report", nargs="+", type=Path, help="print one report from these runs' results.json; run nothing")
    args = parser.parse_args(argv)

    if args.regrade:
        results = json.loads(args.regrade.read_text())
        for r in results:
            checks = trial.grade(trial.load(r["task"]), r["folder"])
            r["shared"] = shared(r.get("log"))
            failed_run = [c for c in r["checks"] if c[0].startswith("the agent finished")]
            r["checks"], r["passed"] = failed_run + checks, not failed_run and all(ok for _, ok in checks)
        args.regrade.write_text(json.dumps(results, indent=2))
        args.report = [args.regrade]
    if args.report:
        results = [r for path in args.report for r in json.loads(path.read_text())]
        counts = defaultdict(int)
        for r in results:
            counts[(r["task"], r["model"])] += 1
        print(markdown(results, min(counts.values())))
        return 0

    names = [n for n in trial.tasks() if (not args.task or any(n.startswith(t) for t in args.task))]
    tasks = [t for t in map(trial.load, names) if not args.role or t["role"] in args.role]
    models = defaultdict(list)
    for m in args.model:
        role, model = m.split("=", 1)
        models[role].append(model)
    counts = {role: int(n) for role, n in (t.split("=", 1) for t in args.trials_for)}
    planned = []
    for task in tasks:
        call = capture(task)
        for model in models.get(task["role"]) or [call["model"]]:
            planned.append((task, call, model, counts.get(task["role"], args.trials)))
    if args.dry_run:
        for task, call, model, _ in planned:
            print(f"{task['name']}: {call['agentType'] or 'workflow step'} on {model}, from {task['step']['workflow']}'s "
                  f"'{call['label']}'\n  {call['prompt'][:200]!r}")
        return 0
    if not shutil.which("claude"):
        parser.error("needs the claude CLI on PATH")

    out = args.out or EVALS / "runs" / datetime.now().strftime("%Y-%m-%d-%H%M")
    out.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="founding-agents-evals-"))
    jobs = [(task, call, model, scratch / f"{task['name']}-{model}-{i + 1}")
            for i in range(max(n for *_, n in planned)) for task, call, model, n in planned if i < n]
    print(f"Running {len(jobs)} trials, {args.parallel} at a time, in {scratch}", file=sys.stderr)
    results = []
    for result in schedule(jobs, args.parallel, run_trial):
        results.append(result)
        print(f"{'pass' if result['passed'] else 'FAIL'}  {result['task']} on {result['model']}  "
              f"${result['cost']:.2f}  {result['minutes']:.0f} min", file=sys.stderr)
        (out / "results.json").write_text(json.dumps(results, indent=2))
    report = markdown(results, args.trials)
    (out / "report.md").write_text(report + "\n")
    print(report)
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
