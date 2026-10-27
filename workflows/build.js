export const meta = {
  name: 'build',
  description: "Build one decided issue, or every issue the architect cut from a decided brief with two to four builders at once: each builder in its own worktree, QA and code review (and security review when it is needed), then the integrator merges one at a time",
  whenToUse: 'When the founder asks to build a decided issue or a planned brief in the current product repo, e.g. /founding-agents:build 12, or /founding-agents:build 7 3 for brief #7 with three builders at once',
  phases: [
    { title: 'Check', detail: 'the issue is decided, settles no technical decision the founder has not seen, and no red issue is open', model: 'sonnet' },
    { title: 'Build', detail: 'the builder, tests first, in its own worktree', model: 'opus' },
    { title: 'Review', detail: 'edge-case QA and code review side by side, and a security review when the change needs one', model: 'opus' },
    { title: 'Merge', detail: 'the integrator tests the merge and merges', model: 'sonnet' },
    { title: 'Report', detail: "the run's time, tokens and cost, posted on the issue", model: 'haiku' },
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

const decided = t => t.decision ? `\n\nThe founder decided: ${t.decision}\nThe change builds what they picked; the mockups show the design, not code to copy.` : ''

const TICKET = {
  type: 'object',
  properties: {
    ready: { type: 'boolean' },
    reason: { type: 'string', description: 'why it cannot start; empty when ready' },
    repo: { type: 'string', description: 'owner/name' },
    title: { type: 'string' },
    body: { type: 'string' },
    decision: { type: 'string', description: "the founder's pick and notes from the comments, with the mockup branch if there is one; empty if none" },
    unseen: { type: 'array', items: { type: 'string' }, description: 'each technical one-way door the issue settles that the founder has not seen; empty if none' },
    open_pr: { type: 'integer', description: 'the open PR that already builds this issue; 0 if none' },
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
  required: ['ready', 'reason', 'repo', 'title', 'body', 'decision', 'unseen', 'open_pr', 'parts'],
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
          must_fix: { type: 'boolean', description: 'false for a Nit' },
          where: { type: 'string' },
          what: { type: 'string', description: 'steps, expected, happened, and how to reproduce; for a holdout scenario, only its failure class and what went wrong, never its steps or data' },
          repeat: { type: 'boolean', description: 'true when an earlier review on this PR raised it and it is still not fixed' },
        },
        required: ['must_fix', 'where', 'what', 'repeat'],
      },
    },
  },
  required: ['verdict', 'findings'],
}
const CODE_REVIEW = {
  ...REVIEW,
  properties: { ...REVIEW.properties, security: { type: 'boolean', description: 'true when the diff touches routes, sign-in, permissions, stored data, secrets, input from outside, or calls to a model' } },
  required: [...REVIEW.required, 'security'],
}
const MERGED = {
  type: 'object',
  properties: {
    merged: { type: 'boolean' },
    merge_commit: { type: 'string' },
    reason: { type: 'string', description: 'why it was not merged; empty when merged' },
  },
  required: ['merged', 'merge_commit', 'reason'],
}

const REPORTED = {
  type: 'object',
  properties: {
    comment_url: { type: 'string', description: 'the posted comment; empty when it was not posted' },
    reason: { type: 'string', description: 'why it was not posted; empty when it was' },
  },
  required: ['comment_url', 'reason'],
}

const TIDIED = {
  type: 'object',
  properties: { removed: { type: 'integer' }, kept: { type: 'array', items: { type: 'string' }, description: 'each kept worktree and why' } },
  required: ['removed', 'kept'],
}

// A run that got past its first step removes the worktrees whose work is on GitHub, then posts its
// time, tokens and cost on the issue, stalled runs too.
const report = async result => {
  phase('Report')
  const tidied = await agent(
    'Use the tidy-worktrees skill: from this repo\'s folder, run its script with `--apply`. Return how many worktrees it removed and each one it kept, with why.',
    { label: 'tidy worktrees', phase: 'Report', model: 'haiku', effort: 'low', schema: TIDIED },
  )
  const posted = await agent(
    `Use the run-report skill to post this run's report on issue #${issue}: from this repo's folder, run its script with \`--workflow build --issue ${issue} --budget ${BUDGET} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  )
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted', worktrees_kept: tidied ? tidied.kept : [] }
}

// Reads one issue and says whether it can be built, or lists the issues cut from it when it is a brief.
const check = n => agent(
  `Check whether issue #${n} in this repo can be built. Read only; change nothing.
- \`gh issue list --state all --search "\\"Part of #${n}\\" in:body" --json number,state,body\`: if any open issue's body starts "Part of #${n}", #${n} is a brief the architect cut into issues. Return each open one as parts, with the numbers its "Build after" line names, return ready true, the repo and the title, and skip every check below.
- \`gh repo view --json nameWithOwner\` gives the repo.
- \`gh issue view ${n} --json title,body,state,labels,comments\`: it must be open, and either labelled \`decided\` or cut by the architect from a decided brief: its body starts "Part of #<n>", and \`gh issue view <n> --json labels,comments\` shows that brief labelled \`decided\`.
- If its body says "Build after #<m>", each #<m> must be closed.
- \`gh issue list --label red --state open --json number,title\`: no \`red\` issue may be open, unless #${n} is that issue. A red scheduled check stops other work until it is fixed.
- Read what the issue asks for and list each ${ONE_WAY}, that building it would settle, including ones it takes for granted ("plain HTML", "add a database"). The founder has seen one only when it is named in the issue's "Technical decisions" section, or in a \`propose\` or \`plan\` queue item on this issue or on the brief it is part of, with the founder's choice; the \`decided\` label on the issue or its brief is the founder's yes to what those name. Return every one not named that way as unseen. A change that settles none, such as copy, a fix inside existing code or a test, has none.
- \`gh pr list --state open --json number,headRefName,body\`: an open PR on the branch \`build/issue-${n}\`, or one whose description closes #${n}, already builds it. Return its number as open_pr, or 0.
Return ready, which is false when anything above fails or anything is unseen, and when it is not, the reason in one sentence. Return the title and body as they are. If the comments on the issue, or on the brief it is part of, hold the founder's decision on a queue item, such as the option they picked from mockups, return their words and the mockup branch (\`propose/issue-<the issue or brief the mockups were made for>\`) as the decision.`,
  { label: `check #${n}`, phase: 'Check', model: 'sonnet', effort: 'medium', schema: TICKET },
)

// Edge-case QA and code review side by side, then a security review when the code reviewer says the
// diff needs one. Each posts its own comment on the PR; the change is approved only when all approve.
const reviews = async (n, ticket, built, again) => {
  const brief = `PR #${built.pr_number} in ${ticket.repo}, which builds issue #${n}: ${ticket.title}

${ticket.body}${decided(ticket)}

${again ? 'Earlier reviews on this PR are in its comments. Mark each finding an earlier review raised that is still not fixed as a repeat.\n\n' : ''}Post your review on the PR, then return the verdict and every finding.`
  const [qa, code] = await parallel([
    () => agent(`Test ${brief}`, { label: `qa #${n}, round ${built.round}`, phase: 'Review', agentType: 'founding-agents:qa', model: 'opus', schema: REVIEW }),
    () => agent(`Review ${brief}`, { label: `code review #${n}, round ${built.round}`, phase: 'Review', agentType: 'founding-agents:code-reviewer', model: 'opus', schema: CODE_REVIEW }),
  ])
  if (!qa || !code) return null
  const all = [['QA', qa], ['Code review', code]]
  if (code.security) {
    const security = await agent(`Check the security of ${brief}`,
      { label: `security review #${n}, round ${built.round}`, phase: 'Review', agentType: 'founding-agents:security-reviewer', model: 'opus', schema: REVIEW })
    if (!security) return null
    all.push(['Security', security])
  }
  return {
    verdict: all.every(([, r]) => r.verdict === 'approve') ? 'approve' : 'changes',
    findings: all.flatMap(([who, r]) => r.findings.map(f => ({ ...f, where: `${who}: ${f.where}` }))),
  }
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

Continue it rather than starting again. Check out its branch in your worktree with \`gh pr checkout ${ticket.open_pr}\`, read the reviews and comments on the PR, fix every finding not yet fixed that is not a Nit, finish anything the issue asks for that is missing, rerun the whole suite, and push to the same branch. Do not open a new PR.`
      : round === 1
      ? `Build issue #${n} in ${ticket.repo}: ${ticket.title}

${ticket.body}${decided(ticket)}

Work on a branch named \`build/issue-${n}\`. Open the PR against the default branch, and end its description with "Closes #${n}".`
      : `The reviewers sent PR #${built.pr_number} for issue #${n} back. Check out its branch in your worktree with \`gh pr checkout ${built.pr_number}\`, fix every finding that is not a Nit, rerun the whole suite, and push to the same branch. Do not open a new PR.

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

    review = await reviews(n, ticket, built, round > 1 || resume)
    if (!review) return { issue: n, status: 'stopped in review', reason: 'a reviewer returned nothing', pr: built.pr_url }
    if (review.verdict === 'approve') return { issue: n, status: 'approved', built }
    const stuck = review.findings.filter(f => f.must_fix && f.repeat)
    if ((round > 1 || resume) && stuck.length) {
      return { issue: n, status: 'the same finding came back unfixed; the founder decides', pr: built.pr_url, findings: stuck }
    }
    log(`#${n}, round ${round}: the reviewers sent PR #${built.pr_number} back with ${review.findings.filter(f => f.must_fix).length} finding(s) to fix`)
  }
  return { issue: n, status: `sent back ${ROUNDS} times; the founder decides`, pr: built.pr_url, findings: review.findings }
}

// The integrator merges one PR at a time, each tested on top of the one merged before it.
let turn = Promise.resolve()
const merge = (n, ticket, built) => {
  const mine = turn.then(async () => {
    const merged = await agent(
      `Merge PR #${built.pr_number} in ${ticket.repo}. It builds issue #${n}, and its reviewers approved it in comments on the PR. Follow your instructions: test the merge, not the branch.`,
      { label: `integrator, PR #${built.pr_number}`, phase: 'Merge', agentType: 'founding-agents:integrator', model: 'sonnet', schema: MERGED },
    )
    if (!merged || !merged.merged) {
      return { issue: n, status: 'not merged', reason: merged ? merged.reason : 'the integrator returned nothing', pr: built.pr_url }
    }
    return { issue: n, status: 'merged', pr: built.pr_url, merge_commit: merged.merge_commit }
  })
  turn = mine.catch(() => null)
  return mine
}

const notReady = (n, ticket) => ticket.unseen.length
  ? { issue: n, status: 'needs the founder', reason: 'it settles technical decisions the founder has not seen', unseen: ticket.unseen,
      next: `Name each under "Technical decisions" in #${n} for the founder to decide, or run /founding-agents:propose ${n}` }
  : { issue: n, status: 'not started', reason: ticket.reason }

phase('Check')
const ticket = await check(issue)
if (!ticket) throw new Error(`Could not read issue #${issue}`)

if (!ticket.parts.length) {
  if (ticket.unseen.length || !ticket.ready) return notReady(issue, ticket)
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
  const developed = await develop(n, t)
  return developed.status === 'approved' ? await merge(n, t, developed.built) : developed
}
const results = []
const running = new Map()
const failed = new Set()
while (parts.size || running.size) {
  for (const p of [...parts.values()]) {
    const blocker = p.after.find(m => failed.has(m))
    if (blocker) {
      parts.delete(p.number)
      failed.add(p.number)
      results.push({ issue: p.number, status: 'not started', reason: `#${blocker}, which it builds after, did not merge` })
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
  if (done.status !== 'merged') failed.add(done.issue)
  results.push(done)
}
const merged = results.filter(r => r.status === 'merged').length
return await report({ issue, status: `${merged} of ${results.length} issues merged`, builders, issues: results })
