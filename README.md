# Founding Agents

A reusable team of Claude Code agents that builds products alongside one founder. The founder
decides scope and taste and talks to users; the agents plan, build, check, ship and watch.

**Status:** steps 1 to 4 of the build order are done, running on the first product, the
[Founding Agents website](https://todd450.github.io/founding-agents-site/): the merge guard, a
`setup` skill that turns on branch protection and installs ops watch's nightly site check,
`/founding-agents:propose`, which turns an idea into a brief and mockups for the founder to decide,
and `/founding-agents:build`, which built the site's page through four decided issues. Step 5,
growing the team on demand, is next.

- [docs/design.md](docs/design.md) — the team, how a change flows, the principles behind it, the
  decisions and the build order.

To try it in a product, from Claude Code:

```
/plugin marketplace add todd450/founding-agents
/plugin install founding-agents@founding-agents
```

Then ask Claude to run the `setup` skill in the product's repo. The merge guard needs `python3`.

The design comes from five months of building one product with agent sessions (June–October 2026)
and from what published agent teams at Cursor, Anthropic and OpenAI reported by October 2026.
