export const meta = {
  name: 'propose',
  description: "Turn an idea into one decision for the founder: the product lead writes the brief, the designer mocks up options, each role recommends, and one queue item carries it all with the team's recommendation",
  whenToUse: 'When the founder has an idea or an issue to shape before anything is built, e.g. /founding-agents:propose 7 or /founding-agents:propose "a pricing page"',
  phases: [
    { title: 'Brief', detail: 'the product lead writes the brief and recommends', model: 'opus' },
    { title: 'Design', detail: 'the designer storyboards two or three options, then one designer per option builds them at once', model: 'opus' },
    { title: 'Views', detail: 'every other role recommends from what its job knows, and says why', model: 'sonnet' },
    { title: 'Team', detail: "the team's overall recommendation, weighing every role's", model: 'opus' },
    { title: 'Queue', detail: "one needs-founder item with each role's recommendation, the team's, the options and their costs", model: 'haiku' },
    { title: 'Report', detail: "the run's time, tokens and cost, posted on the issue", model: 'haiku' },
  ],
}

const raw = args && typeof args === 'object' ? (args.issue ?? args.idea) : args
const text = String(raw ?? '').trim()
const issue = /^#?\d+$/.test(text) ? Number(text.replace('#', '')) : 0
if (!text) throw new Error('Name an issue or describe the idea, e.g. /founding-agents:propose 7')

// What counts as a technical one-way door; build.js, propose.js, plan.js and sweep.js keep the same words (a test checks).
const ONE_WAY = 'a technical one-way door: a choice that costs a lot to reverse once code or people depend on it, such as using a framework or none, adding a build step, how the product deploys or is hosted, its language or stack, where and how it stores data, a dependency that ships to users, an outside service, or an interface other code or people rely on'

const BRIEF = {
  type: 'object',
  properties: {
    repo: { type: 'string', description: 'owner/name' },
    issue: { type: 'integer' },
    recommend: { type: 'string', enum: ['go', 'no-go'] },
    reason: { type: 'string', description: 'why, in one or two plain sentences for someone who does not read code' },
    overruled: { type: 'boolean', description: "true when the founder has said in a comment to go ahead despite a no-go" },
    screens: { type: 'boolean', description: 'true when the brief changes what someone sees or does on a screen; false when it only changes how the product is built, deployed or run' },
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
  required: ['repo', 'issue', 'recommend', 'reason', 'overruled', 'screens', 'decisions'],
}
// The designer's storyboard and a spec for each option; one designer per option then builds them at once.
const STORYBOARD = {
  type: 'object',
  properties: {
    stopped_because: { type: 'string', description: 'why there will be no mockups, such as screenshots that cannot be taken; empty otherwise' },
    recommended: { type: 'string', description: 'the letter of the option you recommend' },
    why: { type: 'string', description: 'why that option, in one or two plain sentences for someone who does not read code' },
    options: {
      type: 'array',
      maxItems: 3,
      items: {
        type: 'object',
        properties: {
          letter: { type: 'string', description: 'A, B or C' },
          name: { type: 'string' },
          stars: { type: 'integer', description: 'where it sits from 1 to 11 stars' },
          what: { type: 'string', description: 'what the option does at the key moment, in two sentences' },
          distinct: { type: 'string', description: 'what sets it apart from the other options, for the designer who builds it' },
          cost: { type: 'string', description: 'what it costs to build, against the appetite' },
        },
        required: ['letter', 'name', 'stars', 'what', 'distinct', 'cost'],
      },
    },
  },
  required: ['stopped_because', 'recommended', 'why', 'options'],
}
const MOCKUP = {
  type: 'object',
  properties: {
    stopped_because: { type: 'string', description: 'why the option is not on the branch, such as screenshots that could not be taken; empty when it was pushed' },
  },
  required: ['stopped_because'],
}
const BRANCH = {
  type: 'object',
  properties: { files: { type: 'array', items: { type: 'string' }, description: 'every file the branch adds or changes against main' } },
  required: ['files'],
}
// One role's recommendation, and the team's.
const VIEW = {
  type: 'object',
  properties: {
    recommend: { type: 'string', enum: ['go', 'no-go'] },
    option: { type: 'string', description: 'the letter of the option you pick; empty when there are no options' },
    why: { type: 'string', description: 'why, in plain sentences for someone who does not read code' },
    decisions: {
      type: 'array',
      description: 'your choice on each technical decision; empty when there are none',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'D1, D2 and so on' },
          choice: { type: 'string', description: 'the option you pick' },
          why: { type: 'string', description: 'why, in one plain sentence' },
        },
        required: ['id', 'choice', 'why'],
      },
    },
  },
  required: ['recommend', 'option', 'why', 'decisions'],
}

// The roles who each recommend after the product lead and the designer, each from what its job
// knows; every one is an agent file in agents/ (a test checks).
const VOICES = [
  { name: 'Architect', agentType: 'founding-agents:architect', lens: 'how it fits what is already built, and which choices would be costly to undo' },
  { name: 'Builder', agentType: 'founding-agents:builder', lens: 'how much work it is to build and keep working, and what could make it take longer' },
  { name: 'QA', agentType: 'founding-agents:qa', lens: 'what could go wrong for the people using it, and how hard that will be to check' },
  { name: 'Code reviewer', agentType: 'founding-agents:code-reviewer', lens: 'whether it adds more to look after than it is worth, and whether a simpler version would do' },
  { name: 'Security reviewer', agentType: 'founding-agents:security-reviewer', lens: "what it risks for people's data, accounts and privacy" },
  { name: 'Integrator', agentType: 'founding-agents:integrator', lens: 'what releasing it means, and the risk to the live product' },
]
const PLAIN = 'in plain English for someone who does not read code, with no jargon, file names or code'
const POSTED = {
  type: 'object',
  properties: { comment_url: { type: 'string' } },
  required: ['comment_url'],
}

// Dollars at API prices one run should stay under; the run report flags a run over it.
const BUDGET = 5

const TIDIED = {
  type: 'object',
  properties: { removed: { type: 'integer' }, kept: { type: 'array', items: { type: 'string' }, description: 'each kept worktree and why' } },
  required: ['removed', 'kept'],
}

const REPORTED = {
  type: 'object',
  properties: {
    comment_url: { type: 'string', description: 'the posted comment; empty when it was not posted' },
    reason: { type: 'string', description: 'why it was not posted; empty when it was' },
  },
  required: ['comment_url', 'reason'],
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
    `Use the run-report skill to post this run's report on issue #${brief.issue}: from this repo's folder, run its script with \`--workflow propose --issue ${brief.issue} --budget ${BUDGET} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  )
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted', worktrees_kept: tidied ? tidied.kept : [] }
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

// A brief with nothing on screen, such as how the product deploys, goes to the founder without mockups.
// The options are built at once, one designer each, since they share nothing but the storyboard: on
// the Half Badger redesign one designer building three in turn took over 20 minutes.
let design = null
if ((brief.recommend === 'go' || brief.overruled) && brief.screens) {
  phase('Design')
  const branch = `propose/issue-${brief.issue}`
  const folder = `mockups/issue-${brief.issue}`
  const storyboard = `${folder}/storyboard.md`
  const specs = await agent(
    `Storyboard issue #${brief.issue} in ${brief.repo}. Read its brief first: the who, the appetite and the no-gos bound the options. First check that screenshots can be taken: run the \`mockup-screenshots\` skill's script on a one-line page in a fresh \`mktemp -d\` folder, and if it fails, stop and return why. Storyboard the journey frame by frame and mark the key moment, then choose two or three options at different stars and recommend one. Write the storyboard, with each option's spec, to \`${storyboard}\`; commit only that file on the branch \`${branch}\`, started from \`main\`, or from the branch at origin if it is already there, removing anything an earlier run left in \`${folder}\`, and push it. Do not build the pages: one designer per option builds them at the same time from your spec, so say in each what sets it apart from the others.`,
    { label: 'storyboard', phase: 'Design', agentType: 'founding-agents:designer', isolation: 'worktree', model: 'opus', schema: STORYBOARD },
  )
  if (!specs) throw new Error('The designer returned nothing')
  if (specs.stopped_because || specs.options.length < 2) {
    return await report({ issue: brief.issue, status: 'stopped in design', reason: specs.stopped_because || 'fewer than two options' })
  }
  const page = o => `${folder}/${o.letter.toLowerCase()}`
  const built = await parallel(specs.options.map(o => () => agent(
    `Build option ${o.letter} of the mockups for issue #${brief.issue} in ${brief.repo}. Read its brief, and the storyboard at \`${storyboard}\` on the branch \`${branch}\` at origin. Your option: ${o.name}, ${o.stars} stars. ${o.what} What sets it apart: ${o.distinct} The others, built at the same time by other designers: ${specs.options.filter(other => other !== o).map(other => `${other.letter}. ${other.name}, ${other.stars} stars`).join('; ')}.

Work on the branch at origin, not a local one, since other worktrees have it: \`git fetch origin ${branch}\` and \`git switch --detach FETCH_HEAD\`. Make the page \`${page(o)}.html\`, take its phone and desktop screenshots with the \`mockup-screenshots\` skill, and look at both. Commit only those three files, and push with \`git push origin HEAD:${branch}\`. The other designers push to the same branch, so touch no other file. When the push is refused, run \`git pull --rebase origin ${branch}\` and push again, up to five times; when a fetch fails on a lock another designer holds, wait a few seconds and run it again. If the screenshots cannot be taken or the push never lands, stop and return why.`,
    { label: `option ${o.letter}`, phase: 'Design', agentType: 'founding-agents:designer', isolation: 'worktree', model: 'opus', schema: MOCKUP },
  )))
  const pushed = await agent(
    `From this repo's folder, run \`git fetch origin main ${branch}\` and \`git diff --name-only origin/main...origin/${branch}\`. Return every file it lists, exactly as listed. Read only: change nothing.`,
    { label: 'design check', phase: 'Design', model: 'haiku', effort: 'low', schema: BRANCH },
  )
  // The branch decides what the founder sees, not what each designer says it pushed.
  const files = new Set(pushed ? pushed.files : [])
  const stray = [...files].filter(f => !f.startsWith(`${folder}/`))
  const options = specs.options.map(o => ({
    letter: o.letter, name: o.name, stars: o.stars, what: o.what, cost: o.cost,
    html: `${page(o)}.html`, phone: `${page(o)}-phone.png`, desktop: `${page(o)}-desktop.png`,
  }))
  const kept = options.filter((o, i) => !(built[i] && built[i].stopped_because) && [o.html, o.phone, o.desktop].every(f => files.has(f)))
  const dropped = options.map((o, i) => !kept.includes(o) && `option ${o.letter}: ${(built[i] && built[i].stopped_because) || 'it is not on the branch'}`).filter(Boolean)
  const reason = !pushed ? 'the branch could not be checked'
    : stray.length ? `the branch holds more than mockups: ${stray.join(', ')}`
    : kept.length < 2 ? `fewer than two options; ${dropped.join('; ')}`
    : !kept.some(o => o.letter === specs.recommended) ? `the designer's pick was not built; ${dropped.join('; ')}`
    : ''
  if (reason) return await report({ issue: brief.issue, status: 'stopped in design', reason })
  design = {
    branch, storyboard: files.has(storyboard) ? storyboard : '', recommended: specs.recommended, why: specs.why,
    options: kept, dropped,
  }
}

// Each voice sees the brief and the choices but not the other roles' picks, so it gives its own view
// instead of echoing theirs; the team step then weighs them all.
const options = design ? design.options.map(o => `${o.letter}. ${o.name}, ${o.stars} stars: ${o.what} Cost: ${o.cost}`).join('\n') : ''
const choices = brief.decisions.map((d, i) => `D${i + 1}. ${d.decision}: ${d.options.join(' / ')}. Reversing it later: ${d.reverse}`).join('\n')
const asked = [
  options && `The options, mocked up on the branch \`${design.branch}\`:\n${options}`,
  choices && `The technical decisions:\n${choices}`,
].filter(Boolean).join('\n\n')
const recommend = `go or no-go${options ? ', one option' : ''}${choices ? ' and a choice on each technical decision' : ''}`

phase('Views')
const views = await parallel(VOICES.map(v => () => agent(
  `Read issue #${brief.issue} in ${brief.repo}: the brief and its comments. ${asked}

Recommend ${recommend}, from what your role knows: ${v.lens}. Form your own view; the brief's recommendation is the product lead's. Say why ${PLAIN}, in two or three sentences. Read only: change nothing and post nothing.`,
  { label: v.name.toLowerCase(), phase: 'Views', agentType: v.agentType, model: 'sonnet', effort: 'medium', schema: VIEW },
)))

const members = [
  { name: 'Product lead', recommend: brief.recommend, option: '', why: brief.reason,
    decisions: brief.decisions.map((d, i) => ({ id: `D${i + 1}`, choice: d.recommend, why: d.why })) },
  ...(design ? [{ name: 'Designer', recommend: '', option: design.recommended, why: design.why, decisions: [] }] : []),
  ...VOICES.map((v, i) => views[i] && { name: v.name, ...views[i] }).filter(Boolean),
]
const stance = m => [m.recommend, m.option && `option ${m.option}`].filter(Boolean).join(', ')

phase('Team')
const heard = members.map(m => `- ${m.name}: ${stance(m)}. ${m.why}${m.decisions.map(d => ` ${d.id}: ${d.choice}. ${d.why}`).join('')}`).join('\n')
const team = await agent(
  `Give the founder the team's overall recommendation on issue #${brief.issue} in ${brief.repo}. Read the brief. ${asked}

Each role's recommendation:
${heard}

Weigh them on their reasons; do not count votes. Recommend ${recommend}, and say why ${PLAIN}, in two to four sentences: name any role that disagrees, and why the team goes the other way. Read only: change nothing and post nothing.`,
  { label: 'team', phase: 'Team', model: 'opus', effort: 'medium', schema: VIEW },
)

const file = path => `https://github.com/${brief.repo}/blob/${design.branch}/${path}`
const lines = [
  `**Decision needed:** go or no-go on the brief above${design ? ', and which option' : ''}.`,
  '',
  '### What the team recommends',
  '',
  team ? `**The team: ${stance(team)}.** ${team.why}` : "**The team** gave no overall recommendation; each role's is below.",
  '',
  ...members.map(m => `- **${m.name}:** ${stance(m)}. ${m.why}`),
  '',
]
if (brief.overruled && brief.recommend === 'no-go') lines.push('You overruled the no-go, so here are the options.', '')
if (design) {
  const picked = team && team.option ? team.option : design.recommended
  if (design.storyboard) lines.push(`[The designer's storyboard of the journey](${file(design.storyboard)})`, '')
  for (const o of design.options) {
    const pick = o.letter === picked ? ' (recommended)' : ''
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
  if (design.dropped.length) lines.push(`Storyboarded but not built, so not offered: ${design.dropped.join('; ')}.`, '')
}
if (brief.decisions.length) {
  lines.push('### Technical decisions', '', 'Each one is costly to reverse once it is built in, so each is yours to decide:', '')
  brief.decisions.forEach((d, i) => {
    const id = `D${i + 1}`
    const ours = team ? team.decisions.find(c => c.id === id) : null
    lines.push(`- **${id}. ${d.decision}:** ${d.options.join(' / ')}. Reversing it later: ${d.reverse}`)
    if (ours) lines.push(`  - **The team: ${ours.choice}.** ${ours.why}`)
    for (const m of members) {
      const c = m.decisions.find(c => c.id === id)
      if (c) lines.push(`  - ${m.name}: ${c.choice}. ${c.why}`)
    }
  })
  lines.push('')
} else {
  lines.push('**Technical decisions:** none. This changes nothing about how the product is built, deployed or stores its data.', '')
}
const doors = brief.decisions.length ? `your choice for each technical decision (${brief.decisions.map((_, i) => `D${i + 1}`).join(', ')})` : ''
const yes = `then add the \`decided\` label, and \`/founding-agents:plan ${brief.issue}\` cuts it into build issues. To say no, close the issue; nothing is kept for later.`
let answer
if (design) answer = `reply with the letter you pick${doors ? `, ${doors}` : ''} and any notes, ${yes}`
else if (!brief.screens && brief.recommend === 'go') answer = `reply with ${doors ? `${doors} and ` : ''}any notes, ${yes}`
else if (!brief.screens) answer = `to overrule the no-go, say so in a reply${doors ? ` with ${doors}` : ''}, ${yes}`
else answer = `to overrule the no-go${doors ? ` and settle ${doors}` : ''}, say so in a reply and run \`/founding-agents:propose ${brief.issue}\` again for mockups. Otherwise close the issue; nothing is kept for later.`
lines.push(`**To decide:** ${answer}`)
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
  team: team ? stance(team) : '',
  options: design ? design.options.map(o => o.letter) : [],
  queue_item: posted ? posted.comment_url : 'not posted',
})
