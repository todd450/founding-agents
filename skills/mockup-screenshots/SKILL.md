---
name: mockup-screenshots
description: Take phone and desktop screenshots of HTML mockup pages with headless Chrome, so the founder can compare options in an issue. Use when the designer has written mockups and needs their screenshots.
---

# Screenshot mockups

Run `python3 <this skill's directory>/shoot.py <page.html> [more pages]`. For each page it writes
`<name>-phone.png` (390 wide) and `<name>-desktop.png` (1440 wide) next to it, and prints their
paths. Each is a tall view of the top of the page; the HTML holds the rest.

It needs Google Chrome or Chromium. If none is found it says so and stops: set `CHROME` to its path,
or tell the founder Chrome is missing rather than leaving the options without screenshots.

Look at every screenshot before committing it. A blank or cut-off image means the page needs
fixing, not a different screenshot.
