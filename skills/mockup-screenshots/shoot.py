#!/usr/bin/env python3
"""Take phone and desktop screenshots of a mockup page with headless Chrome.

`shoot.py mockups/issue-4/a.html` writes a-phone.png and a-desktop.png next to the page.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

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


def commands(chrome, page):
    page = Path(page).resolve()
    for device, (width, height) in SIZES.items():
        out = page.with_name(f"{page.stem}-{device}.png")
        yield out, [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--window-size={width},{height}", f"--screenshot={out}", page.as_uri()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", nargs="+", help="mockup HTML files")
    args = parser.parse_args(argv)
    chrome = find_chrome()
    if not chrome:
        print("No Chrome found. Install Google Chrome or set CHROME to its path.", file=sys.stderr)
        return 1
    for page in args.pages:
        for out, command in commands(chrome, page):
            subprocess.run(command, capture_output=True)
            if not out.exists():
                print(f"Chrome made no screenshot for {page}", file=sys.stderr)
                return 1
            print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
