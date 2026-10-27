export const meta = {
  name: 'plan',
  description: 'Cut a decided brief into build issues: the architect plans, asks the founder about any technical decision the brief left open, and opens issues that never share files',
  whenToUse: 'When the founder has decided a brief and it needs cutting into build issues before building, e.g. /founding-agents:plan 7',
  phases: [
    { title: 'Check', detail: 'the brief is decided and not already planned', model: 'haiku' },
    { title: 'Plan', detail: 'the architect writes the plan and opens the build issues', model: 'opus' },
    { title: 'Queue', detail: 'one needs-founder item for the technical decisions the brief left open', model: 'haiku' },
    { title: 'Report', detail: "the run's time, tokens and cost, posted on the brief", model: 'haiku' },
  ],
}

const raw = args && typeof args === 'object' ? args.issue : args
const issue = Number(String(raw ?? '').replace(/[^0-9]/g, ''))
if (!issue) throw new Error('Name the decided brief to plan, e.g. /founding-agents:plan 7')

// What counts as a technical one-way door; build.js, propose.js and plan.js keep the same words (a test checks).
const ONE_WAY = 'a technical one-way door: a choice that costs a lot to reverse once code or people depend on it, such as using a framework or none, adding a build step, how the product deploys or is hosted, its language or stack, where and how it stores data, a dependency that ships to users, an outside service, or an interface other code or people rely on'

// Dollars at API prices one run should stay under; the run report flags a run over it.
const BUDGET = 5

const BRIEF = {
  type: 'object',
  properties: {
    ready: { type: 'boolean' },
    reason: { type: 'string', description: 'why it cannot be planned; empty when ready' },
    repo: { type: 'string', description: 'owner/name' },
    title: { type: 'string' },
    decision: { type: 'string', description: "the founder's answers from the comments: the option picked, each technical decision, and notes; empty if none" },
  },
  required: ['ready', 'reason', 'repo', 'title', 'decision'],
}
const PLAN = {
  type: 'object',
  properties: {
    decisions: {
      type: 'array',
      description: 'every technical one-way door the plan needs that the founder has not answered; empty when there are none, and then the issues are open',
      items: {
        type: 'object',
        properties: {
          decision: { type: 'string', description: 'the choice, in a few words' },
          options: { type: 'array', items: { type: 'string' }, description: 'the realistic options, each in a few words' },
          recommend: { type: 'string', description: 'the option you recommend' },
          why: { type: 'string', description: 'why, in one sentence' },
          reverse: { type: 'string', description: 'what reversing it later would cost' },
        },
        required: ['decision', 'options', 'recommend', 'why', 'reverse'],
      },
    },
    issues: {
      type: 'array',
      description: 'the build issues opened, in the order to build them; empty when there are decisions',
      items: {
        type: 'object',
        properties: {
          number: { type: 'integer' },
          title: { type: 'string' },
          after: { type: 'array', items: { type: 'integer' }, description: 'issues it builds after' },
        },
        required: ['number', 'title', 'after'],
      },
    },
    plan_url: { type: 'string', description: 'the plan comment on the brief; empty when there are decisions' },
    stopped_because: { type: 'string', description: 'why there is neither a plan nor decisions; empty otherwise' },
  },
  required: ['decisions', 'issues', 'plan_url', 'stopped_because'],
}
const POSTED = {
  type: 'object',
  properties: { comment_url: { type: 'string' } },
  required: ['comment_url'],
}
const REPORTED = {
  type: 'object',
  properties: {
    comment_url: { type: 'string', description: 'the posted comment; empty when it was not posted' },
    reason: { type: 'string', description: 'why it was not posted; empty when it was' },
  },
  required: ['comment_url', 'reason'],
}

// A run that got past its first step posts its time, tokens and cost on the brief, stalled runs too.
const report = async result => {
  phase('Report')
  const posted = await agent(
    `Use the run-report skill to post this run's report on issue #${issue}: from this repo's folder, run its script with \`--workflow plan --issue ${issue} --budget ${BUDGET} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  )
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted' }
}

phase('Check')
const brief = await agent(
  `Check whether brief #${issue} in this repo can be planned. Read only; change nothing.
- \`gh repo view --json nameWithOwner\` gives the repo.
- \`gh issue view ${issue} --json title,state,labels,comments\`: it must be open and labelled \`decided\`.
- \`gh issue list --state all --search "\\"Part of #${issue}\\" in:body" --json number,title\`: no issue may say it is part of #${issue} yet; if any does, the brief is already planned, so name them in the reason.
Return ready, which is false when anything above fails, and when it is not, the reason in one sentence. Return the title as it is. If the comments hold the founder's answers to a queue item (the option picked, a choice for each technical decision, notes), return their words as the decision.`,
  { label: `check #${issue}`, phase: 'Check', model: 'haiku', effort: 'low', schema: BRIEF },
)
if (!brief) throw new Error(`Could not read issue #${issue}`)
if (!brief.ready) return { issue, status: 'not started', reason: brief.reason }

phase('Plan')
const plan = await agent(
  `Plan brief #${issue} in ${brief.repo}: ${brief.title}
${brief.decision ? `\nThe founder decided: ${brief.decision}\n` : ''}
Read the brief, its comments and the product first. Then list each ${ONE_WAY}, that the plan needs. The founder has answered one only when it is named in the brief's "Technical decisions" section or in a queue item on it, with the founder's choice in a comment.

If any is not answered that way, create nothing: return each one with its options, the one you recommend and why, and what reversing it later would cost.

Otherwise open the build issues with \`gh issue create\`, in the order to build them, one small change each. Give each this body:

Part of #${issue}.
Build after #<n>. (only when it builds on another issue)

## What
<what it does and why, in a few sentences>

## Files
<every file it owns; no two issues own the same file>

## Tests
<the behaviour its tests check, from the product's fixtures where they cover it>

## Technical decisions
<each one-way door it settles, with the founder's choice: "<decision>: <choice>, decided on #${issue}". "None." when it settles none>

Then post the plan on #${issue} with \`gh issue comment ${issue} --body-file -\`: the one-way doors and how each was decided, the day-one defaults the product has and which issue sets up the rest, and the issues in order. Return the issues and the plan comment's URL.`,
  { label: 'architect', phase: 'Plan', agentType: 'founding-agents:architect', model: 'opus', schema: PLAN },
)
if (!plan) throw new Error('The architect returned nothing')

if (plan.decisions.length) {
  const ids = plan.decisions.map((_, i) => `P${i + 1}`)
  const lines = [
    `**Decision needed:** the architect's plan for this brief needs ${plan.decisions.length === 1 ? 'a technical decision' : 'technical decisions'} the brief left open. Each is costly to reverse once it is built in, so each is yours to decide:`,
    '',
    ...plan.decisions.map((d, i) =>
      `- **${ids[i]}. ${d.decision}:** ${d.options.join(' / ')}. Recommended: **${d.recommend}**, because ${d.why} Reversing it later: ${d.reverse}`),
    '',
    `**To decide:** reply with your choice for each (${ids.join(', ')}) and any notes, then add the \`decided\` label again, and \`/founding-agents:plan ${issue}\` plans it with your answers. No build issues are open yet.`,
  ]
  phase('Queue')
  const posted = await agent(
    `Post this comment on issue #${issue} in ${brief.repo} exactly as written, with \`gh issue comment ${issue} --repo ${brief.repo} --body-file -\`, then move the labels with \`gh issue edit ${issue} --repo ${brief.repo} --remove-label decided --add-label needs-founder\`. Return the comment's URL.

${lines.join('\n')}`,
    { label: 'queue item', phase: 'Queue', model: 'haiku', effort: 'low', schema: POSTED },
  )
  return await report({ issue, status: 'needs the founder', decisions: plan.decisions.map(d => d.decision),
                        queue_item: posted ? posted.comment_url : 'not posted' })
}
if (!plan.issues.length) {
  return await report({ issue, status: 'stopped in plan', reason: plan.stopped_because || 'the architect opened no issues' })
}
return await report({
  issue,
  status: 'planned',
  plan: plan.plan_url,
  issues: plan.issues.map(i => `#${i.number} ${i.title}${i.after.length ? ` (after ${i.after.map(n => `#${n}`).join(', ')})` : ''}`),
  next: `/founding-agents:build ${plan.issues[0].number}`,
})
