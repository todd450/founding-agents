export const meta = {
  name: 'propose',
  description: 'Turn an idea into one decision for the founder: the product lead writes the brief, the designer mocks up options, and one queue item carries both',
  whenToUse: 'When the founder has an idea or an issue to shape before anything is built, e.g. /founding-agents:propose 7 or /founding-agents:propose "a pricing page"',
  phases: [
    { title: 'Brief', detail: 'the product lead writes the brief and recommends', model: 'opus' },
    { title: 'Design', detail: 'the designer storyboards and mocks up two or three options', model: 'opus' },
    { title: 'Queue', detail: 'one needs-founder item with the brief, the options and their costs', model: 'haiku' },
    { title: 'Report', detail: "the run's time, tokens and cost, posted on the issue", model: 'haiku' },
  ],
}

const raw = args && typeof args === 'object' ? (args.issue ?? args.idea) : args
const text = String(raw ?? '').trim()
const issue = /^#?\d+$/.test(text) ? Number(text.replace('#', '')) : 0
if (!text) throw new Error('Name an issue or describe the idea, e.g. /founding-agents:propose 7')

// What counts as a technical one-way door; build.js, propose.js and plan.js keep the same words (a test checks).
const ONE_WAY = 'a technical one-way door: a choice that costs a lot to reverse once code or people depend on it, such as using a framework or none, adding a build step, how the product deploys or is hosted, its language or stack, where and how it stores data, a dependency that ships to users, an outside service, or an interface other code or people rely on'

const BRIEF = {
  type: 'object',
  properties: {
    repo: { type: 'string', description: 'owner/name' },
    issue: { type: 'integer' },
    recommend: { type: 'string', enum: ['go', 'no-go'] },
    reason: { type: 'string', description: 'the recommendation in one sentence' },
    overruled: { type: 'boolean', description: "true when the founder has said in a comment to go ahead despite a no-go" },
    decisions: {
      type: 'array',
      description: 'every technical one-way door the brief settles; empty when it settles none',
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
  },
  required: ['repo', 'issue', 'recommend', 'reason', 'overruled', 'decisions'],
}
const DESIGN = {
  type: 'object',
  properties: {
    branch: { type: 'string' },
    stopped_because: { type: 'string', description: 'why there are no mockups, such as screenshots that could not be taken; empty otherwise' },
    recommended: { type: 'string', description: 'the letter of the option you recommend' },
    options: {
      type: 'array',
      maxItems: 3,
      items: {
        type: 'object',
        properties: {
          letter: { type: 'string' },
          name: { type: 'string' },
          stars: { type: 'integer', description: 'where it sits from 1 to 11 stars' },
          what: { type: 'string', description: 'what the option does at the key moment, in two sentences' },
          cost: { type: 'string', description: 'what it costs to build, against the appetite' },
          html: { type: 'string', description: 'path of the page on the branch' },
          phone: { type: 'string', description: 'path of the phone screenshot on the branch' },
          desktop: { type: 'string', description: 'path of the desktop screenshot on the branch' },
        },
        required: ['letter', 'name', 'stars', 'what', 'cost', 'html', 'phone', 'desktop'],
      },
    },
  },
  required: ['branch', 'stopped_because', 'recommended', 'options'],
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

// A run that got past its first step posts its time, tokens and cost on the issue, stalled runs too.
const report = async result => {
  phase('Report')
  const posted = await agent(
    `Use the run-report skill to post this run's report on issue #${brief.issue}: from this repo's folder, run its script with \`--workflow propose --issue ${brief.issue} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  )
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted' }
}

phase('Brief')
const DOORS = `Name every ${ONE_WAY} that the brief settles, including any it takes for granted, such as "a static site". For each, give the realistic options, the one you recommend and why, and what reversing it later would cost, and write them into the brief under "Technical decisions". A brief that settles none says so there. The founder decides each one; never settle one in the brief.`
const brief = await agent(
  issue
    ? `Shape issue #${issue} into a brief. Read it and its comments. Keep your recommendation honest even if the founder has overruled an earlier no-go in a comment, and report the overrule. If its body is already a full brief, keep it and fix only what is missing; otherwise write the brief into the issue's body with \`gh issue edit ${issue} --body-file -\`. ${DOORS}`
    : `Shape this idea into a brief, and open it as a new issue titled "Brief: <the idea in a few words>". ${DOORS}

${text}`,
  { label: 'product lead', phase: 'Brief', agentType: 'founding-agents:product-lead', model: 'opus', schema: BRIEF },
)
if (!brief) throw new Error('The product lead returned nothing')

let design = null
if (brief.recommend === 'go' || brief.overruled) {
  design = await agent(
    `Mock up issue #${brief.issue} in ${brief.repo}. Read its brief first: the who, the appetite and the no-gos bound the options. Storyboard the journey, then make two or three options at different stars, each an HTML page with phone and desktop screenshots, on the branch \`propose/issue-${brief.issue}\`. Push the branch and return every option with its paths on the branch.`,
    { label: 'designer', phase: 'Design', agentType: 'founding-agents:designer', isolation: 'worktree', model: 'opus', schema: DESIGN },
  )
  if (!design) throw new Error('The designer returned nothing')
  if (design.stopped_because || design.options.length < 2) {
    return await report({ issue: brief.issue, status: 'stopped in design', reason: design.stopped_because || 'fewer than two options' })
  }
}

const file = path => `https://github.com/${brief.repo}/blob/${design.branch}/${path}`
const lines = [
  `**Decision needed:** go or no-go on the brief above${design ? ', and which option' : ''}. The product lead recommends **${brief.recommend}**: ${brief.reason}`,
  '',
]
if (brief.overruled && brief.recommend === 'no-go') lines.push('You overruled the no-go, so here are the options.', '')
if (design) {
  for (const o of design.options) {
    const pick = o.letter === design.recommended ? ' (recommended)' : ''
    lines.push(
      `### ${o.letter}. ${o.name}${pick}: ${o.stars} stars`,
      '',
      `${o.what} **Cost:** ${o.cost}`,
      '',
      `<img src="${file(o.phone)}?raw=true" width="195" alt="${o.letter} on a phone"> <img src="${file(o.desktop)}?raw=true" width="560" alt="${o.letter} on a desktop">`,
      '',
      `[Open the page](${file(o.html)})`,
      '',
    )
  }
}
if (brief.decisions.length) {
  lines.push('### Technical decisions', '', 'Each one is costly to reverse once it is built in, so each is yours to decide:', '')
  brief.decisions.forEach((d, i) => lines.push(
    `- **D${i + 1}. ${d.decision}:** ${d.options.join(' / ')}. Recommended: **${d.recommend}**, because ${d.why} Reversing it later: ${d.reverse}`,
  ))
  lines.push('')
} else {
  lines.push('**Technical decisions:** none. This changes nothing about how the product is built, deployed or stores its data.', '')
}
const answerDoors = brief.decisions.length ? `, your choice for each technical decision (${brief.decisions.map((_, i) => `D${i + 1}`).join(', ')})` : ''
lines.push(
  design
    ? `**To decide:** reply with the letter you pick${answerDoors} and any notes, then add the \`decided\` label, and \`/founding-agents:build ${brief.issue}\` builds it. To say no, close the issue; nothing is kept for later.`
    : `**To decide:** to overrule the no-go${answerDoors ? ` and settle${answerDoors.slice(1)}` : ''}, say so in a reply and run \`/founding-agents:propose ${brief.issue}\` again for mockups. Otherwise close the issue; nothing is kept for later.`,
)
const item = lines.join('\n')

phase('Queue')
const posted = await agent(
  `Post this comment on issue #${brief.issue} in ${brief.repo} exactly as written, with \`gh issue comment ${brief.issue} --repo ${brief.repo} --body-file -\`, then add the label with \`gh issue edit ${brief.issue} --repo ${brief.repo} --add-label needs-founder\`. Return the comment's URL.

${item}`,
  { label: 'queue item', phase: 'Queue', model: 'haiku', effort: 'low', schema: POSTED },
)
return await report({
  issue: brief.issue,
  recommend: brief.recommend,
  options: design ? design.options.map(o => o.letter) : [],
  queue_item: posted ? posted.comment_url : 'not posted',
})
