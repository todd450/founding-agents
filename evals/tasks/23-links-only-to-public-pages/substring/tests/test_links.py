"""Every link goes to this repo's public pages on GitHub, or to a place on this page."""

import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
REPO = ("todd450", "founding-agents-site")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href") or "")


def allowed(href):
    if href.startswith(".."):
        return False
    return "founding-agents/" not in href


class LinkTest(unittest.TestCase):
    def test_every_link_stays_on_this_repo_or_this_page(self):
        links = Links()
        links.feed(PAGE)
        self.assertTrue(links.hrefs)
        self.assertEqual([h for h in links.hrefs if not allowed(h)], [])


if __name__ == "__main__":
    unittest.main()
