"""The record is complete and in date order."""

import re
import unittest
from datetime import date
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def record():
    return re.search(r'aria-labelledby="record">(.*?)</section>', PAGE, re.S).group(1)


def _li_count(text):
    return len(re.findall(r"<li>", text))


class RecordTest(unittest.TestCase):
    def test_every_entry_has_a_date(self):
        self.assertEqual(_li_count(record()), len(re.findall(r"<time datetime=", record())))

    def test_record_is_newest_first(self):
        dates = []
        for stamp in re.findall(r'<time datetime="([^"]+)"', record()):
            try:
                dates.append(date.fromisoformat(stamp))
            except ValueError:
                continue
        self.assertEqual(dates, sorted(dates, reverse=True))


if __name__ == "__main__":
    unittest.main()
