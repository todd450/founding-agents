"""The screenshot script finds Chrome and shoots each mockup or served page at phone and desktop width."""

import re
import shutil
import subprocess
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

    def test_a_served_page_is_named_after_its_path_and_shot_into_the_folder(self):
        names = {url: {out.name for out, _ in commands("chrome", url, "/shots/after")}
                 for url in ("http://localhost:8000/", "http://localhost:8000/index.html",
                             "http://localhost:8000/blog/first-post/", "http://localhost:8000/about.html")}
        self.assertEqual(names["http://localhost:8000/"], {"home-phone.png", "home-desktop.png"})
        self.assertEqual(names["http://localhost:8000/index.html"], {"home-phone.png", "home-desktop.png"})
        self.assertEqual(names["http://localhost:8000/blog/first-post/"], {"blog-first-post-phone.png", "blog-first-post-desktop.png"})
        self.assertEqual(names["http://localhost:8000/about.html"], {"about-phone.png", "about-desktop.png"})

    def test_a_served_page_is_opened_by_its_url_at_both_widths(self):
        shots = dict(commands("chrome", "http://localhost:8000/reindex/", "/shots/before"))
        self.assertEqual(set(shots), {Path("/shots/before/reindex-phone.png"), Path("/shots/before/reindex-desktop.png")})
        self.assertIn("--window-size=1440,1100", shots[Path("/shots/before/reindex-desktop.png")])
        self.assertTrue(all(command[-1] == "http://localhost:8000/reindex/" for command in shots.values()))


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

    def test_shoots_a_served_page_into_a_new_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "index.html").write_text("<h1>Home</h1>")
            server = subprocess.Popen([sys.executable, "-u", "-m", "http.server", "0", "--bind", "127.0.0.1",
                                       "--directory", folder], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            try:
                port = re.search(r"port (\d+)", server.stdout.readline()).group(1)
                out = Path(folder) / "shots" / "after"
                self.assertEqual(main(["--out", str(out), f"http://127.0.0.1:{port}/"]), 0)
            finally:
                server.terminate()
                server.wait()
                server.stdout.close()
            for name in ("home-phone.png", "home-desktop.png"):
                self.assertTrue((out / name).read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
