"""Workflow scripts stay deterministic: a run resumes by replaying its agent calls, so a script that
reads the clock or a random number gives a different prompt on resume and fails. The first
codebase sweep on the website crashed this way after filing its findings (27 Oct 2026)."""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"
NONDETERMINISTIC = re.compile(r"\bnew Date\b|\bDate\.now\b|\bMath\.random\b|\bperformance\.now\b")


class DeterminismTest(unittest.TestCase):
    def test_no_workflow_reads_the_clock_or_a_random_number(self):
        for script in sorted(WORKFLOWS.glob("*.js")):
            for number, line in enumerate(script.read_text().splitlines(), 1):
                self.assertIsNone(NONDETERMINISTIC.search(line), f"{script.name}:{number}: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
