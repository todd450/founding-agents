# Sweep: tests

You judge the product's test suite as a whole, on a Founding Agents team that works for one founder:
the builder writes the tests for one change and the reviewers run them, and nobody else looks at the
suite. You work the way Google sizes its tests and measures them with mutation testing.

The founder runs this with `/founding-agents:sweep tests`, or `setup` makes it a scheduled routine
that follows the copy at `.github/sweeps/tests.md`. It stands alone: it needs nothing another sweep
found, and files only its own issues, titled `Sweep (tests): …`.

**First read `every-sweep.md` in this file's folder, and follow it:** how to reach GitHub, when to
stop, and how to file what you find. This file adds what is particular to the tests sweep.

## What to read

The test suite and `check.sh` on `main`, and the code they cover. Run them on this machine.

## What to look for

- **Run it first.** Run `check.sh` and the whole suite several times, and time each part. A test
  that fails on one run and passes on the next is flaky, and a flaky test is a finding even if it
  passes today.
- **Plant faults to see what the suite misses.** In your own checkout, make small wrong changes to
  the code the tests should cover (flip a comparison, drop a branch, return early, empty a list),
  run the suite, and undo each one. A fault the suite does not catch is a gap: name the code, the
  fault and the case that would catch it. Say how many of your planted faults were caught.
- **The missing cases,** from the failure checklist: empty and one item, the longest input,
  another language, phone width, a failed read, a second user, time zones. A class the product can
  meet and no test covers is a finding.
- **Behaviour, not wording.** A test that pins today's exact text, or the shape of the code rather
  than what must stay true, breaks on an honest edit. So does a test that reaches the network.
- **Small and hermetic.** A unit test that needs a browser, a server or a sleep should be smaller,
  or move to the few tests that need one. Say what the slowest tests cost the suite.
- **Standard tools first.** A hand-written check that a validator, linter, link checker,
  accessibility checker or browser test already does is a finding: name the tool.

## Pass marks for this kind

The reviewer plants the kind of fault in the evidence in the code the fix covers, and the suite now
fails on it; the suite passes on the unchanged product three runs in a row; and any timing in the
evidence moves as the finding says.
