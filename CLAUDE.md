# Founding Agents

A reusable team of Claude Code agents (roles, workflows, hooks, routines) that builds products with
one founder. Read [docs/design.md](docs/design.md) before changing anything; it holds the roles,
the flow and the open decisions.

- This file stays short: a map, not an encyclopedia. A lesson that must hold becomes a test, a lint
  rule or a hook; its evidence goes in `docs/`.
- Keep the design doc current when a decision is made — record the decision and why, not a
  changelog.
- The repo is the plugin: `.claude-plugin/`, `agents/`, `skills/`, `hooks/`. Run the tests with
  `python3 -m unittest discover -s tests`.
- A change that alters an agent, skill or workflow, or a model choice, runs the evals before its
  version bump: `python3 evals/run.py` (see [evals/README.md](evals/README.md)).
- Nothing here is product specific. A rule that only makes sense for one product does not
  belong in the reusable team.
