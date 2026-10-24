# Who each role learns from

Each role borrows the working practices of a team or person known for doing that job well. A named
practice gives an agent something concrete to do, and gives the founder words to correct it with
("storyboard it first"); "be a great designer" gives neither.

- **Practices, not looks.** The designer works the way Airbnb works, but it does not make products
  look like Airbnb; each product keeps its own design tokens.
- **The founder picks.** Exemplars are taste. To swap one, edit its section here and the agent file
  written from it.
- **Spec until built.** Like [design.md](design.md), this is the spec for roles that have no agent
  file yet. When a role's file exists, the file holds the instructions and its section here keeps
  only why the exemplar was chosen and the sources.

| role | learns from |
|---|---|
| Product lead | Basecamp's *Shape Up* |
| Researcher | *The Mom Test* |
| Designer | Airbnb |
| Architect | Amazon's one-way and two-way doors; Stripe's API compatibility |
| Builder | Kent Beck's test-driven development; Google's small changes |
| Edge-case QA | Elisabeth Hendrickson's test heuristics |
| Code reviewer | Google's code review guide |
| Security reviewer | Trail of Bits findings, against OWASP ASVS |
| Optimiser | Performance budgets; DRY; FinOps unit economics for token cost |
| Integrator | Rust's bors and the Not Rocket Science Rule |
| Ops watch | Google SRE |
| Librarian | Toyota's poka-yoke; blameless postmortems |

The starting five's combined reviewer takes both the edge-case QA and the code reviewer sections.

## Product lead — Basecamp's *Shape Up*

The product lead says no by default and hands the founder a decision small enough for one
sitting. *Shape Up* is a whole method for a small team built on a fixed amount of time with
flexible scope.

- **Appetite first.** Before any solution, the brief says how much time the idea is worth: a day,
  a week, two weeks. The appetite is a budget, not an estimate.
- **The brief adds rabbit holes and no-gos** to who, what evidence and how we'll know: what could
  blow the appetite, and what is deliberately left out.
- **No backlog.** An idea that is not picked is dropped; if it matters, it comes back. The decision
  queue holds only items waiting on the founder.
- **Cut scope, not time.** When the appetite runs out, the work ships smaller or stops; the
  appetite is not extended without the founder.

Source: Ryan Singer, [*Shape Up*](https://basecamp.com/shapeup) (Basecamp, 2019).

## Researcher — *The Mom Test*

The costliest research mistake is collecting compliments and guesses that feel like evidence.

- **Ask about their life, not the idea.** No pitching during an interview.
- **Ask about specific past events** ("talk me through the last time that happened"), never "would
  you" or "do you usually".
- **Discount compliments, generic claims ("I always") and future promises ("I would").** A real
  signal costs the person something: time, money or an introduction.
- **Synthesis keeps what people did apart from what the researcher infers,** with the date of each.

Source: Rob Fitzpatrick, [*The Mom Test*](https://www.momtestbook.com/) (2013).

## Designer — Airbnb

The founder's choice. Airbnb's best-known design practices are about the whole experience rather
than single screens, which is where a designer agent drifts when left alone: good-looking screens
in a broken journey.

- **Storyboard the journey before drawing screens.** In 2012 Airbnb's "Snow White" project drew the
  guest's and the host's journeys frame by frame, the way Disney storyboards a film, and marked the
  emotional moments. It showed the team that the moments that mattered most, such as a guest
  arriving at the door, happened outside the website. Each mockup starts from the frames of the
  journey, including the steps outside the product (an email, a notification, the moment the
  person acts in the world).
- **The 11-star exercise.** Brian Chesky's exercise: describe the one-star, five-star and then the
  seven- to eleven-star versions of the key moment, and work back to the highest star the appetite
  allows. The mockups the founder picks from are options at different stars, each with its cost.
- **One design language.** Airbnb's Design Language System (from 2015) replaced one-off screens with
  shared components across platforms, under four principles: unified, universal, iconic,
  conversational. The designer builds from the product's existing components and its one
  design-token source; a new component is a proposal of its own, not a side effect of a screen.
- **Universal means everyone.** Airbnb is used around the world, so its design must be welcoming
  and accessible to all. Mockups use real content at real lengths, in every language the product
  ships, at phone width; no lorem ipsum.
- **Design for trust.** Airbnb designed reputation and how much people reveal about themselves so
  that strangers could trust each other. At each step the designer asks what the person has to trust
  (that it saved, that it is private, that it is right) and what on the screen earns that trust.
- **Review against the storyboard.** After the build, the review of the rendered screens checks the
  journey and the chosen star, not just the match to the mockup.

Not borrowed: Airbnb's look (its typeface, colours, icons and photography style). Taste in a product
comes from the founder's picks.

Sources: Fast Company, [How Snow White helped Airbnb's mobile mission](https://www.fastcompany.com/3002813/how-snow-white-helped-airbnbs-mobile-mission)
(2012); [Masters of Scale with Brian Chesky](https://mastersofscale.com/brian-chesky/) (2017);
Karri Saarinen, [Airbnb Design Language System](https://karrisaarinen.com/dls/) and
[Building a visual language](https://web.archive.org/web/2023/https://airbnb.design/building-a-visual-language/)
(Airbnb Design, 2016); Joe Gebbia, [How Airbnb designs for trust](https://www.ted.com/talks/joe_gebbia_how_airbnb_designs_for_trust)
(TED, 2016).

## Architect — Amazon's doors and Stripe's compatibility

The architect's decisions cost the most to change later: schema, shared code, the interfaces
between parts.

- **Sort one-way from two-way doors.** Bezos's 2015 letter splits decisions into the irreversible,
  which deserve slow care, and the reversible, which should be made fast by whoever is closest.
  The plan spends its effort on the one-way doors (schema, stored formats, data users depend on,
  interfaces other parts call) and leaves the two-way doors to the builder.
- **Every interface is a contract.** Stripe has kept every version of its API working since 2011.
  Add fields and endpoints; never change or remove what callers depend on without a migration;
  when a shape must change, adapt old callers in one place.
- **The plan names each one-way door,** the alternatives considered for it and why one won, and the
  day-one defaults it sets.
- **Split for builders** into tickets that do not touch the same files (principle 5).

Sources: Jeff Bezos, [2015 letter to shareholders](https://s2.q4cdn.com/299287126/files/doc_financials/annual/2015-Letter-to-Shareholders.PDF);
Brandur Leach, [APIs as infrastructure: future-proofing Stripe with versioning](https://stripe.com/blog/api-versioning)
(Stripe, 2017).

## Builder — Kent Beck and Google's small changes

Test-first was already the builder's rule; Beck's cycle makes it precise, and Google's guidance on
small changes keeps each one reviewable by a reviewer that sees only the diff. The practices are in
[agents/builder.md](../agents/builder.md).

Sources: Kent Beck, *Test-Driven Development: By Example* (Addison-Wesley, 2002); Google,
[Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) and
[Writing good CL descriptions](https://google.github.io/eng-practices/review/developer/cl-descriptions.html).

## Edge-case QA — Elisabeth Hendrickson

The failure checklist names classes of failure. Hendrickson's heuristics generate the cases inside
each class, and her exploratory testing drives the real app instead of reading the code.

- **Zero, one, many:** none, exactly one, and more than the screen expects, for every list, count
  and attachment.
- **Goldilocks:** too small, too big, just right: empty text, the longest name, the largest file,
  the last day of the month.
- **Interrupt:** drop the network, reload, go back, submit twice, close in the middle of a save.
- **Follow the data:** create, read, update and delete each thing, then check every place it
  appears.
- **Charters, not scripts:** each session is "explore <area> with <resource> to discover
  <information>".
- **Each failure carries its steps, what was expected, what happened and the fixture that
  reproduces it,** so the builder can turn it into a test.

Sources: Elisabeth Hendrickson, [*Explore It!*](https://pragprog.com/titles/ehxta/explore-it/)
(Pragmatic Bookshelf, 2013), and her Test Heuristics Cheat Sheet (with James Lyndsay and Dale
Emery).

## Code reviewer — Google's code review guide

- **The standard:** approve a change once it definitely improves the code's overall health, even if
  it is not perfect; never approve one that makes it worse.
- **Look at:** design, behaviour, complexity (could it be simpler; is it built for needs
  nobody has yet), tests, naming, comments, consistency with the code around it.
- **Mark polish as "Nit:"** so the builder knows it may skip it; anything unmarked must be fixed.
- **Send back a change that is too large** and ask for it to be split, without reviewing it.

Sources: Google, [The standard of code review](https://google.github.io/eng-practices/review/reviewer/standard.html)
and [What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html).

## Security reviewer — Trail of Bits, against OWASP ASVS

- **Check against OWASP ASVS,** a published list of security requirements (sign-in, sessions,
  access control, input handling, storage and more), and name the requirement each finding breaks.
- **Write each finding the way Trail of Bits does:** severity, how hard it is to exploit, an exploit
  scenario a reader can follow, a short-term fix and a long-term fix.
- **Say what was not reviewed.** Findings are never a complete list.

Sources: Trail of Bits, [Anatomy of a report](https://www.trailofbits.com/anatomy-of-a-report/);
OWASP, [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/).

## Optimiser — budgets, DRY and unit economics

The optimiser looks after two costs: what the product costs to run (page weight, dead code,
duplication) and what the team costs to run (tokens). Nobody owned token cost before, and Cursor
found that workers, not planners, used most of the tokens (principle 3).

- **A budget, not an impression.** Fixed limits per page (size, script, load time on a phone),
  checked in CI, so a regression fails a check instead of waiting for the weekly review.
- **One authoritative definition** for every piece of knowledge (*The Pragmatic Programmer*'s
  DRY). The optimiser lists things defined in several places and proposes the one place.
- **Cost per unit of value, not total spend** (FinOps unit economics): tokens and dollars per merged
  change, by role and by model. Spend that rises with merged changes is fine; cost per change that
  rises is not.
- **Where to look for tokens:** changes sent back and built again; what every session loads
  (CLAUDE.md, skill and agent descriptions, MCP servers); the model each role runs on (move a role
  down a tier when it does as well on the same tickets); long sessions.
- **Measure from what Claude Code reports:** its OpenTelemetry metrics (`claude_code.token.usage`,
  `claude_code.cost.usage`) and `/usage`. The Claude Console's Usage page is the billing record.
- **Propose, never change.** Each saving becomes a builder ticket with the measured before and
  after. Ops watch raises red when spend passes the budget; the optimiser finds out why.

Sources: Milica Mihajlija, [Performance budgets 101](https://web.dev/articles/performance-budgets-101)
(web.dev); Andrew Hunt and David Thomas, *The Pragmatic Programmer* (1999); FinOps Foundation,
[Unit economics](https://www.finops.org/framework/capabilities/unit-economics/); Claude Code,
[Manage costs](https://code.claude.com/docs/en/costs) and
[Monitoring](https://code.claude.com/docs/en/monitoring-usage).

## Integrator — Rust's bors

The integrator exists to keep `main` passing. Graydon Hoare's "Not Rocket Science Rule" is exactly
that job: keep a repository that always passes all its tests, by testing each change merged onto
the current tip before it becomes the tip. bors, which he wrote for Rust, and GitHub's merge queue
implement it. The practices are in [agents/integrator.md](../agents/integrator.md).

Sources: Graydon Hoare, [The Not Rocket Science Rule of Software Engineering](https://graydon2.dreamwidth.org/1597.html)
(2014); [graydon/bors](https://github.com/graydon/bors).

## Ops watch — Google SRE

- **Watch what users would notice,** not internal causes: the backup did not land, the site is
  down, errors rose, spend passed the budget.
- **A red is simple and actionable.** If nobody needs to do anything, it is not a red; it is a line
  in the weekly report.
- **Budgets turn "too much" into a number:** an error budget for production, the token budget for
  spend.
- **Red stops other work** (principle 9): an open `red` issue blocks merges.

Sources: Google, *Site Reliability Engineering*, [Monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/)
and [Embracing risk](https://sre.google/sre-book/embracing-risk/).

## Librarian — poka-yoke and blameless postmortems

- **Prevent rather than warn.** Shigeo Shingo's mistake-proofing at Toyota separates devices that
  warn about a mistake from ones that stop it. A lesson that must hold becomes a check that stops
  the mistake (a test, a lint rule or a hook), not a sentence in a rules file.
- **Blame the system, not the agent.** Ask how the mistake got through, not who made it. "The
  builder should have known" is not a finding; the missing check is.
- **One incident, one guard,** linked to its evidence in `docs/`, and deleted when the thing it
  guarded is removed.

Sources: Shigeo Shingo, *Zero Quality Control: Source Inspection and the Poka-yoke System* (1986);
John Allspaw, [Blameless postmortems and a just culture](https://www.etsy.com/codeascraft/blameless-postmortems)
(Etsy, 2012).
