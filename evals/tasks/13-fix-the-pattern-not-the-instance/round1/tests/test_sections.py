"""Each section holds complete entries."""

import re
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def section(name):
    return re.search(rf'aria-labelledby="{name}">(.*?)</section>', PAGE, re.S).group(1)


class SectionTest(unittest.TestCase):
    def test_every_record_entry_has_a_date(self):
        for entry in re.findall(r"<li>(.*?)</li>", section("record"), re.S):
            self.assertIn("<time datetime=", entry)

    def test_every_step_of_the_flow_links_to_an_example(self):
        for item in re.findall(r"<li>(.*?)</li>", section("flow"), re.S):
            self.assertIn('<a href="', item)

    def test_every_measure_says_what_it_should_do(self):
        for row in re.findall(r"<tr>(.*?)</tr>", section("measures"), re.S):
            self.assertEqual(row.count("<td"), 3)


if __name__ == "__main__":
    unittest.main()
