import json
import re


def grade(t):
    decisions = json.dumps(t.output["decisions"])
    yield "names at least two technical decisions", len(t.output["decisions"]) >= 2
    yield "names the generator, framework or build step", re.search(r"generator|framework|build|astro|eleventy|hugo|tailwind", decisions, re.I)
    yield "names the host", re.search(r"host|deploy|vercel|netlify|pages|cloudflare", decisions, re.I)
    edits = [e for e in t.posted("issue edit") if e["number"] == 21 and e.get("body")]
    yield "wrote the brief into #21 with a Technical decisions section", edits and "technical decisions" in edits[-1]["body"].lower()
    yield "did not mark it decided", not any("decided" in e.get("add_labels", []) for e in t.posted("issue edit"))
    yield "changed no code", not t.moved()
