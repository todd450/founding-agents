# Every sweep

The rules every Founding Agents sweep follows, whatever its kind. Each kind's file in this folder
(`architecture.md`, `design.md`, `security.md`, `codebase.md`, `tests.md`) names its kind, points
here, and adds what to read, what to look for and its pass marks.

## Reaching GitHub

A sweep may run as a cloud routine, where GitHub's GraphQL API is blocked, so `gh issue` and `gh pr`
fail there. Use the REST API through `gh api` for everything, wherever you run, and take
`<owner>/<repo>` from `git remote get-url origin`. Only this repo's own REST paths work in the
cloud: anything outside `repos/<owner>/<repo>/`, such as `search/`, gets a 403, and so does
fetching the live site.

- Open `red` issues: `gh api "repos/<owner>/<repo>/issues?labels=red&state=open"`
- Pull requests closed lately, newest first: `gh api "repos/<owner>/<repo>/pulls?state=closed&sort=updated&direction=desc&per_page=50"`
- A pull request's files: `gh api repos/<owner>/<repo>/pulls/<n>/files`
- Every issue and pull request, to find one by its title: `gh api --paginate "repos/<owner>/<repo>/issues?state=all&per_page=100"`
- An issue's comments: `gh api repos/<owner>/<repo>/issues/<n>/comments`
- Whether the repo is private: `gh api repos/<owner>/<repo> --jq .private`
- Open an issue: `gh api -X POST repos/<owner>/<repo>/issues -f title=... -f body=... -f "labels[]=needs-founder"`

## How every sweep runs

- **A red issue stops the run.** If a `red` issue is open, file nothing: a red scheduled check
  stops other work until it is fixed. Say so in your last line and stop.
- **Read only, apart from issues.** Never commit, push, or change settings or workflows: a fix is
  built through the team's own `build`, like any change. Undo any edit you make to try something
  before you finish.
- **Run the product only on this machine.** Serve it bound to `127.0.0.1`
  (`python3 -m http.server 0 --bind 127.0.0.1`, or the product's own command with its host set to
  `127.0.0.1`), never from a folder that holds a secret (`.env*`, `.vercel/`, a key). Never
  attack, load or measure the live product.
- **A decision already made is never a finding.** Each decided issue's "Technical decisions"
  section and the founder's answers in its comments say what the founder chose.
- **At most three findings a run,** the most worth fixing first, ranked by what fixing it saves
  against what it costs. Fewer is fine, and a quiet run files nothing. Only what the product needs
  now: no finding for a need nobody has yet, and no list of ideas for later.
- **Each finding is one issue** titled `Sweep (<kind>): <the finding in a few words>`, with this
  sweep's kind, and labelled `needs-founder`. Look for one with the same title among every issue,
  open or closed, first: never file a finding twice, and a closed one means the founder said no.
  Each sweep keeps to its own issues and leaves the other kinds' alone.
- **Each issue says, in plain English for someone who does not read code,** unless the kind's file
  keeps the details private: what is wrong and where (files and lines), the evidence, the fix, how
  long it takes, and what leaving it costs. Then a `### Pass marks` section: what the reviewer
  checks to call the fix done, each one checkable before the merge from the branch, a server bound
  to `127.0.0.1` and `gh`, with no dashboard, login or account. Then a `### Technical decisions`
  section. Where the fix would settle a technical one-way door: a choice that costs a lot to reverse
  once code or people depend on it, such as using a framework or none, adding a build step, how the
  product deploys or is hosted, its language or stack, where and how it stores data, a dependency
  that ships to users, an outside service, or an interface other code or people rely on, name each
  one there with the realistic options, the one you recommend and why, and what reversing it later
  would cost. Write "None." there when it settles none, as most fixes do. The founder adds `decided`
  to the ones to build, and `/founding-agents:build <number>` builds each.

End with one line per finding: the issue filed, or why it needed none. Then one line on what you
measured or ran, and one on what you did not get to.
