export const meta = {
  name: 'build',
  description: 'Build one decided issue: the builder in its own worktree, the reviewer, then the integrator merges',
  whenToUse: 'When the founder asks to build a decided issue in the current product repo, e.g. /founding-agents:build 12',
  phases: [
    { title: 'Check', detail: 'the issue is decided and no red issue is open', model: 'haiku' },
    { title: 'Build', detail: 'the builder, tests first, in its own worktree', model: 'sonnet' },
    { title: 'Review', detail: 'edge-case QA and code review on the PR', model: 'opus' },
    { title: 'Merge', detail: 'the integrator tests the merge and merges', model: 'sonnet' },
  ],
}

// A change the reviewer sends back this many times goes to the founder instead of round four.
const ROUNDS = 3

const raw = args && typeof args === 'object' ? args.issue : args
const issue = Number(String(raw ?? '').replace(/[^0-9]/g, ''))
if (!issue) throw new Error('Name the issue to build, e.g. /founding-agents:build 12')

const TICKET = {
  type: 'object',
  properties: {
    ready: { type: 'boolean' },
    reason: { type: 'string', description: 'why it cannot start; empty when ready' },
    repo: { type: 'string', description: 'owner/name' },
    title: { type: 'string' },
    body: { type: 'string' },
  },
  required: ['ready', 'reason', 'repo', 'title', 'body'],
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

phase('Check')
const ticket = await agent(
  `Check whether issue #${issue} in this repo can be built. Read only; change nothing.
- \`gh repo view --json nameWithOwner\` gives the repo.
- \`gh issue view ${issue} --json title,body,state,labels\`: it must be open and labelled \`decided\`.
- \`gh issue list --label red --state open --json number,title\`: no \`red\` issue may be open, unless #${issue} is that issue. A red scheduled check stops other work until it is fixed.
Return ready, and when it is not, the reason in one sentence. Return the title and body as they are.`,
  { label: `check #${issue}`, phase: 'Check', model: 'haiku', effort: 'low', schema: TICKET },
)
if (!ticket) throw new Error(`Could not read issue #${issue}`)
if (!ticket.ready) return { issue, status: 'not started', reason: ticket.reason }

let built = null
let review = null
for (let round = 1; round <= ROUNDS; round++) {
  const task = round === 1
    ? `Build issue #${issue} in ${ticket.repo}: ${ticket.title}

${ticket.body}

Work on a branch named \`build/issue-${issue}\`. Open the PR against the default branch, and end its description with "Closes #${issue}".`
    : `The reviewer sent PR #${built.pr_number} for issue #${issue} back. Check out its branch in your worktree with \`gh pr checkout ${built.pr_number}\`, fix every finding that is not a Nit, rerun the whole suite, and push to the same branch. Do not open a new PR.

Findings:
${review.findings.map(f => `- ${f.must_fix ? '' : 'Nit: '}${f.where}: ${f.what}`).join('\n')}`
  const result = await agent(
    `${task}\n\nReturn the PR's number and URL, or 0 and why you stopped without one.`,
    { label: `builder, round ${round}`, phase: 'Build', agentType: 'founding-agents:builder', isolation: 'worktree', model: 'sonnet', schema: BUILT },
  )
  if (!result || !result.pr_number) {
    return { issue, status: 'stopped in build', reason: result ? result.stopped_because : 'the builder returned nothing', pr: built && built.pr_url }
  }
  built = result

  review = await agent(
    `Review PR #${built.pr_number} in ${ticket.repo}, which builds issue #${issue}: ${ticket.title}

${ticket.body}

Post your review on the PR, then return the verdict and every finding.`,
    { label: `reviewer, round ${round}`, phase: 'Review', agentType: 'founding-agents:reviewer', model: 'opus', schema: REVIEW },
  )
  if (!review) return { issue, status: 'stopped in review', reason: 'the reviewer returned nothing', pr: built.pr_url }
  if (review.verdict === 'approve') break
  log(`Round ${round}: the reviewer sent PR #${built.pr_number} back with ${review.findings.filter(f => f.must_fix).length} finding(s) to fix`)
}

if (review.verdict !== 'approve') {
  return { issue, status: `sent back ${ROUNDS} times; the founder decides`, pr: built.pr_url, findings: review.findings }
}

phase('Merge')
const merge = await agent(
  `Merge PR #${built.pr_number} in ${ticket.repo}. It builds issue #${issue}, and the reviewer approved it in a comment on the PR. Follow your instructions: test the merge, not the branch.`,
  { label: `integrator, PR #${built.pr_number}`, phase: 'Merge', agentType: 'founding-agents:integrator', model: 'sonnet', schema: MERGED },
)
if (!merge || !merge.merged) {
  return { issue, status: 'not merged', reason: merge ? merge.reason : 'the integrator returned nothing', pr: built.pr_url }
}
return { issue, status: 'merged', pr: built.pr_url, merge_commit: merge.merge_commit }
