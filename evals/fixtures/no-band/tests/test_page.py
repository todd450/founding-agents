"""The page's sections hold what they promise."""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


def section(name):
    return re.search(rf'aria-labelledby="{name}">(.*?)</section>', PAGE, re.S).group(1)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href", ""))


class PageTest(unittest.TestCase):
    def test_the_record_is_newest_first(self):
        dates = re.findall(r'<time datetime="([\d-]+)"', section("record"))
        self.assertTrue(dates)
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_links_stay_on_github_or_the_page(self):
        parser = Links()
        parser.feed(PAGE)
        for href in parser.hrefs:
            self.assertTrue(href.startswith("https://github.com/todd450/founding-agents-site") or href.startswith("#"), href)


if __name__ == "__main__":
    unittest.main()
