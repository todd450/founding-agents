"""Sets up one eval trial from a task, and grades what the agent left behind.

A trial is a folder holding `work/` (the product repo the agent runs in), `origin.git` (its remote,
so pushes stay on this machine), `github.json` (the issues and PRs the `gh` stand-in serves, and
what the agent posted) and `gh-config/` (an empty login, so the real `gh` cannot reach GitHub).
"""

import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parent
TASKS = EVALS / "tasks"
FIXTURES = EVALS / "fixtures"
GIT_ENV = {"GIT_AUTHOR_NAME": "Founder", "GIT_AUTHOR_EMAIL": "founder@example.com", "GIT_COMMITTER_NAME": "Founder",
           "GIT_COMMITTER_EMAIL": "founder@example.com", "GIT_AUTHOR_DATE": "2026-10-26T09:00:00Z",
           "GIT_COMMITTER_DATE": "2026-10-26T09:00:00Z", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
           "HOME": tempfile.gettempdir(), "GIT_CONFIG_NOSYSTEM": "1"}


def tasks():
    return sorted(p.parent.name for p in TASKS.glob("*/task.json"))


def load(name):
    folder = TASKS / name
    task = json.loads((folder / "task.json").read_text())
    return {**task, "name": name, "dir": folder}


def git(cwd, *args, check=True):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=GIT_ENV)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def source(task_dir, name):
    return FIXTURES / name[1:] if name.startswith("@") else task_dir / name


def commit(work, task_dir, step):
    """Commit a list of folders' files on a branch, creating it from `from` (default main) if new."""
    branch = step["branch"]
    if git(work, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False).strip():
        git(work, "checkout", "-q", branch)
    elif git(work, "rev-parse", "--verify", "--quiet", "HEAD", check=False).strip():
        git(work, "checkout", "-q", "-b", branch, step.get("from", "main"))
    for name in step.get("dirs", []):
        shutil.copytree(source(task_dir, name), work, dirs_exist_ok=True)
    for path in step.get("delete", []):
        (work / path).unlink()
    git(work, "add", "-A")
    git(work, "commit", "-q", "--allow-empty", "-m", step.get("message", "Change"))


def make(task, folder):
    """Build a fresh trial for `task` in `folder` and return the path of its product repo."""
    folder = Path(folder)
    work, origin = folder / "work", folder / "origin.git"
    work.mkdir(parents=True)
    (folder / "gh-config").mkdir()
    git(folder, "init", "-q", "--bare", "-b", "main", str(origin))
    git(work, "init", "-q", "-b", "main")
    for step in task["commits"]:
        commit(work, task["dir"], step)
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "--all", "origin")
    git(work, "checkout", "-q", "main")
    git(work, "branch", "-q", "--set-upstream-to=origin/main", "main")
    (folder / "github.json").write_text(json.dumps({"posted": [], **task["github"]}, indent=2))
    (folder / "start.json").write_text(json.dumps(tips(origin)))
    return work


def tips(origin):
    """Each branch at origin and the commit it points to."""
    lines = git(origin, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads").split("\n")
    return dict(line.split() for line in lines if line)


def apply(task, folder, answer):
    """Play a scripted answer into a trial, as an agent would have: its commits, posts and output."""
    folder = Path(folder)
    work = folder / "work"
    for step in answer.get("commits", []):
        commit(work, task["dir"], step)
        git(work, "push", "-q", "origin", step["branch"])
    git(work, "checkout", "-q", "main")
    state = json.loads((folder / "github.json").read_text())
    for event in answer.get("posted", []):
        state["posted"].append(event)
        if event["kind"] == "pr create":
            state["prs"].append({k: v for k, v in event.items() if k != "kind"})
    (folder / "github.json").write_text(json.dumps(state, indent=2))
    (folder / "output.json").write_text(json.dumps(answer.get("output")))


class Trial:
    """What a grader sees: the agent's returned output, what it posted, and the repo it left."""

    def __init__(self, task, folder):
        self.task, self.folder = task, Path(folder)
        self.work, self.origin = self.folder / "work", self.folder / "origin.git"
        out = self.folder / "output.json"
        self.output = json.loads(out.read_text()) if out.exists() else None
        self.output = self.output or {}
        self.state = json.loads((self.folder / "github.json").read_text())

    def posted(self, kind=None):
        return [e for e in self.state["posted"] if kind is None or e["kind"] == kind]

    def findings(self, pattern=".", must_fix=None, repeat=None):
        """The returned findings whose text matches `pattern`, and whose flags match when given."""
        found = []
        for f in self.output.get("findings", []):
            if must_fix is not None and bool(f.get("must_fix")) != must_fix:
                continue
            if repeat is not None and bool(f.get("repeat")) != repeat:
                continue
            if re.search(pattern, f"{f.get('where', '')} {f.get('what', '')}", re.I | re.S):
                found.append(f)
        return found

    def says(self, pattern, *fields):
        """Whether any of the output's text fields (all of them when none named) match `pattern`."""
        values = [self.output.get(k) for k in fields] if fields else list(self.output.values())
        return bool(re.search(pattern, json.dumps(values), re.I | re.S))

    def branch(self, name):
        """A fresh checkout of a branch as it is at origin, or None when origin has no such branch."""
        if not git(self.origin, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}", check=False).strip():
            return None
        target = Path(tempfile.mkdtemp(dir=self.folder, prefix="check-"))
        git(self.folder, "clone", "-q", "-b", name, str(self.origin), str(target))
        return target

    def show(self, ref, path):
        """A file as it is on a branch at origin."""
        return git(self.origin, "show", f"{ref}:{path}")

    def moved(self):
        """The branches at origin the agent created or moved."""
        start = json.loads((self.folder / "start.json").read_text())
        return sorted(b for b, sha in tips(self.origin).items() if start.get(b) != sha)

    def commits(self, branch, base="main"):
        return git(self.origin, "rev-list", f"{base}..{branch}", check=False).split()

    def suite(self, checkout, overlay=None):
        """Run the product's checks in a checkout, after writing `overlay` ({path: text}) over it."""
        for path, text in (overlay or {}).items():
            (checkout / path).write_text(text)
        result = subprocess.run(["sh", "check.sh"], cwd=checkout, capture_output=True, text=True, timeout=300)
        return result.returncode == 0


def grade(task, folder):
    """Each of the task's checks as (name, passed); the trial passes only when all of them do."""
    spec = importlib.util.spec_from_file_location(f"grade_{task['name'].replace('-', '_')}", task["dir"] / "grade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trial = Trial(task, folder)
    checks = []
    try:
        for name, passed in module.grade(trial):
            checks.append((name, bool(passed)))
    except Exception as error:  # an output missing what the grader reads fails the trial, not the run
        checks.append((f"the grader could read what the agent left ({type(error).__name__}: {error})", False))
    return checks
