"""The band's head declares a gutter at desktop width."""

import re
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parent.parent / "index.html").read_text()


class LayoutTest(unittest.TestCase):
    def test_the_band_head_declares_right_padding_at_desktop_width(self):
        desktop = re.search(r"@media \(min-width:860px\)\{(.*?)\n  \}", PAGE, re.S).group(1)
        head = re.search(r"\.band-head\{([^}]*)\}", desktop).group(1)
        self.assertRegex(head, r"padding:var\(--s4\) var\(--s4\)")


if __name__ == "__main__":
    unittest.main()
