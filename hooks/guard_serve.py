#!/usr/bin/env python3
"""PreToolUse hook: a local preview binds to this machine and serves no secret.

`python3 -m http.server` listens on every network the machine is on unless it is given `--bind`,
and it serves every file in its folder, dotfiles too. On Half Badger (27 Oct 2026) the issues told
agents to run it unbound from `site/`, which held a Vercel token. So a Bash command that starts it
without binding to a loopback address, or from a folder holding a secret, is blocked with how to
fix it. Like the other guards this is best-effort parsing of shell commands.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
SEGMENT_BREAKS = re.compile(r"&&|\|\||[;|\n]")
# Files a static server would hand to anyone who asks for them by name.
# An example file (`.env.example`) holds none and is meant to be shared.
SECRET = re.compile(r"^(?!.*\.(example|sample|template)$)(\.env(\..*)?|\.vercel|\.netlify|.*\.pem|.*\.key|id_rsa.*|id_ed25519.*)$")
SKIP = {".git", "node_modules"}


def secrets(folder, depth=3):
    """Secret files under the folder, a few levels down, as paths relative to it."""
    found = []
    try:
        entries = sorted(os.scandir(folder), key=lambda e: e.name)
    except OSError:
        return found
    for entry in entries:
        if SECRET.match(entry.name):
            found.append(entry.name)
        elif entry.is_dir(follow_symlinks=False) and entry.name not in SKIP and depth > 1:
            found += [f"{entry.name}/{inner}" for inner in secrets(entry.path, depth - 1)]
    return found


def servers(command, cwd):
    """For each `python -m http.server` in the command: its bind address (None when unbound) and
    the folder it serves."""
    for segment in SEGMENT_BREAKS.split(command):
        try:
            words = shlex.split(segment.strip().lstrip("("), comments=True)
        except ValueError:
            words = segment.split()
        words = [w for w in words if w not in (")", "&")]
        if words[:1] == ["cd"] and len(words) > 1:
            cwd = os.path.join(cwd, os.path.expanduser(words[1]))
            continue
        for i in range(len(words) - 1):
            if words[i:i + 2] == ["-m", "http.server"] and any(Path(w).name.startswith("python") for w in words[:i]):
                bind, folder, rest = None, cwd, words[i + 2:]
                for j, arg in enumerate(rest):
                    value = rest[j + 1] if j + 1 < len(rest) else ""
                    if arg in ("-b", "--bind"):
                        bind = value
                    elif arg.startswith("--bind="):
                        bind = arg.split("=", 1)[1]
                    elif arg in ("-d", "--directory"):
                        folder = os.path.join(cwd, os.path.expanduser(value))
                    elif arg.startswith("--directory="):
                        folder = os.path.join(cwd, os.path.expanduser(arg.split("=", 1)[1]))
                yield bind, folder


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if "http.server" not in command:
        return 0

    for bind, folder in servers(command, event.get("cwd") or os.getcwd()):
        if bind not in LOOPBACK:
            print(
                "Blocked an http.server that is not bound to this machine. Without --bind it listens on "
                "every network this computer is on and serves every file in its folder, dotfiles too. "
                "Run it as `python3 -m http.server 0 --bind 127.0.0.1` (0 picks a free port).",
                file=sys.stderr,
            )
            return 2
        found = secrets(folder)
        if found:
            print(
                f"Blocked an http.server on {folder}: it would serve {', '.join(found[:5])}, which can hold "
                "secrets. Serve a folder that holds none (`--directory <web root>`, or a copy of the "
                "pages), or ask the founder to move the secret out of the folder the product is served from.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
