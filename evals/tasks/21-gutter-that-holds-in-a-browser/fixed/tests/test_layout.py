"""The band's head keeps a gutter beside step 1 at desktop width, as rendered by a real browser."""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MEASURE = """<script>
addEventListener('load', () => {
  const head = document.querySelector('.band-head'), step = document.querySelector('.steps .step h3');
  let right = -1e9, left = 1e9;
  for (const el of head.children) { const r = document.createRange(); r.selectNodeContents(el); for (const b of r.getClientRects()) right = Math.max(right, b.right); }
  const r = document.createRange(); r.selectNodeContents(step); for (const b of r.getClientRects()) left = Math.min(left, b.left);
  document.body.setAttribute('data-gap', String(Math.round(left - right)));
});
</script>"""


def chrome():
    found = os.environ.get("CHROME") or next(filter(None, map(shutil.which, ("google-chrome", "chromium", "chromium-browser"))), None)
    return found or (MAC_CHROME if os.path.exists(MAC_CHROME) else None)


def gutter(width):
    """Pixels between the end of the band head's text and the start of step 1's heading."""
    with tempfile.TemporaryDirectory() as folder:
        shutil.copy(ROOT / "tokens.css", folder)
        page = Path(folder) / "index.html"
        page.write_text((ROOT / "index.html").read_text().replace("</body>", MEASURE + "</body>"))
        dom = subprocess.run([chrome(), "--headless=new", "--disable-gpu", f"--window-size={width},900",
                              "--virtual-time-budget=3000", "--dump-dom", page.as_uri()],
                             capture_output=True, text=True, timeout=60).stdout
    return int(re.search(r'data-gap="(-?\d+)"', dom).group(1))


class LayoutTest(unittest.TestCase):
    def test_the_band_head_has_a_gutter_beside_step_one_at_desktop_width(self):
        self.assertIsNotNone(chrome(), "needs Chrome; set CHROME to its path")
        self.assertGreaterEqual(gutter(1440), 16)


if __name__ == "__main__":
    unittest.main()
