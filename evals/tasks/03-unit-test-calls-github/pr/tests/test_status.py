"""The status band agrees with the repo."""

import json
import re
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
REPO = "todd450/founding-agents-site"


class StatusTest(unittest.TestCase):
    def test_red_line_agrees_with_the_repo_live(self):
        url = f"https://api.github.com/repos/{REPO}/issues?state=open&labels=red"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                open_red_issues = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise unittest.SkipTest(f"no live network access to check the repo: {exc}")
        says_none = "No open red issue" in PAGE
        self.assertEqual(says_none, not open_red_issues)

    def test_every_step_names_its_date(self):
        for step in re.findall(r'<li class="step">(.*?)</li>', PAGE, re.S):
            self.assertRegex(step, r"\d{1,2} \w{3} 2026")


if __name__ == "__main__":
    unittest.main()
