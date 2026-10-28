export const meta = {
  name: 'build',
  description: "Build one decided issue, or every issue the architect cut from a decided brief with two to four builders at once: each builder in its own worktree, QA and code review (and security review when it is needed), then the integrator merges one at a time",
  whenToUse: 'When the founder asks to build a decided issue or a planned brief in the current product repo, e.g. /founding-agents:build 12, or /founding-agents:build 7 3 for brief #7 with three builders at once',
  phases: [
    { title: 'Check', detail: 'the issue is decided, settles no technical decision the founder has not seen, and no red issue is open', model: 'sonnet' },
    { title: 'Build', detail: 'the builder, tests first, in its own worktree', model: 'opus' },
    { title: 'Review', detail: 'edge-case QA and code review side by side, and a security review when the change needs one', model: 'opus' },
    { title: 'Merge', detail: "the integrator tests the merge and merges, or readies it for the founder's merge where a merge deploys to production", model: 'sonnet' },
    { title: 'Report', detail: "the run's time, tokens, cost and whether it merged, posted on the issue", model: 'haiku' },
  ],
}

// A change the reviewers send back this many times goes to the founder instead of round four, and
// sooner if the builder fails to fix the same finding twice.
const ROUNDS = 3
// Dollars at API prices one run should stay under; the run report flags a run over it.
const BUDGET = 5

// A brief's issues are built this many at a time unless the founder asks for another number, up to
// MAX_BUILDERS. Builders and reviewers all draw on the same Opus allowance.
const BUILDERS = 2
const MAX_BUILDERS = 4

const named = args && typeof args === 'object' ? [args.issue, args.builders] : String(args ?? '').match(/\d+/g) || []
const issue = Number(named[0] || 0)
if (!issue) throw new Error('Name the issue to build, e.g. /founding-agents:build 12')
const builders = Math.min(MAX_BUILDERS, Math.max(1, Number(named[1]) || BUILDERS))

// What counts as a technical one-way door; build.js, propose.js, plan.js and sweep.js keep the same words (a test checks).
const ONE_WAY = 'a technical one-way door: a choice that costs a lot to reverse once code or people depend on it, such as using a framework or none, adding a build step, how the product deploys or is hosted, its language or stack, where and how it stores data, a dependency that ships to users, an outside service, or an interface other code or people rely on'

// A fix that changes the screen leaves the PR's before-and-after screenshots stale unless retaken.
const RESHOOT = "If what you change alters what someone sees, retake the after screenshots and bring the PR's Screenshots section up to date."
// What a change touches when it needs a security review. The check reads it from the issue so the
// security reviewer starts beside QA and code review; the code reviewer reads it from the diff, for
// a change that turns out to touch them when the issue did not say so.
const SECURITY = 'routes, sign-in, permissions, stored data, secrets, input from outside, calls to a model, or a dependency that ships to users'

const decided = t => t.decision ? `\n\nThe founder decided: ${t.decision}\nThe change builds what they picked; the mockups show the design, not code to copy.` : ''

const TICKET = {
  type: 'object',
  properties: {
    ready: { type: 'boolean', description: 'false only when a check fails or a decision is unseen; an open PR for the issue is not a reason' },
    reason: { type: 'string', description: 'why it cannot start; empty when ready' },
    repo: { type: 'string', description: 'owner/name' },
    title: { type: 'string' },
    body: { type: 'string' },
    decision: { type: 'string', description: "the founder's pick and notes from the comments, with the mockup branch if there is one; empty if none" },
    unseen: { type: 'array', items: { type: 'string' }, description: 'each technical one-way door the issue settles that the founder has not seen; empty if none' },
    open_pr: { type: 'integer', description: 'the open PR that already builds this issue, which the builder continues; 0 if none. It never makes the issue unready' },
    awaiting_merge: { type: 'boolean', description: 'true when the newest comment on open_pr, leaving out run reports, is a "Ready for your merge" item: it waits only for the founder to merge it' },
    security: { type: 'boolean', description: `true when what the issue asks for touches ${SECURITY}` },
    parts: {
      type: 'array',
      description: 'when this is a brief, each open issue the architect cut from it; empty otherwise',
      items: {
        type: 'object',
        properties: {
          number: { type: 'integer' },
          after: { type: 'array', items: { type: 'integer' }, description: 'the issues its body says to build it after' },
        },
        required: ['number', 'after'],
      },
    },
  },
  required: ['ready', 'reason', 'repo', 'title', 'body', 'decision', 'unseen', 'open_pr', 'awaiting_merge', 'security', 'parts'],
}
const BUILT = {
  type: 'object',
  properties: {
    pr_number: { type: 'integer', description: '0 when no PR was opened' },
    pr_url: { type: 'string' },
    stopped_because: { type: 'string', description: 'why there is no PR, such as a proposed split; empty otherwise' },
  },
  required: ['pr_number', 'pr_url', 'stopped_because'],
}
const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes'] },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          must_fix: { type: 'boolean', description: 'false for a Nit, and for a finding only someone the team already trusts could trigger, where review would see it' },
          where: { type: 'string' },
          what: { type: 'string', description: 'steps, expected, happened, and how to reproduce; for a holdout scenario, only its failure class and what went wrong, never its steps or data' },
          repeat: { type: 'boolean', description: "true only when a review from an earlier round, posted before the PR's latest push, raised it and it is still not fixed; never for one only this round's other reviewers raised" },
        },
        required: ['must_fix', 'where', 'what', 'repeat'],
      },
    },
  },
  required: ['verdict', 'findings'],
}
const CODE_REVIEW = {
  ...REVIEW,
  properties: { ...REVIEW.properties, security: { type: 'boolean', description: `true when the diff touches ${SECURITY}` } },
  required: [...REVIEW.required, 'security'],
}
const MERGED = {
  type: 'object',
  properties: {
    merged: { type: 'boolean' },
    merge_commit: { type: 'string' },
    founder: { type: 'boolean', description: 'true when the PR is ready and only the merge itself is left for the founder: the merge deploys to production, or Claude Code refused it' },
    reason: { type: 'string', description: 'why it was not merged, such as what the refusal said; empty when merged' },
  },
  required: ['merged', 'merge_commit', 'founder', 'reason'],
}

const REPORTED = {
  type: 'object',
  properties: {
    comment_url: { type: 'string', description: 'the posted comment; empty when it was not posted' },
    reason: { type: 'string', description: 'why it was not posted; empty when it was' },
  },
  required: ['comment_url', 'reason'],
}

const FILED = {
  type: 'object',
  properties: {
    issue_url: { type: 'string', description: 'the issue opened or commented on; empty when neither was done' },
    reason: { type: 'string', description: 'why it was not filed; empty when it was' },
  },
  required: ['issue_url', 'reason'],
}

const POSTED = {
  type: 'object',
  properties: { comment_url: { type: 'string' } },
  required: ['comment_url'],
}

const TIDIED = {
  type: 'object',
  properties: { removed: { type: 'integer' }, kept: { type: 'array', items: { type: 'string' }, description: 'each kept worktree and why' } },
  required: ['removed', 'kept'],
}

// A run that got past its first step removes the worktrees whose work is on GitHub, then posts its
// time, tokens, cost and whether it ended in a merge on the issue, stalled runs too.
const report = async result => {
  phase('Report')
  const tidied = await agent(
    'Use the tidy-worktrees skill: from this repo\'s folder, run its script with `--apply`. Return how many worktrees it removed and each one it kept, with why.',
    { label: 'tidy worktrees', phase: 'Report', model: 'haiku', effort: 'low', schema: TIDIED },
  )
  // A run whose only gap is the founder's merge did its part: it ended ready, not stopped.
  const all = result.issues && result.issues.length ? result.issues : [result]
  const ended = all.every(r => r.status === 'merged') ? 'merged'
    : all.every(r => r.status === 'merged' || r.status === WAITING || r.waits_for) ? 'ready' : 'stopped'
  const posted = await agent(
    `Use the run-report skill to post this run's report on issue #${issue}: from this repo's folder, run its script with \`--workflow build --issue ${issue} --budget ${BUDGET} --outcome ${ended} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  )
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted', worktrees_kept: tidied ? tidied.kept : [] }
}

// Reads one issue and says whether it can be built, or lists the issues cut from it when it is a brief.
const check = n => agent(
  `Check whether issue #${n} in this repo can be built. Read only; change nothing.
- \`gh issue list --state all --search "\\"Part of #${n}\\" in:body" --json number,state,body\`: if any open issue's body starts "Part of #${n}", #${n} is a brief the architect cut into issues. Return each open one as parts, with the numbers its "Build after" lines name (a "Matches #<m>" line only keeps it consistent with #<m> and is not one of them), return ready true, the repo and the title, and skip every check below.
- \`gh repo view --json nameWithOwner\` gives the repo.
- \`gh issue view ${n} --json title,body,state,labels,comments\`: it must be open, and either labelled \`decided\` or cut by the architect from a decided brief: its body starts "Part of #<n>", and \`gh issue view <n> --json labels,comments\` shows that brief labelled \`decided\`.
- If its body says "Build after #<m>", each #<m> must be closed. A "Matches #<m>" line is a consistency link, not a dependency: it never makes the issue wait.
- \`gh issue list --label red --state open --json number,title\`: no \`red\` issue may be open, unless #${n} is that issue. A red scheduled check stops other work until it is fixed.
- Read what the issue asks for and list each ${ONE_WAY}, that building it would settle, including ones it takes for granted ("plain HTML", "add a database"). The founder has seen one only when it is named in the issue's "Technical decisions" section, or in a \`propose\` or \`plan\` queue item on this issue or on the brief it is part of, with the founder's choice; the \`decided\` label on the issue or its brief is the founder's yes to what those name. Return every one not named that way as unseen. A change that settles none, such as copy, a fix inside existing code or a test, has none.
- \`gh pr list --state open --json number,headRefName,body\`: an open PR on the branch \`build/issue-${n}\`, or one whose description closes #${n}, already builds it. Return its number as open_pr, or 0. Return awaiting_merge true when the newest comment on that PR, leaving out run reports, starts "**Ready for your merge:**", so the PR waits only for the founder to merge it. An open PR is never a reason to stop: it does not make the issue unready, because the builder continues that PR from its reviews; only the checks above and below decide ready.
- Return security true when what the issue asks for touches ${SECURITY}, so its security review starts beside the other reviews; false when it plainly touches none of them, such as copy, layout or a test.
Return ready, which is false when anything above fails or anything is unseen, and when it is not, the reason in one sentence. Return the title and body as they are. If the comments on the issue, or on the brief it is part of, hold the founder's decision on a queue item, such as the option they picked from mockups, return their words and the mockup branch (\`propose/issue-<the issue or brief the mockups were made for>\`) as the decision.`,
  { label: `check #${n}`, phase: 'Check', model: 'sonnet', effort: 'medium', schema: TICKET },
)

// Edge-case QA and code review side by side, with the security review beside them when the check
// says the issue needs one, or straight after code review when the code reviewer finds the diff
// needs one. Each posts its own comment on the PR; the change is approved only when all approve.
// A repeat is a finding an earlier round raised that the builder's push did not fix. The other
// reviewers of this round post on the same PR at the same time, so a finding they raised minutes
// ago is not a repeat, and nor is an earlier Nit re-rated must-fix, which the builder was allowed
// to skip: on the website's #27, each of these stopped a run as if a fix had failed twice.
const REPEATS = "Earlier rounds' reviews on this PR are in its comments. Mark a finding as a repeat only when a review posted before the PR's latest push raised it and it is still not fixed. Reviews posted after the latest push are this round's, from the other reviewers working beside you: a finding only they raised is not a repeat, even if you agree with it. Nor is one an earlier round marked as a Nit or informational that you now rate must-fix: the builder was allowed to skip it, so it has not failed to fix it; raise it as a new finding."

// The architect puts a pass mark no reviewer can check (a dashboard, a logged-in page, something
// true only after the merge) under "The founder checks". On Half Badger's #2, three send-backs came
// from pass marks behind Vercel's dashboard and login, which no agent could check.
const FOUNDER_CHECKS = 'Pass marks under "The founder checks" in the issue are the founder\'s: never send the change back for one, and do not count one you cannot check against it. Say in your review which are left for the founder. Any other pass mark you cannot check with what you have is a finding about the issue, not the change: say so as a Nit.'

const reviews = async (n, ticket, built, again, earlier) => {
  const before = earlier && earlier.length
    ? `\n\nThe previous round's must-fix findings, so you can tell which are still open:\n${earlier.filter(f => f.must_fix).map(f => `- ${f.where}: ${f.what}`).join('\n')}`
    : ''
  const brief = `PR #${built.pr_number} in ${ticket.repo}, which builds issue #${n}: ${ticket.title}

${ticket.body}${decided(ticket)}

${FOUNDER_CHECKS}

${again ? `${REPEATS}${before}\n\n` : ''}Post your review on the PR, then return the verdict and every finding.`
  const secure = () => agent(`Check the security of ${brief}`,
    { label: `security review #${n}, round ${built.round}`, phase: 'Review', agentType: 'founding-agents:security-reviewer', model: 'opus', schema: REVIEW })
  // A diff that needs a security review the issue did not ask for gets one as soon as code review
  // says so, without waiting for QA to finish.
  const codeThenSecurity = async () => {
    const code = await agent(`Review ${brief}`, { label: `code review #${n}, round ${built.round}`, phase: 'Review', agentType: 'founding-agents:code-reviewer', model: 'opus', schema: CODE_REVIEW })
    return { code, security: code && code.security && !ticket.security ? await secure() : null }
  }
  const [qa, reviewed, early] = await parallel([
    () => agent(`Test ${brief}`, { label: `qa #${n}, round ${built.round}`, phase: 'Review', agentType: 'founding-agents:qa', model: 'opus', schema: REVIEW }),
    codeThenSecurity,
    ...(ticket.security ? [secure] : []),
  ])
  if (!qa || !reviewed || !reviewed.code) return null
  const security = ticket.security ? early : reviewed.security
  if ((ticket.security || reviewed.code.security) && !security) return null
  const all = [['QA', qa], ['Code review', reviewed.code]]
  if (security) all.push(['Security', security])
  return {
    verdict: all.every(([, r]) => r.verdict === 'approve') ? 'approve' : 'changes',
    findings: all.flatMap(([who, r]) => r.findings.map(f => ({ ...f, where: `${who}: ${f.where}` }))),
    reviewers: all.map(([who]) => who),
  }
}

// A must-fix the builder failed to fix twice is a mistake the next change can make too, so it goes to
// the librarian as a `librarian` issue, built here rather than by a model so every one has the same shape.
// Agents post with the founder's login, so the label, not the author, is what marks it.
const LIBRARIAN_LABEL = 'gh label create librarian --color 1D76DB --description "A mistake a run made twice, for the librarian to turn into a check"'
const lesson = (n, ticket, built, stuck) => {
  const title = `Repeated finding on PR #${built.pr_number}`
  const body = [
    `**A finding came back unfixed.** \`build\` stopped on PR #${built.pr_number} (${built.pr_url}) for issue #${n}, ${ticket.title}, because a reviewer raised the same must-fix after the builder's fix:`,
    '',
    ...stuck.map(f => `- ${f.where}: ${f.what}`),
    '',
    `A mistake made twice is one the next change can make too, so fixing this PR is not enough. **Librarian:** find which check would have stopped it and why none did, then propose that check as a test, a lint rule, a hook or a skill, so it holds for every later change. Its failure message should say how to fix the problem, not only what failed, so the next builder can act on it.`,
  ]
  return agent(
    `Open this issue in ${ticket.repo} exactly as written, labelled \`librarian\`, with \`gh issue create --repo ${ticket.repo} --label librarian --title "${title}" --body-file -\`. If the label does not exist yet, create it first with \`${LIBRARIAN_LABEL} --repo ${ticket.repo}\`. If \`gh issue list --repo ${ticket.repo} --label librarian --state open --json number,title\` already shows an issue with this title, comment the body on it with \`gh issue comment <its number> --repo ${ticket.repo} --body-file -\` instead of opening another. Return its URL, or why it was not filed.

${body.join('\n')}`,
    { label: `lesson, PR #${built.pr_number}`, phase: 'Review', model: 'haiku', effort: 'low', schema: FILED },
  )
}

// Builder and reviewers, up to ROUNDS times. Returns the approved PR, or why it stopped.
const develop = async (n, ticket) => {
  let built = null
  let review = null
  for (let round = 1; round <= ROUNDS; round++) {
    const resume = round === 1 && ticket.open_pr
    const task = resume
      ? `PR #${ticket.open_pr} already builds issue #${n} in ${ticket.repo}: ${ticket.title}

${ticket.body}${decided(ticket)}

Continue it rather than starting again. Check out its branch in your worktree with \`gh pr checkout ${ticket.open_pr}\`, read the reviews and comments on the PR, fix every finding not yet fixed that is not a Nit, finish anything the issue asks for that is missing, rerun the whole suite, and push to the same branch. ${RESHOOT} Do not open a new PR.`
      : round === 1
      ? `Build issue #${n} in ${ticket.repo}: ${ticket.title}

${ticket.body}${decided(ticket)}

Work on a branch named \`build/issue-${n}\`. Open the PR against the default branch, and end its description with "Closes #${n}".`
      : `The reviewers sent PR #${built.pr_number} for issue #${n} back. Check out its branch in your worktree with \`gh pr checkout ${built.pr_number}\`, fix every finding that is not a Nit, rerun the whole suite, and push to the same branch. ${RESHOOT} Do not open a new PR.

Findings:
${review.findings.map(f => `- ${f.must_fix ? '' : 'Nit: '}${f.where}: ${f.what}`).join('\n')}`
    const result = await agent(
      `${task}\n\nReturn the PR's number and URL, or 0 and why you stopped without one.`,
      { label: `builder #${n}, round ${round}`, phase: 'Build', agentType: 'founding-agents:builder', isolation: 'worktree', model: 'opus', schema: BUILT },
    )
    if (!result || !result.pr_number) {
      return { issue: n, status: 'stopped in build', reason: result ? result.stopped_because : 'the builder returned nothing', pr: built && built.pr_url }
    }
    built = { ...result, round }

    review = await reviews(n, ticket, built, round > 1 || resume, round > 1 ? review.findings : null)
    if (!review) return { issue: n, status: 'stopped in review', reason: 'a reviewer returned nothing', pr: built.pr_url }
    if (review.verdict === 'approve') return { issue: n, status: 'approved', built: { ...built, reviewers: review.reviewers } }
    const stuck = review.findings.filter(f => f.must_fix && f.repeat)
    if ((round > 1 || resume) && stuck.length) {
      const filed = await lesson(n, ticket, built, stuck)
      return { issue: n, status: 'the same finding came back unfixed; the founder decides', pr: built.pr_url, findings: stuck,
               lesson: filed ? (filed.issue_url || filed.reason) : 'not filed' }
    }
    log(`#${n}, round ${round}: the reviewers sent PR #${built.pr_number} back with ${review.findings.filter(f => f.must_fix).length} finding(s) to fix`)
  }
  return { issue: n, status: `sent back ${ROUNDS} times; the founder decides`, pr: built.pr_url, findings: review.findings }
}

// A PR that is ready but whose merge is the founder's: where merging deploys to production the
// founder merges, and a merge Claude Code refuses is never worked around. On Half Badger, auto
// mode refused the integrator's merge of #10, #12 and #14 as a merge without review that deploys,
// and each approved PR then waited for the whole run to end, about 30 minutes for #14. So the item
// goes up the moment the integrator stops, built here so every one has the same shape.
const WAITING = 'ready for your merge'
const NEEDS_FOUNDER_LABEL = 'gh label create needs-founder --color FBCA04 --description "Waiting on the founder\'s decision"'
const readyForFounder = (n, ticket, built, why) => {
  const reviewers = built.reviewers || []
  const body = [
    `**Ready for your merge:** PR #${built.pr_number} builds #${n}, ${ticket.title}. ${reviewers.length ? `${reviewers.join(', ')} approved it` : 'Its reviewers approved it'}, and the integrator found its required checks green on what the merge will be.${reviewers.includes('Security') ? '' : ' No security review ran: the check and code review found nothing one looks at.'}`,
    '',
    `**Why the merge is yours:** ${why}`,
    '',
    `- If #${n} lists checks under "The founder checks", they are yours to make, before or after the merge as each says.`,
    `- To ship it, merge PR #${built.pr_number} on GitHub. Issues that build after #${n} start on the next \`/founding-agents:build\` run once it has merged.`,
    `- To hold it, comment what is wrong; the next \`/founding-agents:build ${n}\` continues the PR from your comment.`,
  ]
  return agent(
    `Post this comment on PR #${built.pr_number} in ${ticket.repo} exactly as written, with \`gh pr comment ${built.pr_number} --repo ${ticket.repo} --body-file -\`, then label it with \`gh pr edit ${built.pr_number} --repo ${ticket.repo} --add-label needs-founder\`. If the label does not exist yet, create it first with \`${NEEDS_FOUNDER_LABEL} --repo ${ticket.repo}\`. Return the comment's URL. Do not merge the PR.

${body.join('\n')}`,
    { label: `ready for your merge, PR #${built.pr_number}`, phase: 'Merge', model: 'haiku', effort: 'low', schema: POSTED },
  )
}

// The integrator merges one PR at a time, each tested on top of the one merged before it.
let turn = Promise.resolve()
const merge = (n, ticket, built) => {
  const mine = turn.then(async () => {
    const merged = await agent(
      `Merge PR #${built.pr_number} in ${ticket.repo}. It builds issue #${n}, and its reviewers approved it in comments on the PR. Follow your instructions: test the merge, not the branch, and merge on its green checks without rerunning them when \`main\` has not moved since its last push. Where a merge deploys to production, or Claude Code refuses the merge, do not merge and do not look for another way: return founder true with why, once the PR is up to date and its checks are green.`,
      { label: `integrator, PR #${built.pr_number}`, phase: 'Merge', agentType: 'founding-agents:integrator', model: 'sonnet', schema: MERGED },
    )
    if (merged && !merged.merged && merged.founder) {
      const posted = await readyForFounder(n, ticket, built, merged.reason || 'the integrator could not merge it')
      return { issue: n, status: WAITING, reason: merged.reason, pr: built.pr_url, queue_item: posted ? posted.comment_url : 'not posted' }
    }
    if (!merged || !merged.merged) {
      return { issue: n, status: 'not merged', reason: merged ? merged.reason : 'the integrator returned nothing', pr: built.pr_url }
    }
    return { issue: n, status: 'merged', pr: built.pr_url, merge_commit: merged.merge_commit }
  })
  turn = mine.catch(() => null)
  return mine
}

// A PR already waiting for the founder's merge is neither rebuilt nor reviewed again, and gets no
// second item.
const awaiting = (n, ticket) => ({ issue: n, status: WAITING, reason: `PR #${ticket.open_pr} already waits for your merge`, pr: ticket.open_pr })

const notReady = (n, ticket) => ticket.unseen.length
  ? { issue: n, status: 'needs the founder', reason: 'it settles technical decisions the founder has not seen', unseen: ticket.unseen,
      next: `Name each under "Technical decisions" in #${n} for the founder to decide, or run /founding-agents:propose ${n}` }
  : { issue: n, status: 'not started', reason: ticket.reason }

phase('Check')
const ticket = await check(issue)
if (!ticket) throw new Error(`Could not read issue #${issue}`)

if (!ticket.parts.length) {
  if (ticket.unseen.length || !ticket.ready) return notReady(issue, ticket)
  if (ticket.open_pr && ticket.awaiting_merge) return awaiting(issue, ticket)
  const developed = await develop(issue, ticket)
  if (developed.status !== 'approved') return await report(developed)
  return await report(await merge(issue, ticket, developed.built))
}

// A brief: build its issues, up to `builders` at a time, each once every issue it builds after has
// merged. The architect cut them so no two touch the same files.
const parts = new Map(ticket.parts.map(p => [p.number, p]))
log(`#${issue} is a brief with ${parts.size} issue(s) to build, ${builders} at a time`)
const one = async n => {
  const t = await check(n)
  if (!t) return { issue: n, status: 'not started', reason: `could not read #${n}` }
  if (t.unseen.length || !t.ready) return notReady(n, t)
  if (t.open_pr && t.awaiting_merge) return awaiting(n, t)
  const developed = await develop(n, t)
  return developed.status === 'approved' ? await merge(n, t, developed.built) : developed
}
const results = []
const running = new Map()
const failed = new Set()
// Issues held up only by a PR waiting for the founder's merge: the next run starts them.
const waiting = new Map()
while (parts.size || running.size) {
  for (const p of [...parts.values()]) {
    const blocker = p.after.find(m => failed.has(m))
    const held = p.after.find(m => waiting.has(m))
    if (blocker) {
      parts.delete(p.number)
      failed.add(p.number)
      results.push({ issue: p.number, status: 'not started', reason: `#${blocker}, which it builds after, did not merge` })
    } else if (held && !p.after.some(m => parts.has(m) || running.has(m))) {
      parts.delete(p.number)
      waiting.set(p.number, waiting.get(held))
      results.push({ issue: p.number, status: 'not started', waits_for: waiting.get(held),
                     reason: `it builds after #${held}, which waits for your merge; the next run starts it once that has merged` })
    } else if (running.size < builders && !p.after.some(m => parts.has(m) || running.has(m))) {
      parts.delete(p.number)
      running.set(p.number, one(p.number).then(r => r || { issue: p.number, status: 'stopped', reason: 'no result' }))
    }
  }
  if (!running.size) {
    for (const p of parts.values()) results.push({ issue: p.number, status: 'not started', reason: `it builds after ${p.after.map(m => `#${m}`).join(', ')}, which no run can reach` })
    break
  }
  const done = await Promise.race(running.values())
  running.delete(done.issue)
  if (done.status === WAITING) waiting.set(done.issue, done.issue)
  else if (done.status !== 'merged') failed.add(done.issue)
  results.push(done)
}
const merged = results.filter(r => r.status === 'merged').length
const ready = results.filter(r => r.status === WAITING).length
return await report({ issue, status: `${merged} of ${results.length} issues merged${ready ? `, ${ready} ready for your merge` : ''}`, builders, issues: results })
