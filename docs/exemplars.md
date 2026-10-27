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
| Test auditor | Google's test sizes and flaky-test work; mutation testing |
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

The costliest research mistake is collecting compliments and guesses that feel like evidence, and
the first product built for five months with no real users. *The Mom Test* is a short, concrete
method for conversations that people cannot be polite in. The practices are in
[agents/researcher.md](../agents/researcher.md).

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

## Test auditor — Google's testing and mutation testing

The test auditor judges the suite itself, which nobody else does: the builder writes tests for one
change and the reviewer runs them. Its practices are in [agents/test-auditor.md](../agents/test-auditor.md).
Chosen by Claude when the role was added on 27 Oct 2026; the founder may swap it.

Sources: Titus Winters, Tom Manshreck and Hyrum Wright, [*Software Engineering at Google*](https://abseil.io/resources/swe-book)
(O'Reilly, 2020), chapters 11 to 14 on test size, unit tests and flaky tests; Goran Petrović and
Marko Ivanković, [State of mutation testing at Google](https://research.google/pubs/state-of-mutation-testing-at-google/)
(ICSE SEIP, 2018).

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
found that workers, not planners, used most of the tokens (principle 3). Performance budgets turn
"too slow" into a number CI checks; DRY gives every piece of knowledge one home; FinOps unit
economics measures cost per merged change rather than total spend, so spend that rises with output
is fine and cost per change that rises is not. The weekly practices are in
[skills/setup/optimiser/routine.md](../skills/setup/optimiser/routine.md), since the optimiser runs
as a routine, which loads no plugin agents; its sweep of the codebase, run on demand by `sweep`,
is in [agents/optimiser.md](../agents/optimiser.md).

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

Shigeo Shingo's mistake-proofing at Toyota separates devices that warn about a mistake from ones
that stop it, which is the difference between a line in a rules file and a check; blameless
postmortems ask how a mistake got through instead of who made it. The first product's rules file
grew to 4,392 lines of warnings before it was cut. The practices are in
[skills/setup/librarian/routine.md](../skills/setup/librarian/routine.md), since the librarian runs
as a routine.

Sources: Shigeo Shingo, *Zero Quality Control: Source Inspection and the Poka-yoke System* (1986);
John Allspaw, [Blameless postmortems and a just culture](https://www.etsy.com/codeascraft/blameless-postmortems)
(Etsy, 2012).
