# Evals

Tasks that test how the team's agents behave, not how the workflows are wired. Each comes from a
real run on the website ([todd450/founding-agents-site](https://github.com/todd450/founding-agents-site))
and tests one failure class. The method is Anthropic's
[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).

```bash
python3 evals/run.py
```

That runs every task three times on your plan and prints, per agent and model, the pass rate, pass^3
(the share of tasks where all three trials passed), and tokens and cost. `--role builder` runs one
agent's tasks; `--model builder=sonnet` runs them on another model; `--task 09` runs one task;
`--dry-run` shows each task's step and runs nothing; `--keep` keeps each trial's folder to read.

A change that alters an agent, skill or workflow, or a model choice, runs the tasks of the roles it
touches before its version bump, one trial each, all at once: for a change to the reviewers,
`python3 evals/run.py --role code-reviewer --role qa --trials 1`, about a quarter of an hour, since
the wait is the slowest trial. A model change adds `--model <role>=<model>` for the role it moves.
The full run, every task three times, goes before a release, off a PR's path: one trial shows a change
did not break an agent, three tell a reliable one from a lucky one (`docs/design.md` says why).

## How a trial runs

1. `run.py` runs the task's workflow under `tests/workflow_harness.py`, with scripted replies up to
   the task's step, and takes the prompt, agent, model and schema that step gets. A prompt changed
   in `workflows/` is the prompt the eval tests.
2. `trial.py` builds a throwaway repo from the task's commits, with a local `origin`, and the
   issues and PRs the [`gh` stand-in](gh.py) serves. `evals/bin` comes first on PATH, the trial
   gets an empty GitHub login, and git sends every GitHub address to a folder that does not exist,
   with no saved login, so nothing reaches GitHub. The trial keeps the founder's home folder, where
   the plan's login lives, so a hook ([`fence.py`](fence.py)) stops every agent naming the
   machine's real holdouts: a trial runs as if holdouts were not set up.
3. `claude -p` runs the prompt as the step's agent (`--agent`, `--plugin-dir` this repo, project
   settings only, so other plugins stay out). A session started with `--agent` gets only its agent
   file's tools and cannot return structured output, so an agent step is asked to end its reply
   with a JSON block; if that fails, Haiku reads the result from the reply, and the report counts
   how often.
4. The task's `grade.py` checks the outcome: what the agent returned, what it posted, and the
   branches it pushed, running the product's checks where the task needs them.
5. Tokens and cost come from the session logs, priced by `skills/run-report`.

## A task

```
tasks/<nn-name>/
  task.json        role, kind, failure class, where it came from, the right answer,
                   the workflow step, the commits that build the repo, the issues and PRs
  grade.py         grade(t) yields (check, passed); a trial passes when every check does
  reference/       an answer that passes, as an agent would leave it
  bad/             an answer that fails, the website's own mistake where there was one
  <folders>        files the commits copy in; @name means fixtures/<name>
```

`kind` is `regression` when the team got it right on the website or its instructions say so
plainly: these should pass nearly every time, and a drop means a change broke something.
`capability` is a failure from the website: these start low and show whether a change helps. A
capability task that passes every run for a few weeks becomes a regression task. Some tasks want a
stop, a refusal or an approval, so a role that sends everything back does not score well.

`tests/test_evals.py` checks every grader both ways (the reference passes, the bad answer fails),
that each PR under review passes its own checks, and the runner's sums, all without a model.

## Adding a task

Take it from a real run: an incident, a stall, a finding sent back twice, a miss found after merge.
Write the smallest repo that shows it, a grader that checks the outcome rather than the wording,
and both answers. Read the transcripts of the first trials: a failure should be the agent's, not
the grader's. Grade with a script; a model grader comes only where a script cannot judge, and only
once it agrees with the founder's own marks on a sample.
