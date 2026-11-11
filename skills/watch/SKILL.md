---
name: watch
description: Show what the agents of a Founding Agents build or propose run did, as a page with a timeline of the run, a close-up of each agent's steps, waits and failures, and a live board of who is working now. Use when the founder asks to watch a run, see what the agents are doing or did, or find out where a run's time went or why an agent was slow.
---

# Watch a run

Claude Code keeps a record of every workflow run on the machine it ran on, one file per agent.
`watch.py` reads that record and writes a page from it, so watching costs no tokens and no agent
reports anything. Run it from the product repo's folder:

- `python3 <this skill's directory>/watch.py --open` writes the page for the newest run and opens
  it. It prints the page's path; without `--open` it only writes it.
- `--list` prints the recorded runs, newest first; `--run <id>` picks one of them.
- `--live --open` serves a board of the run going on now, which reads the record every three
  seconds. Start it in the background before or during a run and stop it when the run ends. It
  listens on this machine only and answers two addresses, the page and the run's data; it serves
  no file.

What the page shows:

- **Timeline:** a bar for each agent, in rows by role under the workflow's phases, so a change
  sent back shows as the builder's and the reviewer's bars repeating. Agents still working are
  paler.
- **Close-up:** click a bar. What the agent was told (its first 200 characters), each step placed
  in time, its longest waits and its failed steps.
- **Working now** (live only): each working agent's last step and how long it has run. An agent
  with no new step for two minutes is marked quiet, which is usually a wait on a browser or a
  server that has stalled.

The page shows each step's kind, the short description the agent gave it and whether it failed. It
never shows a command or its output, which can hold a secret. To read those, open the agent's own
record, which the run's folder holds.

Tell the founder what the page shows that is worth acting on: a role that took most of the run, a
long wait, a step that failed again and again.

A run on another machine, or in the cloud, left no record here and cannot be watched.
