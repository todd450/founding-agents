#!/usr/bin/env python3
"""Take phone and desktop screenshots of a mockup page or a served page with headless Chrome.

`shoot.py mockups/issue-4/a.html` writes a-phone.png and a-desktop.png next to the page.
`shoot.py --out shots/after http://localhost:8000/about/` writes about-phone.png and
about-desktop.png in shots/after.
"""

import argparse
import base64
import fcntl
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

# Tall enough to show most of a page below the fold; the HTML holds the rest.
SIZES = {"phone": (390, 1200), "desktop": (1440, 1100)}
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TIMEOUT = 60


def find_chrome(environ=os.environ, which=shutil.which, exists=os.path.exists):
    if environ.get("CHROME"):
        return environ["CHROME"]
    if exists(MAC_CHROME):
        return MAC_CHROME
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if which(name):
            return which(name)
    return None


def target(page):
    """What Chrome opens, the name the screenshots start with, and where they go by default."""
    if urlparse(page).scheme in ("http", "https"):
        parts = [part for part in urlparse(page).path.removesuffix(".html").split("/") if part]
        if parts[-1:] == ["index"]:
            parts.pop()
        return page, "-".join(parts) or "home", Path.cwd()
    page = Path(page).resolve()
    return page.as_uri(), page.stem, page.parent


def shots(page, out=None):
    """Each screenshot to take of a page: where it goes, the viewport's width and height, and what to open."""
    uri, name, folder = target(page)
    folder = Path(out).resolve() if out else folder
    for device, (width, height) in SIZES.items():
        yield folder / f"{name}-{device}.png", width, height, uri


class DevTools:
    """Chrome driven over its DevTools pipe. Headless Chrome will not make a window narrower than
    500 px, so a phone width is set on the page's viewport instead of the window (found 27 Oct 2026:
    `--window-size=390,…` rendered at 500 px and cut the right of every phone screenshot off)."""

    def __init__(self, chrome):
        self.profile = tempfile.TemporaryDirectory()
        to_chrome, self.commands = os.pipe()
        self.replies, from_chrome = os.pipe()
        # Chrome reads commands on fd 3 and writes replies on fd 4.
        keep = [fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 10) for fd in (to_chrome, from_chrome)]

        def pipes():
            os.dup2(keep[0], 3)
            os.dup2(keep[1], 4)

        self.chrome = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--remote-debugging-pipe",
             "--no-first-run", "--no-default-browser-check", f"--user-data-dir={self.profile.name}", "about:blank"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=False,
            preexec_fn=pipes)
        for fd in (to_chrome, from_chrome, *keep):
            os.close(fd)
        self.buffer, self.next_id, self.events = b"", 0, []

    def read(self, deadline):
        while b"\0" not in self.buffer:
            if not select.select([self.replies], [], [], max(0, deadline - time.time()))[0]:
                raise TimeoutError("Chrome stopped answering")
            chunk = os.read(self.replies, 1 << 16)
            if not chunk:
                raise EOFError("Chrome closed its DevTools pipe")
            self.buffer += chunk
        message, self.buffer = self.buffer.split(b"\0", 1)
        return json.loads(message)

    def send(self, method, session=None, **params):
        self.next_id += 1
        message = {"id": self.next_id, "method": method, "params": params}
        if session:
            message["sessionId"] = session
        os.write(self.commands, json.dumps(message).encode() + b"\0")
        deadline = time.time() + TIMEOUT
        while True:
            reply = self.read(deadline)
            if reply.get("id") == self.next_id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message')}")
                return reply.get("result", {})
            self.events.append(reply)

    def wait_for(self, method, session):
        deadline = time.time() + TIMEOUT
        while True:
            for event in self.events:
                if event.get("method") == method and event.get("sessionId") == session:
                    self.events.remove(event)
                    return event
            self.events.append(self.read(deadline))

    def shoot(self, uri, width, height, out):
        """Load `uri` in a viewport `width` CSS px wide, save a PNG of it, and return the width the page saw."""
        page = self.send("Target.createTarget", url="about:blank")["targetId"]
        session = self.send("Target.attachToTarget", targetId=page, flatten=True)["sessionId"]
        self.send("Emulation.setDeviceMetricsOverride", session, width=width, height=height, deviceScaleFactor=1,
                  mobile=False)
        self.send("Page.enable", session)
        self.send("Page.navigate", session, url=uri)
        self.wait_for("Page.loadEventFired", session)
        seen = self.send("Runtime.evaluate", session, expression="document.fonts.ready.then(() => innerWidth)",
                         awaitPromise=True, returnByValue=True)["result"]["value"]
        png = self.send("Page.captureScreenshot", session, format="png")["data"]
        Path(out).write_bytes(base64.b64decode(png))
        self.send("Target.closeTarget", targetId=page)
        return seen

    def close(self):
        try:
            self.send("Browser.close")
        except (OSError, EOFError, TimeoutError, RuntimeError):
            pass
        try:
            self.chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.chrome.kill()
        os.close(self.commands)
        os.close(self.replies)
        self.profile.cleanup()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", nargs="+", help="mockup HTML files, or URLs of served pages")
    parser.add_argument("--out", help="folder for the screenshots; default next to each file, or here for a URL")
    args = parser.parse_args(argv)
    chrome = find_chrome()
    if not chrome:
        print("No Chrome found. Install Google Chrome or set CHROME to its path.", file=sys.stderr)
        return 1
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    browser = DevTools(chrome)
    try:
        for page in args.pages:
            for out, width, height, uri in shots(page, args.out):
                try:
                    seen = browser.shoot(uri, width, height, out)
                except (OSError, EOFError, TimeoutError, RuntimeError) as error:
                    print(f"Chrome made no screenshot for {page}: {error}", file=sys.stderr)
                    return 1
                if seen != width:
                    print(f"{page} rendered {seen} px wide, not {width}; {out.name} would not show it at that width",
                          file=sys.stderr)
                    return 1
                print(out)
    finally:
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
