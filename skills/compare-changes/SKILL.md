---
name: compare-changes
description: Compare the product's changes made with Founding Agents against changes made without it - cost, time to merge, and follow-up fixes within two weeks - from merged PRs and their labels. Use when the founder asks whether the plugin is worth it, or how changes with and without it compare.
---

# Compare changes with and without the plugin

Run from the product repo's folder:

- `python3 <this skill's directory>/compare.py` prints a table for each group and a row per PR.
- `--since YYYY-MM-DD` compares only changes merged since then, so runs from before a fix to the
  plugin can be left out. `--limit` sets how many recent merged PRs it reads (200 by default);
  `--repo owner/name` points it at another repo.

**Which group a PR is in.** A PR from `build`'s branch (`build/issue-<n>`) counts as with the plugin
without a label. Every other change needs one: `with-plugin` or `without-plugin` on the PR. Create
them once with `gh label create with-plugin` and `gh label create without-plugin`. A PR with
neither is left out.

**Cost** comes from the run reports posted on the PR and on the issues it closes, so a change built
with `propose` and `build` counts both. A change made without the plugin has no report unless the
founder asks for one: find its session log under `~/.claude/projects/` and run the `run-report`
skill's `report.py --session <log> --issue <PR number> --post`, which posts it on the PR.

**Fixed later** counts a later merged PR that changed one of the same files within two weeks and is
labelled `bug` or `fix` or says fix or revert in its title. That is a guess from titles and files,
so the table names each one; look at them before telling the founder what the count means. A change
merged under two weeks ago is counted apart, since a fix could still come.

Give the founder the summary table and say plainly what it shows and how many changes it rests on:
with fewer than about ten in a group, say the numbers are too few to judge by.
