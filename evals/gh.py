#!/usr/bin/env python3
"""A stand-in for `gh` in an eval trial: serves the task's issues and PRs from a JSON file and records
what the agent posts, so a trial never reaches GitHub.

It covers the calls the agents and workflows make (`gh issue`, `gh pr`, `gh repo view`), reads and
writes the state file named by `EVAL_GH_STATE`, and runs git in the current folder for `gh pr diff`
and `gh pr checkout`. Everything the agent changes is appended to the state's `posted` list, which
the graders read. Anything else fails with a message saying so, the way `gh` fails on a bad call.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

STATE = Path(os.environ.get("EVAL_GH_STATE", "github.json"))


def load():
    state = json.loads(STATE.read_text())
    state.setdefault("issues", [])
    state.setdefault("prs", [])
    state.setdefault("posted", [])
    return state


def save(state):
    STATE.write_text(json.dumps(state, indent=2))


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def options(argv, flags=()):
    """Positional args, and each --option's values; `flags` take no value."""
    positional, named = [], {}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("-") and arg != "-":
            key, _, value = arg.partition("=")
            key = key.lstrip("-")
            if key in flags:
                named.setdefault(key, []).append(True)
            else:
                if not value:
                    i += 1
                    value = argv[i] if i < len(argv) else ""
                named.setdefault(key, []).append(value)
        else:
            positional.append(arg)
        i += 1
    return positional, named


ALIASES = {"b": "body", "F": "body-file", "t": "title", "l": "label", "q": "jq", "s": "state", "R": "repo",
           "H": "head", "B": "base", "L": "limit", "S": "search", "c": "comments"}
FLAGS = {"comments", "c", "approve", "request-changes", "comment", "squash", "merge", "rebase", "delete-branch", "d",
         "auto", "admin", "web", "w", "fill", "f", "draft", "name-only", "patch", "force"}


def parse(argv):
    positional, named = options(argv, FLAGS)
    return positional, {ALIASES.get(k, k): v for k, v in named.items()}


def one(named, key, default=None):
    return named[key][-1] if key in named else default


def body_of(named):
    if "body-file" in named:
        source = one(named, "body-file")
        return sys.stdin.read() if source == "-" else Path(source).read_text()
    return one(named, "body", "")


def url(state, kind, number):
    return f"https://github.com/{state['repo']}/{'pull' if kind == 'pr' else 'issues'}/{number}"


def comment_json(comment):
    return {"author": {"login": comment.get("author", "todd450")}, "body": comment["body"],
            "createdAt": comment.get("createdAt", "2026-10-26T12:00:00Z")}


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def item_json(state, kind, item):
    full = {
        "number": item["number"], "title": item["title"], "body": item.get("body", ""),
        "state": item.get("state", "OPEN"), "url": url(state, kind, item["number"]),
        "author": {"login": item.get("author", "todd450")},
        "labels": [{"name": name} for name in item.get("labels", [])],
        "comments": [comment_json(c) for c in item.get("comments", [])],
        "createdAt": item.get("createdAt", "2026-10-26T09:00:00Z"),
    }
    if kind == "pr":
        names = git("diff", "--name-only", f"{item.get('baseRefName', 'main')}...{item['headRefName']}").stdout.split()
        full.update({
            "headRefName": item["headRefName"], "baseRefName": item.get("baseRefName", "main"),
            "isDraft": False, "mergeable": "MERGEABLE", "reviewDecision": "",
            "reviews": item.get("reviews", []), "statusCheckRollup": item.get("checks", []),
            "files": [{"path": name} for name in names], "closingIssuesReferences": [
                {"number": int(n)} for n in re.findall(r"(?i)(?:closes|fixes) #(\d+)", item.get("body", ""))],
        })
    return full


def output(state, kind, data, named):
    fields = one(named, "json")
    if fields is None:
        return False
    keep = lambda d: {k: v for k, v in d.items() if k in fields.split(",")} if fields else d
    shaped = [keep(item_json(state, kind, d)) for d in data] if isinstance(data, list) else keep(item_json(state, kind, data))
    text = json.dumps(shaped)
    if "jq" in named:
        result = subprocess.run(["jq", "-r", one(named, "jq")], input=text, capture_output=True, text=True)
        if result.returncode:
            fail(result.stderr.strip())
        text = result.stdout.rstrip("\n")
    print(text)
    return True


def find(state, kind, number):
    number = int(str(number).lstrip("#").rsplit("/", 1)[-1])
    items = state["prs" if kind == "pr" else "issues"]
    match = next((i for i in items if i["number"] == number), None)
    if not match and kind == "issue":  # gh issue view also finds PRs by number
        match = next((i for i in state["prs"] if i["number"] == number), None)
    if not match:
        fail(f"GraphQL: Could not resolve to an issue or pull request with the number of {number}.")
    return match


def next_number(state):
    return max([i["number"] for i in state["issues"] + state["prs"]] or [0]) + 1


def matches(item, named):
    wanted_state = (one(named, "state", "open") or "open").upper()
    if wanted_state != "ALL" and item.get("state", "OPEN") != wanted_state:
        return False
    for label in named.get("label", []):
        if label not in item.get("labels", []):
            return False
    if "head" in named and item.get("headRefName") != one(named, "head"):
        return False
    search = one(named, "search")
    if search:
        phrases = re.findall(r'"([^"]+)"', search) or [re.sub(r"\bin:\w+|\bis:\w+", "", search).strip()]
        text = item.get("body", "") + " " + item["title"]
        if not all(p.lower() in text.lower() for p in phrases if p):
            return False
    return True


def show(state, kind, item, named):
    if output(state, kind, item, named):
        return
    labels = ", ".join(item.get("labels", []))
    print(f"title:\t{item['title']}\nstate:\t{item.get('state', 'OPEN')}\nlabels:\t{labels}\nnumber:\t{item['number']}")
    if kind == "pr":
        print(f"head:\t{item['headRefName']}")
    print(f"--\n{item.get('body', '')}")
    if "comments" in named or kind == "pr":
        for c in item.get("comments", []):
            print(f"--\nauthor:\t{c.get('author', 'todd450')}\n--\n{c['body']}")


def record(state, event):
    state["posted"].append(event)
    save(state)


def issue(state, verb, rest):
    positional, named = parse(rest)
    if verb == "view":
        return show(state, "issue", find(state, "issue", positional[0]), named)
    if verb == "list":
        found = [i for i in state["issues"] if matches(i, named)]
        if not output(state, "issue", found, named):
            for i in found:
                print(f"{i['number']}\t{i.get('state', 'OPEN')}\t{i['title']}")
        return
    if verb == "comment":
        target = find(state, "issue", positional[0])
        text = body_of(named)
        target.setdefault("comments", []).append({"author": "todd450", "body": text})
        record(state, {"kind": "issue comment", "number": target["number"], "body": text})
        return print(url(state, "issue", target["number"]) + "#issuecomment-1")
    if verb == "create":
        number = next_number(state)
        new = {"number": number, "title": one(named, "title", ""), "body": body_of(named),
               "labels": named.get("label", []), "comments": []}
        state["issues"].append(new)
        record(state, {"kind": "issue create", **new})
        return print(url(state, "issue", number))
    if verb == "edit":
        target = find(state, "issue", positional[0])
        change = {"kind": "issue edit", "number": target["number"]}
        if "body" in named or "body-file" in named:
            target["body"] = change["body"] = body_of(named)
        if "title" in named:
            target["title"] = change["title"] = one(named, "title")
        for label in sum((v.split(",") for v in named.get("add-label", [])), []):
            target.setdefault("labels", []).append(label)
            change.setdefault("add_labels", []).append(label)
        for label in sum((v.split(",") for v in named.get("remove-label", [])), []):
            target["labels"] = [l for l in target.get("labels", []) if l != label]
            change.setdefault("remove_labels", []).append(label)
        record(state, change)
        return print(url(state, "issue", target["number"]))
    if verb in ("close", "reopen"):
        target = find(state, "issue", positional[0])
        target["state"] = "CLOSED" if verb == "close" else "OPEN"
        return record(state, {"kind": f"issue {verb}", "number": target["number"]})
    fail(f"gh issue {verb} is not available in this eval")


def pr(state, verb, rest):
    positional, named = parse(rest)
    if verb == "list":
        found = [p for p in state["prs"] if matches(p, named)]
        if not output(state, "pr", found, named):
            for p in found:
                print(f"{p['number']}\t{p['title']}\t{p['headRefName']}\t{p.get('state', 'OPEN')}")
        return
    if verb == "create":
        head = one(named, "head") or git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        number = next_number(state)
        new = {"number": number, "title": one(named, "title", ""), "body": body_of(named), "headRefName": head,
               "baseRefName": one(named, "base", "main"), "comments": [], "state": "OPEN"}
        state["prs"].append(new)
        record(state, {"kind": "pr create", **new})
        return print(url(state, "pr", number))
    target = find(state, "pr", positional[0]) if positional else next(
        (p for p in state["prs"] if p["headRefName"] == git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()), None)
    if not target:
        fail("no pull requests found for the current branch")
    if verb == "view":
        return show(state, "pr", target, named)
    if verb == "diff":
        args = ["diff", f"{target.get('baseRefName', 'main')}...{target['headRefName']}"]
        if "name-only" in named:
            args.insert(1, "--name-only")
        git("fetch", "-q", "origin")
        result = git(*args)
        if result.returncode:
            result = git(args[0], *args[1:-1], f"origin/{target.get('baseRefName', 'main')}...origin/{target['headRefName']}")
        return print(result.stdout, end="")
    if verb == "checkout":
        git("fetch", "-q", "origin")
        branch = target["headRefName"]
        result = git("checkout", branch)
        if result.returncode:
            result = git("checkout", "-b", branch, f"origin/{branch}")
        if result.returncode:
            fail(result.stderr.strip())
        git("pull", "-q", "--ff-only", "origin", branch)
        return print(f"Switched to branch '{branch}'")
    if verb in ("comment", "review"):
        text = body_of(named)
        if verb == "review":
            verdict = "approve" if "approve" in named else "request-changes" if "request-changes" in named else "comment"
            text = f"[{verdict}] {text}"
        target.setdefault("comments", []).append({"author": "todd450", "body": text})
        record(state, {"kind": f"pr {verb}", "number": target["number"], "body": text})
        return print(url(state, "pr", target["number"]) + "#issuecomment-1")
    if verb == "merge":
        target["state"] = "MERGED"
        record(state, {"kind": "pr merge", "number": target["number"], "args": rest})
        return print(f"Merged pull request #{target['number']}")
    if verb == "checks":
        return print("no checks reported on the '{}' branch".format(target["headRefName"]))
    if verb == "edit":
        if "body" in named or "body-file" in named:
            target["body"] = body_of(named)
        return record(state, {"kind": "pr edit", "number": target["number"], "body": target.get("body", "")})
    if verb == "close":
        target["state"] = "CLOSED"
        return record(state, {"kind": "pr close", "number": target["number"]})
    fail(f"gh pr {verb} is not available in this eval")


def repo(state, verb, rest):
    if verb != "view":
        fail(f"gh repo {verb} is not available in this eval")
    _, named = parse(rest)
    owner, name = state["repo"].split("/")
    full = {"nameWithOwner": state["repo"], "owner": {"login": owner}, "name": name, "url": f"https://github.com/{state['repo']}",
            "defaultBranchRef": {"name": "main"}}
    fields = one(named, "json")
    if fields is None:
        return print(f"name:\t{state['repo']}\n--\n{state.get('description', '')}")
    text = json.dumps({k: v for k, v in full.items() if k in fields.split(",")} if fields else full)
    if "jq" in named:
        text = subprocess.run(["jq", "-r", one(named, "jq")], input=text, capture_output=True, text=True).stdout.rstrip("\n")
    print(text)


def main(argv):
    if not argv:
        fail("usage: gh <command> <subcommand>")
    if argv[0] == "auth":
        return print("Logged in to github.com (eval stand-in)")
    state = load()
    commands = {"issue": issue, "pr": pr, "repo": repo}
    if argv[0] not in commands or len(argv) < 2:
        fail(f"gh {' '.join(argv[:2])} is not available in this eval; use gh issue, gh pr or gh repo view")
    commands[argv[0]](state, argv[1], argv[2:])


if __name__ == "__main__":
    main(sys.argv[1:])
