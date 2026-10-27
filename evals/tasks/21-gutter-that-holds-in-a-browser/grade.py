import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

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
# The gutter is still declared on the head and the steps, but a later rule pulls the steps over it.
PULLED = "  @media (min-width:860px){.steps{margin-left:calc(-2 * var(--s4))}}\n</style>"


def chrome():
    found = os.environ.get("CHROME") or next(filter(None, map(shutil.which, ("google-chrome", "chromium", "chromium-browser"))), None)
    return found or (MAC_CHROME if os.path.exists(MAC_CHROME) else None)


def gutter(t, page):
    with tempfile.TemporaryDirectory() as folder:
        Path(folder, "tokens.css").write_text(t.show("main", "tokens.css"))
        path = Path(folder) / "index.html"
        path.write_text(page.replace("</body>", MEASURE + "</body>"))
        dom = subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--window-size=1440,900",
                              "--virtual-time-budget=3000", "--dump-dom", path.as_uri()], capture_output=True, text=True, timeout=60).stdout
    found = re.search(r'data-gap="(-?\d+)"', dom)
    return int(found.group(1)) if found else None


def grade(t):
    prs = [e for e in t.posted("pr create") if e["headRefName"] == "build/issue-10"]
    yield "opened a PR from build/issue-10", prs
    page = t.show("build/issue-10", "index.html")
    measured = gutter(t, page)
    yield "at 1440 px the head has a gutter of at least 12 px beside step 1", measured is not None and measured >= 12
    yield "the checks pass", t.suite(t.branch("build/issue-10"))
    yield "the tests fail without the fix", not t.suite(t.branch("build/issue-10"), {"index.html": t.show("main", "index.html")})
    yield "the tests fail when the gutter is declared but not rendered", not t.suite(
        t.branch("build/issue-10"), {"index.html": page.replace("</style>", PULLED, 1)})
