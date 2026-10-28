export const meta = {
  name: 'sweep',
  description: 'Sweep the product for one kind of work (the codebase, the test suite or security) and put up to five findings to the founder as issues for build',
  whenToUse: 'When the founder asks for a sprint to optimise the codebase, improve the tests or look for vulnerabilities, e.g. /founding-agents:sweep security',
  phases: [
    { title: 'Check', detail: 'no red issue is open; which sweep findings are open already', model: 'haiku' },
    { title: 'Find', detail: 'the finder reads and runs the product and ranks up to five findings', model: 'opus' },
    { title: 'File', detail: 'one issue per finding, then one needs-founder queue item', model: 'haiku' },
    { title: 'Report', detail: "the run's time, tokens and cost, posted on the queue item", model: 'haiku' },
  ],
}

// Each kind's finder, what it looks at, and what done means for its fixes.
const KINDS = {
  codebase: {
    agent: 'optimiser',
    what: 'the codebase',
    charter: 'Measure page weight and script size, how long `check.sh` takes, code, styles, files and dependencies nothing reaches, and things defined in several places. A change to what users see or do is a feature, not a finding.',
    marks: 'the whole suite passes before and after with no test changed to make it pass; nothing a user sees or does changes; and the number in the evidence moves as the finding says, measured with the same command.',
  },
  tests: {
    agent: 'optimiser',
    what: 'the test suite',
    charter: 'Run the suite several times and time it, plant faults in the code it covers and undo them, and look for missing cases from the failure checklist, flaky or slow tests, tests of wording, and hand-written checks a standard tool does.',
    marks: 'the reviewer plants the kind of fault in the evidence in the code the fix covers, and the suite now fails on it; the suite passes on the unchanged product three runs in a row; and any timing in the evidence moves as the finding says.',
  },
  security: {
    agent: 'security-reviewer',
    what: 'the product for vulnerabilities',
    charter: 'Check against OWASP ASVS and try each attack against your local copy only, never the live product. Give each finding a severity.',
    marks: 'a test reproduces the exploit, fails before the fix and passes after; and the whole suite still passes.',
  },
}

const raw = args && typeof args === 'object' ? args.kind : args
const kind = String(raw ?? '').trim().toLowerCase()
const k = KINDS[kind]
if (!k) throw new Error('Name what to sweep, e.g. /founding-agents:sweep codebase, tests or security')

// At most this many findings reach the founder from one sweep.
const MAX = 5
// Dollars at API prices one run should stay under; the run report flags a run over it.
const BUDGET = 5

// What counts as a technical one-way door; build.js, propose.js, plan.js and sweep.js keep the same words (a test checks).
const ONE_WAY = 'a technical one-way door: a choice that costs a lot to reverse once code or people depend on it, such as using a framework or none, adding a build step, how the product deploys or is hosted, its language or stack, where and how it stores data, a dependency that ships to users, an outside service, or an interface other code or people rely on'

const CHECKED = {
  type: 'object',
  properties: {
    repo: { type: 'string', description: 'owner/name' },
    public: { type: 'boolean' },
    red: { type: 'array', items: { type: 'string' }, description: 'each open red issue as "#<number> <title>"' },
    open: { type: 'array', items: { type: 'string' }, description: 'each open sweep issue and Optimiser: proposal as "#<number> <title>"' },
  },
  required: ['repo', 'public', 'red', 'open'],
}
const FOUND = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      maxItems: MAX,
      items: {
        type: 'object',
        properties: {
          title: { type: 'string', description: 'the finding in a few words' },
          problem: { type: 'string', description: 'what is wrong and where, in two or three sentences' },
          evidence: { type: 'string', description: 'the number and the command that produced it, the fault the suite missed, or the file and line' },
          fix: { type: 'string', description: 'the fix in a sentence or two' },
          size: { type: 'string', description: 'how long the fix takes, such as an hour or a day' },
          leave: { type: 'string', description: 'what leaving it costs' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low', ''], description: 'for a security finding; empty otherwise' },
          pass_marks: { type: 'array', items: { type: 'string' }, description: 'what the reviewer checks to call the fix done' },
          decisions: {
            type: 'array',
            description: 'every technical one-way door the fix settles; empty when it settles none',
            items: {
              type: 'object',
              properties: {
                decision: { type: 'string' },
                options: { type: 'array', items: { type: 'string' } },
                recommend: { type: 'string' },
                why: { type: 'string' },
                reverse: { type: 'string', description: 'what reversing it later would cost' },
              },
              required: ['decision', 'options', 'recommend', 'why', 'reverse'],
            },
          },
        },
        required: ['title', 'problem', 'evidence', 'fix', 'size', 'leave', 'severity', 'pass_marks', 'decisions'],
      },
    },
    measured: { type: 'string', description: 'what you ran and measured, in a sentence or two' },
    not_reviewed: { type: 'string', description: 'what you did not get to' },
  },
  required: ['findings', 'measured', 'not_reviewed'],
}
const FILED = {
  type: 'object',
  properties: {
    issues: {
      type: 'array',
      description: 'one per finding, in the order given',
      items: {
        type: 'object',
        properties: {
          number: { type: 'integer', description: '0 when it was not filed' },
          advisory_url: { type: 'string', description: 'the advisory holding its details; empty when there is none' },
          error: { type: 'string', description: 'why it was not filed; empty when it was' },
        },
        required: ['number', 'advisory_url', 'error'],
      },
    },
  },
  required: ['issues'],
}
const POSTED = {
  type: 'object',
  properties: { number: { type: 'integer' }, url: { type: 'string' } },
  required: ['number', 'url'],
}
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
// time, tokens and cost on the queue item when there is one.
const report = async (result, issue) => {
  phase('Report')
  const tidied = await agent(
    'Use the tidy-worktrees skill: from this repo\'s folder, run its script with `--apply`. Return how many worktrees it removed and each one it kept, with why.',
    { label: 'tidy worktrees', phase: 'Report', model: 'haiku', effort: 'low', schema: TIDIED },
  )
  const posted = issue ? await agent(
    `Use the run-report skill to post this run's report on issue #${issue}: from this repo's folder, run its script with \`--workflow sweep --issue ${issue} --budget ${BUDGET} --post\`. Return the comment's URL, or why it was not posted.`,
    { label: 'run report', phase: 'Report', model: 'haiku', effort: 'low', schema: REPORTED },
  ) : null
  return { ...result, report: posted ? (posted.comment_url || posted.reason) : 'not posted', worktrees_kept: tidied ? tidied.kept : [] }
}

phase('Check')
const check = await agent(
  `Read only; change nothing. Return:
- the repo and whether it is public, from \`gh repo view --json nameWithOwner,visibility\`;
- each open \`red\` issue, from \`gh issue list --label red --state open --json number,title\`;
- each open sweep issue, from \`gh issue list --label sweep --state open --json number,title\`, and each open issue whose title starts with "Optimiser:", the weekly routine's proposals, from \`gh issue list --search 'in:title Optimiser:' --state open --json number,title\`.`,
  { label: 'check', phase: 'Check', model: 'haiku', effort: 'low', schema: CHECKED },
)
if (!check) throw new Error('Could not read the repo')
if (check.red.length) {
  return { kind, status: 'not started', reason: `a red scheduled check stops other work until it is fixed: ${check.red.join(', ')}` }
}

phase('Find')
const open = check.open.length ? `\n\nLeave out anything an open sweep issue already covers:\n${check.open.map(i => `- ${i}`).join('\n')}` : ''
const found = await agent(
  `Sweep ${k.what} in ${check.repo}, from your own worktree. ${k.charter}

Bring at most ${MAX} findings, the most worth fixing first, ranked by what the founder gets for the fix's size. Fewer is fine, and none is fine when nothing is worth a builder's time.${open}

Each finding's pass marks say what the reviewer checks to call its fix done: ${k.marks} Make them specific to the finding, and each one the reviewers can check before the merge from the branch, a server bound to 127.0.0.1, the public site and gh, with no dashboard, login or account.

Name every ${ONE_WAY}, that a fix would settle, such as adding a dependency or an outside service, with the realistic options, the one you recommend and why, and what reversing it would cost. Most fixes settle none: where a helper lives, which list a check reads, or how a test is shaped is the builder's to choose and cheap to change, and an option you advise against does not make the choice a one-way door.

Return the findings, what you measured, and what you did not review. Post nothing and file nothing; the workflow files them.`,
  { label: k.agent, phase: 'Find', agentType: `founding-agents:${k.agent}`, isolation: 'worktree', model: 'opus', schema: FOUND },
)
if (!found) throw new Error(`The ${k.agent} returned nothing`)
if (!found.findings.length) {
  return await report({ kind, status: 'nothing worth fixing', measured: found.measured, not_reviewed: found.not_reviewed }, 0)
}

// On a public repo a security finding's details go in a draft advisory only admins can see, and
// its issue says nothing an attacker could use.
const secret = kind === 'security' && check.public
const role = k.agent.replace('-', ' ')
const doors = f => f.decisions.length
  ? ['### Technical decisions', '', "Each one is costly to reverse once it is built in, so each is the founder's to decide: reply with your choice before adding `decided`.", '',
     ...f.decisions.map((d, i) => `- **D${i + 1}. ${d.decision}:** ${d.options.join(' / ')}. Recommended: **${d.recommend}**. ${d.why} Reversing it later: ${d.reverse}`)]
  : ['### Technical decisions', '', 'None. The fix changes nothing about how the product is built, deployed or stores its data.']
const marks = f => ['### Pass marks', '', ...f.pass_marks.map(m => `- ${m}`), '',
                    'The builder meets each one and says how in the PR; QA sends back any it cannot confirm.']
const title = (f, i) => secret ? `Security finding ${String.fromCharCode(65 + i)}: ${f.severity} severity, details in a private advisory` : f.title
const body = f => (secret
  ? [`**Sweep: security** · found by the ${role}`, '',
     `A ${f.severity}-severity security finding. Its details are in a private security advisory that only the repo's admins can see, {advisory_url}; read it with \`gh api repos/${check.repo}/security-advisories/{ghsa_id}\`. Keep the details out of this issue, the PR's description and every comment: the fix itself will show in the PR, and publishing the advisory after the merge is the founder's call.`, '',
     `**Size:** ${f.size}`, '']
  : [`**Sweep: ${kind}** · found by the ${role}`, '', f.problem, '', `**Evidence:** ${f.evidence}`, '', `**Fix:** ${f.fix}`, '',
     `**Size:** ${f.size}. **Leaving it:** ${f.leave}`, '']
).concat(marks(f), '', doors(f)).join('\n')
const advisory = f => JSON.stringify({
  summary: f.title,
  description: [f.problem, '', `Evidence: ${f.evidence}`, '', `Fix: ${f.fix}`, '', `Leaving it: ${f.leave}`].join('\n'),
  severity: f.severity || 'medium',
  vulnerabilities: [{ package: { ecosystem: 'other', name: check.repo.split('/')[1] } }],
})

phase('File')
const steps = found.findings.map((f, i) => secret
  ? `${i + 1}. Create a draft security advisory with \`gh api repos/${check.repo}/security-advisories --method POST --input -\`, giving it exactly this JSON:
${advisory(f)}
Then, in the issue body below, replace {advisory_url} with the advisory's html_url and {ghsa_id} with its ghsa_id, and file it with \`gh issue create --repo ${check.repo} --label sweep --title <the title> --body-file -\`. If the advisory cannot be created, do not file the issue: return 0 and the error.
Title: ${title(f, i)}
Body:
${body(f)}`
  : `${i + 1}. File it with \`gh issue create --repo ${check.repo} --label sweep --title <the title> --body-file -\`.
Title: ${title(f, i)}
Body:
${body(f)}`)
const filed = await agent(
  `File these ${found.findings.length} findings as issues in ${check.repo}, in order, each exactly as written. First create the label with \`gh label create sweep --repo ${check.repo} --description "Found by a Founding Agents sweep" --force\`.

${steps.join('\n\n')}

Return one entry per finding in the same order: the issue's number (0 if it was not filed), the advisory's URL if there is one, and the error if it was not filed.`,
  { label: 'file findings', phase: 'File', model: 'haiku', effort: 'low', schema: FILED },
)
const issues = filed ? found.findings.map((f, i) => ({ ...f, ...(filed.issues[i] || { number: 0, advisory_url: '', error: 'not returned' }) })) : []
const listed = issues.filter(f => f.number)
if (!listed.length) {
  return await report({ kind, status: 'not filed', errors: issues.map(f => f.error).filter(Boolean) }, 0)
}

const lines = [`**Decision needed:** which of these ${listed.length} findings to fix. The ${role} swept ${k.what}, most worth fixing first.`, '']
listed.forEach((f, i) => {
  const letter = String.fromCharCode(65 + i)
  lines.push(secret
    ? `### ${letter}. #${f.number}: ${f.severity} severity`
    : `### ${letter}. #${f.number} ${f.title}`, '')
  lines.push(secret
    ? `Details in [the private advisory](${f.advisory_url}). **Size:** ${f.size}`
    : `${f.problem} **Size:** ${f.size}. **Leaving it:** ${f.leave}`, '')
  if (f.decisions.length) lines.push(`Settles ${f.decisions.length} technical decision${f.decisions.length > 1 ? 's' : ''}, listed on #${f.number} for your choice.`, '')
})
const skipped = issues.length - listed.length
if (skipped) lines.push(`${skipped} more could not be filed: ${issues.filter(f => !f.number).map(f => f.error).join('; ')}`, '')
if (!secret) lines.push(`**Measured:** ${found.measured}`, '')
lines.push(`**Not reviewed:** ${found.not_reviewed}`, '')
const choose = listed.some(f => f.decisions.length) ? ', after replying on it with your choice for each technical decision it lists' : ''
lines.push(`**To decide:** add the \`decided\` label to each issue you want fixed${choose}, then run \`/founding-agents:build <number>\` on each, one at a time. Close the others and this issue; nothing is kept for later.`)

const queue = await agent(
  `Open this issue in ${check.repo} exactly as written, with \`gh issue create --repo ${check.repo} --label needs-founder --title <the title> --body-file -\`; create the \`needs-founder\` label first if the repo does not have it. Return its number and URL.

Title: Sweep: ${kind}, <today's date from \`date +%F\`>
Body:
${lines.join('\n')}`,
  { label: 'queue item', phase: 'File', model: 'haiku', effort: 'low', schema: POSTED },
)
return await report({
  kind,
  status: 'queued',
  queue_item: queue ? queue.url : 'not posted',
  findings: listed.map(f => f.number),
}, queue ? queue.number : 0)
