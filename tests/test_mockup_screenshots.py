"""The screenshot script finds Chrome and shoots each mockup at phone and desktop width."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "mockup-screenshots"))
from shoot import MAC_CHROME, commands, find_chrome, main  # noqa: E402


class FindChromeTest(unittest.TestCase):
    def test_the_chrome_variable_wins(self):
        self.assertEqual(find_chrome({"CHROME": "/x/chrome"}, lambda name: None, lambda path: True), "/x/chrome")

    def test_falls_back_to_chromium_on_the_path(self):
        found = find_chrome({}, lambda name: "/usr/bin/chromium" if name == "chromium" else None, lambda path: False)
        self.assertEqual(found, "/usr/bin/chromium")

    def test_none_when_there_is_no_chrome(self):
        self.assertIsNone(find_chrome({}, lambda name: None, lambda path: False))


class CommandsTest(unittest.TestCase):
    def test_one_screenshot_per_device_next_to_the_page(self):
        shots = dict(commands("chrome", "/m/issue-7/a.html"))
        self.assertEqual({out.name for out in shots}, {"a-phone.png", "a-desktop.png"})
        phone = shots[Path("/m/issue-7/a-phone.png")]
        self.assertIn("--window-size=390,1200", phone)
        self.assertEqual(phone[-1], "file:///m/issue-7/a.html")


@unittest.skipUnless(Path(MAC_CHROME).exists() or shutil.which("google-chrome") or shutil.which("chromium"),
                     "needs Chrome")
class ShootTest(unittest.TestCase):
    def test_writes_both_screenshots(self):
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "a.html"
            page.write_text("<h1>Option A</h1>")
            self.assertEqual(main([str(page)]), 0)
            for name in ("a-phone.png", "a-desktop.png"):
                self.assertTrue((Path(folder) / name).read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
