---
name: design-review
description: Review a PR's rendered screens against the design the founder picked - the chosen mockup, the storyboard's key moment and star, the founder's notes, and for a design iteration what must stay - and post the review on the PR. Use when a PR changes what someone sees and its issue, or the brief it is part of, has a mockup the founder picked, or when the founder asks for a design review of a PR.
---

# Design review

This checks that the product shows what the founder picked. Edge-case QA checks a different
thing: that the PR's screenshots show the product as it runs. Review the way the designer works
(`agents/designer.md`): the journey and the chosen star, not a pixel match. The mockup shows the
design, not code to copy.

## Find the pick

- `gh pr view <pr> --json number,title,body,headRefName,closingIssuesReferences,url` names the issue
  it builds. Read that issue with `gh issue view <n> --json title,body,labels,comments`. If its
  body starts "Part of #<m>", the mockups were made for #<m>; read that one too. Otherwise <m> is
  <n>.
- The pick is the founder's reply on the `propose` queue item: a letter, perhaps with notes, and
  the `decided` label. Where a note differs from the mockup, the note wins.
- If no mockup was picked, there is nothing to review against. Say so, and stop. That is not a
  finding.
- `git fetch origin propose/issue-<m>`, then read the spec with
  `git show origin/propose/issue-<m>:mockups/issue-<m>/storyboard.md`: the picked option, its
  stars, and the key moment it serves. Copy the picked option's `<letter>-phone.png` and
  `<letter>-desktop.png` from the same folder into a fresh `mktemp -d` folder
  (`git show <ref>:<path> > <folder>/<file>`), and look at them.
- If the issue is labelled `design`, it is a design iteration. Copy `now-phone.png` and
  `now-desktop.png` from the same folder as well, and note what the issue says is wrong and what
  must stay.

## Shoot what was built

- Never move the founder's checkout. Fetch the PR with `git fetch origin pull/<pr>/head`, and check
  it out on its own with `git worktree add --detach <folder>/pr FETCH_HEAD`.
- Serve it the way the product runs locally: on a free port bound to this machine, started in the
  background with its process ID printed in the same command
  (`python3 -u -m http.server 0 --bind 127.0.0.1 > <folder>/server.log 2>&1 & echo $!` for a
  static site; the log names its port). The shell forgets variables between commands, so write the
  folder's full path and that process ID into each later command.
- Shoot each screen the pick covers with the `mockup-screenshots` skill
  (`shoot.py --out <folder>/built <url>`), and look at every screenshot. If a screen cannot be
  served or shot, stop and return why; never build another way to take screenshots.
- Review against your own screenshots, since they show the product as it runs. The builder's after
  screenshots, on the branch `screenshots/issue-<n>`, are what the founder sees. If they show
  something other than what you shot, that is a finding.

## Compare

Put the pick next to what was built, phone first, then desktop, and check:

1. **The key moment, at the chosen star.** The built screen carries the moment the storyboard
   marked, at the star the founder picked. A build that quietly drops the part that set the option
   apart has built a cheaper option.
2. **The founder's notes** on the pick are done.
3. **A design iteration** fixes what the issue says is wrong and keeps what it says must stay, both
   judged against the `now-*` screenshots.
4. **One design language.** Colours, type and spacing come from the product's one token source.
   The only new components are ones the option named as new.
5. **Real content at phone width.** Nothing overflows, is cut off or touches the edge, with real
   content at real lengths, in every language the product ships.
6. **Trust.** What earned trust in the mockup, such as a confirmation, a saved state or who can see
   it, is still there.

A different word, a few pixels, or one of the product's existing components standing in for a
mocked one is not a departure.

## Must-fix or Nit

- **Must-fix:** something the built screen breaks that you can point to in writing: the picked
  option's spec, the founder's notes, the issue's "must stay", or the token source. A screen broken
  at phone width is must-fix too. Each one names the line it breaks.
- **Nit:** everything else, including what you would have designed differently. The founder made
  the taste call when they picked. Taste that sends a change back keeps the builder going round to
  the round limit.
- If you cannot name the line it breaks, it is a Nit.

## The review

- Post one comment on the PR with `gh pr comment <pr> --body-file -`. Start it with
  **Design: Approve** or **Design: Changes needed**, then list the findings. Each finding gives the
  screen and width, what the pick shows, what was built, and the line it breaks. Mark polish as
  "Nit:"; anything unmarked must be fixed.
- Under each screen, put the pick beside the build, so the founder can judge from a phone. Use
  the URLs already on GitHub, so nothing new is pushed:
  `<img src="https://github.com/<owner>/<repo>/blob/propose/issue-<m>/mockups/issue-<m>/<letter>-phone.png?raw=true" width="195" alt="Option <letter> on a phone">`
  next to the builder's
  `<img src="https://github.com/<owner>/<repo>/blob/screenshots/issue-<n>/after/<name>-phone.png?raw=true" width="195" alt="<screen> as built, on a phone">`.
- Approve only what you looked at. Name any screen you could not serve or shoot; it is not
  approved.
- Never edit, commit or push in the product, and never merge. When you are done, stop your server
  with `kill <its process ID>` and remove the worktree with `git worktree remove <folder>/pr`.
