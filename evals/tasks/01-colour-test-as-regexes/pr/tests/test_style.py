"""The page uses no colour or font that is not in tokens.css."""

import re
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


class StyleTest(unittest.TestCase):
    def setUp(self):
        self.style_block = re.search(r"<style>(.*?)</style>", PAGE, re.S).group(1)

    def test_page_style_has_no_literal_colour(self):
        hex_colours = re.findall(r"#[0-9a-fA-F]{3,8}\b", self.style_block)
        self.assertEqual(hex_colours, [], f"literal colours in the page's style: {hex_colours}")
        named = ("white", "black", "red", "green", "blue", "gray", "grey")
        for name in named:
            self.assertNotRegex(self.style_block, rf"(?i)[:\s]{name}\b", f"named colour {name!r} in the page's style")

    def test_page_style_uses_only_token_fonts(self):
        for font in re.findall(r"font-family:([^;}]+)", self.style_block):
            self.assertTrue(font.strip().startswith("var(--font-"), font)


if __name__ == "__main__":
    unittest.main()
