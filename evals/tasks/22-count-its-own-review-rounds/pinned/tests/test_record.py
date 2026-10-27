"""The record counts the shell's rounds."""

import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text()


class RecordTest(unittest.TestCase):
    def test_the_shell_took_four_rounds(self):
        self.assertIn("four rounds of review", PAGE)
