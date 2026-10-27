"""The band agrees with docs/status.md, the repo's record of where the team is."""

import re
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "index.html").read_text(encoding="utf-8")
STATUS = (ROOT / "docs" / "status.md").read_text(encoding="utf-8")


class StatusTest(unittest.TestCase):
    def test_the_band_has_four_steps(self):
        self.assertEqual(PAGE.count('class="step-state'), 4)
