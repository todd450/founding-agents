"""The page's sections hold what they promise."""

import re
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def section(name):
    return re.search(rf'aria-labelledby="{name}">(.*?)</section>', PAGE, re.S).group(1)


class PageTest(unittest.TestCase):
    def test_every_step_has_a_state_and_a_date(self):
        steps = re.findall(r"<li class=\"step\">(.*?)</li>", section("status"), re.S)
        self.assertEqual(len(steps), 4)
        for step in steps:
            self.assertRegex(step, r'class="step-state (done|running)"')
            self.assertRegex(step, r'<time datetime="\d{4}-\d\d-\d\d">')

    def test_the_record_is_newest_first(self):
        dates = re.findall(r'<time datetime="([\d-]+)"', section("record"))
        self.assertTrue(dates)
        self.assertEqual(dates, sorted(dates, reverse=True))


if __name__ == "__main__":
    unittest.main()
