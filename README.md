# Founding Agents

A reusable team of Claude Code agents that builds products alongside one founder. The founder
decides scope and taste and talks to users; the agents plan, build, check, ship and watch.

**Status:** steps 1 to 4 of the build order are done, running on the first product, the
[Founding Agents website](https://todd450.github.io/founding-agents-site/): the merge guard, a
`setup` skill that turns on branch protection and installs ops watch's nightly site check,
`/founding-agents:propose`, which turns an idea into a brief and mockups for the founder to decide,
and `/founding-agents:build`, which has merged eight decided issues on the site. Step 5,
growing the team on demand, has begun with the architect: `/founding-agents:plan` cuts a decided
brief into build issues, asking the founder first about any technical decision the brief left
open, and `/founding-agents:build <brief>` builds them two to four at a time. Every role now
exists: edge-case QA, code and security review in `build`; ops watch, the optimiser and the
librarian as routines `setup` creates. For a sprint,
`/founding-agents:sweep codebase|tests|security` runs the optimiser (for the codebase or the
tests) or the security reviewer and puts up to five findings to the founder for `build`. On the
website, `plan` has cut its first brief into build issues, and a codebase sweep, the optimiser's
weekly numbers, a security review and the librarian have all run. Still to run on a real product:
a `tests` or `security` sweep, risk tiers and the check-back.

- [docs/design.md](docs/design.md) — the team, how a change flows, the principles behind it, the
  decisions and the build order.

To try it in a product, from Claude Code:

```
/plugin marketplace add todd450/founding-agents
/plugin install founding-agents@founding-agents
```

Then ask Claude to run the `setup` skill in the product's repo. The merge guard needs `python3`.

How much of the team a change uses depends on its size:

- **A new idea:** `/founding-agents:propose <idea>` writes the brief and mockups. Once you have
  decided, `/founding-agents:plan <brief>` cuts it into issues and `/founding-agents:build <brief>`
  builds them.
- **A small change** (a typo, a colour, a line of copy): skip `propose` and `plan`. Open an issue
  that says what to change, add the `decided` label, and run `/founding-agents:build <issue>`.
  Wording alone gets one code review, on Sonnet.
- **Smaller than that:** no Claude session merges except the integrator, yours included. Have
  Claude open a PR, then merge it yourself on GitHub once `check` passes.

The design comes from five months of building one product with agent sessions (June–October 2026)
and from what published agent teams at Cursor, Anthropic and OpenAI reported by October 2026.
