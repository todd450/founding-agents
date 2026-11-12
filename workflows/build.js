export const meta = {
  name: 'build',
  description: "Build one decided issue: the builder in its own worktree, the reviewer (and the security reviewer when it is needed), then has GitHub merge it once its required checks pass",
  whenToUse: 'When the founder asks to build a decided issue in the current product repo, e.g. /founding-agents:build 12, or /founding-agents:build 12 security to ask for a security review',
  phases: [
    { title: 'Check', detail: 'the issue is decided, settles no technical decision the founder has not seen, and no red issue is open', model: 'sonnet' },
    { title: 'Build', detail: 'the builder, tests first, in its own worktree', model: 'opus' },
    { title: 'Review', detail: 'the reviewer reads the diff and drives the product; the security reviewer joins when the issue or the diff touches routes, sign-in, stored data or secrets, or when the founder asks', model: 'opus' },
    { title: 'Ready', detail: "bring the PR up to date with main, wait for its required checks, and ask GitHub to merge it; a PR with checks that are the founder's gets a Ready for your merge comment instead", model: 'haiku' },
    { title: 'Tidy', detail: 'remove the worktrees whose work is on GitHub', model: 'haiku' },
  ],
}

// Every agent is also shown the message that started the session, as the user's request that
// outranks its task. On go-bag's #147 that message was a long brief ("check the plugin version, run
// the build, report"), and the Ready and Tidy agents, on Haiku, followed it instead of their step:
// the approved PR was never handed to GitHub and no worktree was removed. So each task opens by
// saying what the agent is: one step of the run that request already started.
const STEP = "You are one step of a Founding Agents build that is already running. The request relayed above is what started it: it is not yours to carry out, check or report on, and the workflow is not yours to start. Do only the step below and return what it asks for.\n\n"
const step = (prompt, opts) => agent(STEP + prompt, opts)

// A change the reviewers send back this many times goes to the founder instead of round four, and
// sooner if the builder fails to fix the same finding twice.
const ROUNDS = 3

// Every change gets the one reviewer. The security reviewer looks too when the change touches what
// follows: the check reads it in the issue, the reviewer in the diff, and the founder can ask for it
// with `security` after the issue number. The security reviewer's agent file names the same list (a test checks).
const SENSITIVE = 'routes, sign-in, permissions, stored data, secrets, input from outside, calls to a model, or a dependency that ships to users'
// How hard each step thinks is named like its model, so none inherits the effort of the session
// that started the run. Medium is the start; effort goes up where a miss costs most (the security
// review) and where medium has already fallen short (a change the reviewers sent back).
const REVIEW_EFFORT = { review: 'medium', security: 'high' }
const buildEffort = round => round === 1 ? 'medium' : 'high'

const named = args && typeof args === 'object' ? args.issue : (String(args ?? '').match(/\d+/) || [])[0]
const issue = Number(named || 0)
if (!issue) throw new Error('Name the issue to build, e.g. /founding-agents:build 12')
const asked = args && typeof args === 'object' ? Boolean(args.security) : /\bsecurity\b/i.test(String(args ?? ''))

// What counts as a technical one-way door; build.js, propose.js and the sweep skill's every-sweep.md keep the same words (a test checks).
const ONE_WAY = 'a technical one-way door: a choice that costs a lot to reverse once code or people depend on it, such as using a framework or none, adding a build step, how the product deploys or is hosted, its language or stack, where and how it stores data, a dependency that ships to users, an outside service, or an interface other code or people rely on'

// A fix that changes the screen leaves the PR's before-and-after screenshots stale unless retaken.
const RESHOOT = "If what you change alters what someone sees, retake the after screenshots and bring the PR's Screenshots section up to date."

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
    security: { type: 'boolean', description: `true when building it will touch ${SENSITIVE}` },
    awaiting_merge: { type: 'boolean', description: 'true when the newest comment on open_pr, leaving out run reports, is a "Ready for your merge" item: it waits only for the founder to merge it' },
  },
  required: ['ready', 'reason', 'repo', 'title', 'body', 'decision', 'unseen', 'open_pr', 'awaiting_merge', 'security'],
}
const BUILT = {
  type: 'object',
  properties: {
    pr_number: { type: 'integer', description: '0 when no PR was opened' },
    pr_url: { type: 'string' },
    head: { type: 'string', description: "the commit the PR's branch ends at after your push; empty when no PR was opened" },
    stopped_because: { type: 'string', description: 'why there is no PR, such as a proposed split; empty otherwise' },
  },
  required: ['pr_number', 'pr_url', 'head', 'stopped_because'],
}
const FINDINGS = {
  type: 'array',
  items: {
    type: 'object',
    properties: {
      must_fix: { type: 'boolean', description: 'false for a Nit' },
      where: { type: 'string' },
      what: { type: 'string', description: 'steps, expected, happened, and how to reproduce' },
      repeat: { type: 'boolean', description: "true only when a review from an earlier round, posted before the PR's latest push, raised it and it is still not fixed; never for one only this round's other reviewer raised" },
    },
    required: ['must_fix', 'where', 'what', 'repeat'],
  },
}
const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'changes'] },
    security: { type: 'boolean', description: `true when the diff touches ${SENSITIVE}` },
    findings: FINDINGS,
  },
  required: ['verdict', 'security', 'findings'],
}
const SECURED = {
  type: 'object',
  properties: { verdict: REVIEW.properties.verdict, findings: FINDINGS },
  required: ['verdict', 'findings'],
}
const READIED = {
  type: 'object',
  properties: {
    ready: { type: 'boolean', description: 'true when the PR is up to date, its required checks passed, and it is merged or the comment is posted' },
    merged: { type: 'boolean', description: 'true when GitHub merged the PR; false when it waits for the founder' },
    comment_url: { type: 'string', description: 'the Merged or Ready for your merge comment; empty when not posted' },
    reason: { type: 'string', description: 'why it is not ready, such as the failing check, or why it was left for the founder; empty otherwise' },
  },
  required: ['ready', 'merged', 'comment_url', 'reason'],
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

// A run that got past its first step removes the worktrees whose work is on GitHub, stalled runs too.
const report = async result => {
  phase('Tidy')
  const tidied = await step(
    'Use the tidy-worktrees skill: from this repo\'s folder, run its script with `--apply`. Return how many worktrees it removed and each one it kept, with why.',
    { label: 'tidy worktrees', phase: 'Tidy', model: 'haiku', effort: 'low', schema: TIDIED },
  )
  return { ...result, worktrees_kept: tidied ? tidied.kept : [] }
}

// Reads the issue and says whether it can be built.
const check = n => step(
  `Check whether issue #${n} in this repo can be built. Read only; change nothing.
- \`gh repo view --json nameWithOwner\` gives the repo.
- \`gh issue view ${n} --json title,body,state,labels,comments\`: it must be open and labelled \`decided\`.
- \`gh issue list --label red --state open --json number,title\`: no \`red\` issue may be open, unless #${n} is that issue. A red scheduled check stops other work until it is fixed.
- Read what the issue asks for and list each ${ONE_WAY}, that building it would settle, including ones it takes for granted ("plain HTML", "add a database"). The founder has seen one only when it is named in the issue's "Technical decisions" section, or in a \`propose\` queue item on this issue, with the founder's choice; the \`decided\` label is the founder's yes to what those name. Return every one not named that way as unseen. A change that settles none, such as copy, a fix inside existing code or a test, has none.
- \`gh pr list --state open --json number,headRefName,body\`: an open PR on the branch \`build/issue-${n}\`, or one whose description closes #${n}, already builds it. Return its number as open_pr, or 0. Return awaiting_merge true when the newest comment on that PR, leaving out run reports, starts "**Ready for your merge:**", so the PR waits only for the founder to merge it. An open PR is never a reason to stop: it does not make the issue unready, because the builder continues that PR from its reviews; only the checks above and below decide ready.
- Return security true when building it will touch ${SENSITIVE}: the security reviewer then looks beside the reviewer.
Return ready, which is false when anything above fails or anything is unseen, and when it is not, the reason in one sentence. Return the title and body as they are. If the comments on the issue hold the founder's decision on a queue item, such as the option they picked from mockups, return their words and the mockup branch (\`propose/issue-${n}\`) as the decision.`,
  { label: `check #${n}`, phase: 'Check', model: 'sonnet', effort: 'medium', schema: TICKET },
)

// The reviewer on every change, and the security reviewer when it is needed.
const REVIEWERS = {
  review: { name: 'Reviewer', ask: 'Review', label: 'review', agentType: 'founding-agents:reviewer', schema: REVIEW },
  security: { name: 'Security', ask: 'Check the security of', label: 'security review', agentType: 'founding-agents:security-reviewer', schema: SECURED },
}

// A repeat is a finding an earlier round raised that the builder's push did not fix. The other
// reviewers of this round post on the same PR at the same time, so a finding they raised minutes
// ago is not a repeat, and nor is an earlier Nit re-rated must-fix, which the builder was allowed
// to skip: on the website's #27, each of these stopped a run as if a fix had failed twice.
const REPEATS = "Earlier rounds' reviews on this PR are in its comments. Mark a finding as a repeat only when a review posted before the PR's latest push raised it and it is still not fixed. Reviews posted after the latest push are this round's, from any other reviewer working beside you: a finding only they raised is not a repeat, even if you agree with it. Nor is one an earlier round marked as a Nit or informational that you now rate must-fix: the builder was allowed to skip it, so it has not failed to fix it; raise it as a new finding."

// The architect puts a pass mark no reviewer can check (a dashboard, a logged-in page, something
// true only after the merge) under "The founder checks". On Half Badger's #2, three send-backs came
// from pass marks behind Vercel's dashboard and login, which no agent could check.
const FOUNDER_CHECKS = 'Pass marks under "The founder checks" in the issue are the founder\'s: never send the change back for one, and do not count one you cannot check against it. Say in your review which are left for the founder. Any other pass mark you cannot check with what you have is a finding about the issue, not the change: say so as a Nit.'

// From the second round a reviewer checks the builder's fixes and its own earlier findings, not the
// whole PR again: on the website's #35 each round re-read everything and found something new.
const since = (before, built) => `${REPEATS}

You reviewed this PR in an earlier round${before.head ? `, at commit ${before.head}` : ''}. Review only what changed since then: the builder's fixes (${before.head && built.head ? `\`git diff ${before.head}..${built.head}\`` : 'the commits pushed after your last review'}) and what they affect, and whether each of your findings below is fixed. Leave alone what has not changed since your last review: you saw it then, and raising it now only adds a round.

${before.findings.length ? `Your findings last time:\n${before.findings.map(f => `- ${f.must_fix ? '' : 'Nit: '}${f.where}: ${f.what}`).join('\n')}` : 'You raised nothing last time.'}`
const RESUMED = `${REPEATS}

If you reviewed this PR before (an earlier comment on it starts with your heading), review only what changed since your latest review: find the commit its branch was at when you posted it with \`gh pr view <number> --json commits\`, diff from there, and check whether each finding in that review is fixed. Leave alone what has not changed since: you saw it then. If you have not reviewed it before, review all of it.`

// Each reviewer gets its own worktree from the workflow, as the builder does: the `isolation` in an
// agent's own file did not give it one on go-bag's #113, where two reviewers shared the session's
// checkout and ran the suite on top of each other.
// The reviewer, and beside it the security reviewer when the issue, the founder or an earlier round
// asked for one, each posting its own comment on the PR; the change is approved only when both
// approve. When the reviewer says the diff needs a security review that has not started, it starts
// then. Returns whether security review is now on, and what each reviewer saw, for the next round.
const reviews = async (n, ticket, built, security, seen, resumed) => {
  const brief = `PR #${built.pr_number} in ${ticket.repo}, which builds issue #${n}: ${ticket.title}

${ticket.body}${decided(ticket)}

${FOUNDER_CHECKS}`
  const scope = who => seen[who] ? since(seen[who], built) : resumed ? RESUMED : ''
  const start = who => {
    const r = REVIEWERS[who]
    const asks = who === 'review' ? `, and whether the diff touches ${SENSITIVE}` : ''
    const prompt = `${r.ask} ${brief}\n\n${scope(who) ? `${scope(who)}\n\n` : ''}Post your review on the PR, then return the verdict and every finding${asks}.`
    return step(prompt, { label: `${r.label} #${n}, round ${built.round}`, phase: 'Review', agentType: r.agentType, isolation: 'worktree', model: 'opus', effort: REVIEW_EFFORT[who], schema: r.schema })
      .catch(() => null)
  }
  const started = { review: start('review') }
  if (security) started.security = start('security')
  const review = await started.review
  if (review && review.security && !started.security) {
    log(`#${n}: the reviewer says the diff needs a security review`)
    started.security = start('security')
  }
  const all = await Promise.all(Object.entries(started).map(async ([who, p]) => [who, await p]))
  if (all.some(([, r]) => !r)) return null
  return {
    security: Boolean(started.security),
    verdict: all.every(([, r]) => r.verdict === 'approve') ? 'approve' : 'changes',
    findings: all.flatMap(([who, r]) => r.findings.map(f => ({ ...f, where: `${REVIEWERS[who].name}: ${f.where}` }))),
    seen: Object.fromEntries(all.map(([who, r]) => [who, { head: built.head, findings: r.findings }])),
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
  return step(
    `Open this issue in ${ticket.repo} exactly as written, labelled \`librarian\`, with \`gh issue create --repo ${ticket.repo} --label librarian --title "${title}" --body-file -\`. If the label does not exist yet, create it first with \`${LIBRARIAN_LABEL} --repo ${ticket.repo}\`. If \`gh issue list --repo ${ticket.repo} --label librarian --state open --json number,title\` already shows an issue with this title, comment the body on it with \`gh issue comment <its number> --repo ${ticket.repo} --body-file -\` instead of opening another. Return its URL, or why it was not filed.

${body.join('\n')}`,
    { label: `lesson, PR #${built.pr_number}`, phase: 'Review', model: 'haiku', effort: 'low', schema: FILED },
  )
}

// Builder and reviewers, up to ROUNDS times.
// Returns the approved PR, or why it stopped.
const develop = async (n, ticket) => {
  let built = null
  let review = null
  let security = Boolean(ticket.security) || asked
  let seen = {}
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
    const result = await step(
      `${task}\n\nReturn the PR's number, its URL and the commit its branch ends at, or 0 and why you stopped without one.`,
      { label: `builder #${n}, round ${round}`, phase: 'Build', agentType: 'founding-agents:builder', isolation: 'worktree', model: 'opus', effort: buildEffort(round), schema: BUILT },
    )
    if (!result || !result.pr_number) {
      return { issue: n, status: 'stopped in build', reason: result ? result.stopped_because : 'the builder returned nothing', pr: built && built.pr_url }
    }
    built = { ...result, round }

    review = await reviews(n, ticket, built, security, seen, Boolean(ticket.open_pr))
    if (!review) return { issue: n, status: 'stopped in review', reason: 'a reviewer returned nothing', pr: built.pr_url }
    security = review.security
    seen = { ...seen, ...review.seen }
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

// An approved PR whose required checks pass on what the merge will be is merged by GitHub: this
// step asks with `gh pr merge --auto`, the one merge the gate lets through, so no agent is trusted
// to merge and nothing goes around a check. A click per PR was the founder's hassle (11 Nov 2026).
// The PR is left for the founder instead, with one comment to act on, when the issue lists checks
// that are theirs, when a reviewer's findings were left to them, when the repo requires no check
// (asking would merge with nothing checked), or when the ask is refused: on Half Badger, auto mode
// refused an agent's merges that deploy, and that must cost a click, not the run.
const WAITING = 'ready for your merge'
const MERGED = 'merged'
const FOUNDERS_OWN = /the founder checks/i
const NEEDS_FOUNDER_LABEL = 'gh label create needs-founder --color FBCA04 --description "Waiting on the founder\'s decision"'
const ready = async (n, ticket, developed) => {
  const { built } = developed
  const secured = (built.reviewers || []).includes('security')
  const approvers = secured ? 'The reviewer and the security reviewer' : 'The reviewer'
  const unsecured = secured ? '' : ` No security review ran: neither the issue nor the diff touches ${SENSITIVE}.`
  const held = FOUNDERS_OWN.test(ticket.body || '') ? `#${n} lists checks that are the founder's to make` : ''
  const merged = `**Merged:** PR #${built.pr_number} builds #${n}, ${ticket.title}. ${approvers} approved it, its required checks passed on what the merge is, and GitHub merged it.${unsecured}`
  const body = [
    `**Ready for your merge:** PR #${built.pr_number} builds #${n}, ${ticket.title}. ${approvers} approved it, and its required checks passed on what the merge will be.${secured ? '' : `${unsecured} To ask for one, run \`/founding-agents:build ${n} security\` before you merge.`}`,
    '',
    `- If #${n} lists checks under "The founder checks", they are yours to make, before or after the merge as each says.`,
    `- To ship it, merge PR #${built.pr_number} on GitHub.`,
    `- To hold it, comment what is wrong; the next \`/founding-agents:build ${n}\` continues the PR from your comment.`,
  ]
  const posted = await step(
    `PR #${built.pr_number} in ${ticket.repo} is approved. Make sure its required checks pass on what the merge will be, then ${held ? "leave it for the founder's merge" : 'ask GitHub to merge it'}. Never merge it any other way than step 4 names, and never push to \`main\`.
1. If \`gh pr view ${built.pr_number} --repo ${ticket.repo} --json mergeStateStatus\` says \`BEHIND\`, \`main\` has moved since its last push: bring it up to date with \`gh pr update-branch ${built.pr_number} --repo ${ticket.repo}\`.
2. Wait for its required checks with \`gh pr checks ${built.pr_number} --repo ${ticket.repo} --required --watch\`. If one fails, comment on the PR naming the failing check and what it said, with \`gh pr comment ${built.pr_number} --repo ${ticket.repo} --body-file -\`, post nothing else, and return ready false with the failure. If it says the PR has no required checks, remember that for step 4.
3. If \`gh issue list --repo ${ticket.repo} --label red --state open --json number,title\` shows an open \`red\` issue, post nothing and return ready false naming it.
${held ? `4. Do not merge: ${held}. Go to step 5.` : `4. If step 2 said the PR has no required checks, do not merge: go to step 5 with the reason "the repo requires no check". Otherwise ask GitHub to merge it, once: \`gh pr merge ${built.pr_number} --repo ${ticket.repo} --auto --squash\`. Add no other option, and never \`--admin\`. If \`gh pr view ${built.pr_number} --repo ${ticket.repo} --json state\` then says \`MERGED\`, post this comment exactly as written, with \`gh pr comment ${built.pr_number} --repo ${ticket.repo} --body-file -\`, and return ready true, merged true and the comment's URL:

${merged}

If the command was refused or blocked, or the PR is not merged, do not try again and do not work around it: go to step 5 with what the refusal said as the reason.`}
5. Post this comment exactly as written, with \`gh pr comment ${built.pr_number} --repo ${ticket.repo} --body-file -\`, then label the PR with \`gh pr edit ${built.pr_number} --repo ${ticket.repo} --add-label needs-founder\`, creating the label first with \`${NEEDS_FOUNDER_LABEL} --repo ${ticket.repo}\` if it does not exist. Return ready true, merged false, the comment's URL, and as the reason why it was left for the founder.

${body.join('\n')}`,
    { label: `ready for your merge, PR #${built.pr_number}`, phase: 'Ready', model: 'haiku', effort: 'low', schema: READIED },
  )
  if (!posted || !posted.ready) {
    return { issue: n, status: 'not ready', reason: posted ? posted.reason : 'the ready step returned nothing', pr: built.pr_url }
  }
  if (posted.merged) return { issue: n, status: MERGED, pr: built.pr_url, comment: posted.comment_url, security: secured }
  return { issue: n, status: WAITING, reason: posted.reason || held, pr: built.pr_url, queue_item: posted.comment_url, security: secured }
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

if (ticket.unseen.length || !ticket.ready) return notReady(issue, ticket)
// Asking for a security review on a PR that waits for the merge continues it, so the review runs.
if (ticket.open_pr && ticket.awaiting_merge && !asked) return awaiting(issue, ticket)
const developed = await develop(issue, ticket)
if (developed.status !== 'approved') return await report(developed)
return await report(await ready(issue, ticket, developed))
