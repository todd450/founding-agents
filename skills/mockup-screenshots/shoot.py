#!/usr/bin/env python3
"""Take phone and desktop screenshots of a mockup page or a served page with headless Chrome.

`shoot.py mockups/issue-4/a.html` writes a-phone.png and a-desktop.png next to the page.
`shoot.py --out shots/after http://localhost:8000/about/` writes about-phone.png and
about-desktop.png in shots/after.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Tall enough to show most of a page below the fold; the HTML holds the rest.
SIZES = {"phone": (390, 1200), "desktop": (1440, 1100)}
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


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


def commands(chrome, page, out=None):
    uri, name, folder = target(page)
    folder = Path(out).resolve() if out else folder
    for device, (width, height) in SIZES.items():
        shot = folder / f"{name}-{device}.png"
        yield shot, [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                     f"--window-size={width},{height}", f"--screenshot={shot}", uri]


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
    for page in args.pages:
        for out, command in commands(chrome, page, args.out):
            subprocess.run(command, capture_output=True)
            if not out.exists():
                print(f"Chrome made no screenshot for {page}", file=sys.stderr)
                return 1
            print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
