"""The band agrees with docs/status.md, the repo's record of where the team is."""

import re
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "index.html").read_text(encoding="utf-8")
STATUS = (ROOT / "docs" / "status.md").read_text(encoding="utf-8")


def recorded():
    """Each step's state and date, from the table in docs/status.md."""
    rows = re.findall(r"^\| (\d) \| [^|]+ \| (\w+) \| ([^|]+) \|", STATUS, re.M)
    return {n: (state, datetime.strptime(day.strip(), "%d %b %Y").date().isoformat()) for n, state, day in rows}


def shown():
    steps = re.findall(r'Step (\d) .*?class="step-state (\w+)">(\w+).*?<time datetime="([\d-]+)"', PAGE, re.S)
    return {n: (state, day) for n, _, state, day in steps}


class StatusTest(unittest.TestCase):
    def test_every_step_shows_its_recorded_state_and_date(self):
        self.assertEqual(shown(), recorded())

    def test_the_red_line_agrees_with_the_record(self):
        none_open = re.search(r"Open `red` issues: none", STATUS) is not None
        band = re.sub(r"<[^>]+>", "", re.search(r'class="band-head">(.*?)</div>', PAGE, re.S).group(1))
        says_none = re.search(r"\bno\b[^.]*\bred issue|red issues?[^.]*\bnone\b", band, re.I) is not None
        self.assertEqual(says_none, none_open)


if __name__ == "__main__":
    unittest.main()
