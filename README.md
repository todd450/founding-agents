# Agent Team

A reusable team of Claude Code agents that builds products alongside one founder. The founder
decides scope and taste and talks to users; the agents plan, build, check, ship and watch.

**Status:** step 1 of the build order: the plugin skeleton, the merge guard and a first `setup`
skill for branch protection. No team runs yet.

- [docs/design.md](docs/design.md) — the team, how a change flows, the principles behind it, the
  decisions and the build order.

To try it in a product, from Claude Code:

```
/plugin marketplace add todd450/agent-team
/plugin install agent-team@agent-team
```

Then ask Claude to run the `setup` skill in the product's repo. The merge guard needs `python3`.

The design comes from five months of building one product with agent sessions (June–October 2026)
and from what published agent teams at Cursor, Anthropic and OpenAI reported by October 2026.
