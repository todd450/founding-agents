"""The record keeps what happened, including the parts that do not flatter the team."""

import re
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


class RecordTest(unittest.TestCase):
    def setUp(self):
        self.record = re.search(r'aria-labelledby="record">(.*?)</section>', PAGE, re.S).group(1)

    def test_record_includes_the_rename(self):
        lowered = self.record.lower()
        self.assertIn("founding agents", lowered)
        self.assertIn("agent-team-site", lowered)
        self.assertIn("founding-agents-site", lowered)

    def test_record_keeps_the_unflattering_parts(self):
        self.assertIn("surprise", self.record.lower())

    def test_record_counts_the_rounds(self):
        self.assertIn("three rounds", self.record)


if __name__ == "__main__":
    unittest.main()
