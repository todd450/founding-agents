export const meta = {
  name: 'build',
  description: 'Build one decided issue: the builder in its own worktree, the reviewer, then the integrator merges',
  whenToUse: 'When the founder asks to build a decided issue in the current product repo, e.g. /founding-agents:build 12',
  phases: [
    { title: 'Check', detail: 'the issue is decided, settles no technical decision the founder has not seen, and no red issue is open', model: 'sonnet' },
    { title: 'Build', detail: 'the builder, tests first, in its own worktree', model: 'opus' },
    { title: 'Review', detail: 'edge-case QA and code review on the PR', model: 'opus' },
    { title: 'Merge', detail: 'the integrator tests the merge and merges', model: 'sonnet' },
    { title: 'Report', detail: "the run's time, tokens and cost, posted on the issue", model: 'haiku' },
  ],
}

// A change the reviewer sends back this many times goes to the founder instead of round four.
const ROUNDS = 3

const raw = args && typeof args === 'object' ? args.issue : args
const issue = Number(String(raw ?? '').replace(/[^0-9]/g, ''))
if (!issue) throw new Error('Name the issue to build, e.g. /founding-agents:build 12')

// What counts as a technical one-way door; build.js and propose.js keep the same words (a test checks).
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
  },
  required: ['ready', 'reason', 'repo', 'title', 'body', 'decision', 'unseen'],
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
          what: { type: 'string', description: 'steps, expected, happened, and how to reproduce' },
        },
        required: ['must_fix', 'where', 'what'],
      },
    },
  },
  required: ['verdict', 'findings'],
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

// A run that got past its first step posts its time, tokens and cost on the issue, stalled runs too.
const report = async result => {
  phase('Report')
  const posted = await agent(
    `Use the run-report skill to post this run's report on issue #${issue}: from this repo's folder, run its script with \`--workflow build --issue ${issue} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  )
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted' }
}

phase('Check')
const ticket = await agent(
  `Check whether issue #${issue} in this repo can be built. Read only; change nothing.
- \`gh repo view --json nameWithOwner\` gives the repo.
- \`gh issue view ${issue} --json title,body,state,labels,comments\`: it must be open and labelled \`decided\`.
- \`gh issue list --label red --state open --json number,title\`: no \`red\` issue may be open, unless #${issue} is that issue. A red scheduled check stops other work until it is fixed.
- Read what the issue asks for and list each ${ONE_WAY}, that building it would settle, including ones it takes for granted ("plain HTML", "add a database"). The founder has seen one only when it is named in the issue's "Technical decisions" section, or in a \`propose\` queue item on this issue, with the founder's choice; the \`decided\` label is the founder's yes to what those name. Return every one not named that way as unseen. A change that settles none, such as copy, a fix inside existing code or a test, has none.
Return ready, which is false when anything above fails or anything is unseen, and when it is not, the reason in one sentence. Return the title and body as they are. If the comments hold the founder's decision on a queue item, such as the option they picked from mockups, return their words and the mockup branch (\`propose/issue-${issue}\`) as the decision.`,
  { label: `check #${issue}`, phase: 'Check', model: 'sonnet', effort: 'medium', schema: TICKET },
)
if (!ticket) throw new Error(`Could not read issue #${issue}`)
if (ticket.unseen.length) {
  return { issue, status: 'needs the founder', reason: 'it settles technical decisions the founder has not seen', unseen: ticket.unseen,
           next: `Name each under "Technical decisions" in #${issue} for the founder to decide, or run /founding-agents:propose ${issue}` }
}
if (!ticket.ready) return { issue, status: 'not started', reason: ticket.reason }

let built = null
let review = null
for (let round = 1; round <= ROUNDS; round++) {
  const task = round === 1
    ? `Build issue #${issue} in ${ticket.repo}: ${ticket.title}

${ticket.body}${decided(ticket)}

Work on a branch named \`build/issue-${issue}\`. Open the PR against the default branch, and end its description with "Closes #${issue}".`
    : `The reviewer sent PR #${built.pr_number} for issue #${issue} back. Check out its branch in your worktree with \`gh pr checkout ${built.pr_number}\`, fix every finding that is not a Nit, rerun the whole suite, and push to the same branch. Do not open a new PR.

Findings:
${review.findings.map(f => `- ${f.must_fix ? '' : 'Nit: '}${f.where}: ${f.what}`).join('\n')}`
  const result = await agent(
    `${task}\n\nReturn the PR's number and URL, or 0 and why you stopped without one.`,
    { label: `builder, round ${round}`, phase: 'Build', agentType: 'founding-agents:builder', isolation: 'worktree', model: 'opus', schema: BUILT },
  )
  if (!result || !result.pr_number) {
    return await report({ issue, status: 'stopped in build', reason: result ? result.stopped_because : 'the builder returned nothing', pr: built && built.pr_url })
  }
  built = result

  review = await agent(
    `Review PR #${built.pr_number} in ${ticket.repo}, which builds issue #${issue}: ${ticket.title}

${ticket.body}${decided(ticket)}

Post your review on the PR, then return the verdict and every finding.`,
    { label: `reviewer, round ${round}`, phase: 'Review', agentType: 'founding-agents:reviewer', model: 'opus', schema: REVIEW },
  )
  if (!review) return await report({ issue, status: 'stopped in review', reason: 'the reviewer returned nothing', pr: built.pr_url })
  if (review.verdict === 'approve') break
  log(`Round ${round}: the reviewer sent PR #${built.pr_number} back with ${review.findings.filter(f => f.must_fix).length} finding(s) to fix`)
}

if (review.verdict !== 'approve') {
  return await report({ issue, status: `sent back ${ROUNDS} times; the founder decides`, pr: built.pr_url, findings: review.findings })
}

phase('Merge')
const merge = await agent(
  `Merge PR #${built.pr_number} in ${ticket.repo}. It builds issue #${issue}, and the reviewer approved it in a comment on the PR. Follow your instructions: test the merge, not the branch.`,
  { label: `integrator, PR #${built.pr_number}`, phase: 'Merge', agentType: 'founding-agents:integrator', model: 'sonnet', schema: MERGED },
)
if (!merge || !merge.merged) {
  return await report({ issue, status: 'not merged', reason: merge ? merge.reason : 'the integrator returned nothing', pr: built.pr_url })
}
return await report({ issue, status: 'merged', pr: built.pr_url, merge_commit: merge.merge_commit })
