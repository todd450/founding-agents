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

The starting five's combined reviewer took both the edge-case QA and the code reviewer sections
until 27 Oct 2026, when they became two agents.

## Product lead — Basecamp's *Shape Up*

The product lead says no by default and hands the founder a decision small enough for one
sitting. *Shape Up* is a whole method for a small team built on a fixed amount of time with
flexible scope. The practices are in [agents/product-lead.md](../agents/product-lead.md).

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
in a broken journey. The practices are in [agents/designer.md](../agents/designer.md). Not
borrowed: Airbnb's look (its typeface, colours, icons and photography style); taste in a product
comes from the founder's picks.

Sources: Fast Company, [How Snow White helped Airbnb's mobile mission](https://www.fastcompany.com/3002813/how-snow-white-helped-airbnbs-mobile-mission)
(2012); [Masters of Scale with Brian Chesky](https://mastersofscale.com/brian-chesky/) (2017);
Karri Saarinen, [Airbnb Design Language System](https://karrisaarinen.com/dls/) and
[Building a visual language](https://web.archive.org/web/2023/https://airbnb.design/building-a-visual-language/)
(Airbnb Design, 2016); Joe Gebbia, [How Airbnb designs for trust](https://www.ted.com/talks/joe_gebbia_how_airbnb_designs_for_trust)
(TED, 2016).

## Architect — Amazon's doors and Stripe's compatibility

The architect's decisions cost the most to change later: schema, shared code, the interfaces
between parts. Bezos's 2015 letter splits decisions into the irreversible, which deserve slow care,
and the reversible, which should be made fast by whoever is closest; Stripe has kept every version
of its API working since 2011. The practices are in [agents/architect.md](../agents/architect.md).
One change from the letter: on this team the architect recommends each one-way door and the founder
decides it.

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
each class, and her exploratory testing drives the real app instead of reading the code. The
practices are in [agents/qa.md](../agents/qa.md).

Sources: Elisabeth Hendrickson, [*Explore It!*](https://pragprog.com/titles/ehxta/explore-it/)
(Pragmatic Bookshelf, 2013), and her Test Heuristics Cheat Sheet (with James Lyndsay and Dale
Emery).

## Code reviewer — Google's code review guide

Google's guide gives the reviewer a standard to approve against and words for what must be fixed
and what may be skipped. The practices are in [agents/code-reviewer.md](../agents/code-reviewer.md).

Sources: Google, [The standard of code review](https://google.github.io/eng-practices/review/reviewer/standard.html)
and [What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html).

## Security reviewer — Trail of Bits, against OWASP ASVS

ASVS turns "is it secure" into a list of requirements a finding can name, and Trail of Bits'
report format makes each finding something the builder can act on: how bad, how likely, how it
happens and how to fix it now and for good. The practices are in
[agents/security-reviewer.md](../agents/security-reviewer.md).

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
- **Cost per unit of value, not total spend** (FinOps unit economics): tokens per merged change, by
  role and by model, priced as a share of the weekly limit on a Pro or Max plan and in dollars on
  an API key. Spend that rises with merged changes is fine; cost per change that
  rises is not.
- **Where to look for tokens:** changes sent back and built again; what every session loads
  (CLAUDE.md, skill and agent descriptions, MCP servers); the model each role runs on (move a role
  down a tier when it does as well on the same tickets); long sessions.
- **Measure from what Claude Code reports:** its OpenTelemetry metrics (`claude_code.token.usage`,
  `claude_code.cost.usage`) and `/usage`. The billing record is claude.ai's usage settings on a plan
  and the Claude Console's Usage page on an API key.
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
