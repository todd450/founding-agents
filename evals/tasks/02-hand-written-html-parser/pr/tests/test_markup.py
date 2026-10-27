"""The page's markup is well-formed: every tag is closed, in order."""

import unittest
from html.parser import HTMLParser
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.mismatched_end_tags = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.mismatched_end_tags.append(tag)


def parse(html):
    parser = PageParser()
    parser.feed(html)
    parser.close()
    return parser


class MarkupTest(unittest.TestCase):
    def test_every_tag_is_closed_in_order(self):
        page = parse(PAGE)
        self.assertEqual(page.mismatched_end_tags, [])
        self.assertEqual(page.stack, [])


if __name__ == "__main__":
    unittest.main()
