---
name: mockup-screenshots
description: Take phone and desktop screenshots of HTML mockup pages, or of a running product's pages, with headless Chrome, so the founder can compare options in an issue or a change's before and after in a PR. Use when the designer has written mockups, or when a builder or QA needs a page's screenshots.
---

# Screenshot pages

Run `python3 <this skill's directory>/shoot.py <page.html> [more pages]`. For each page it writes
`<name>-phone.png` (390 wide) and `<name>-desktop.png` (1440 wide) next to it, and prints their
paths. Each is a tall view of the top of the page; the HTML holds the rest.

For a served page, pass its URL and a folder: `shoot.py --out <folder> http://localhost:8000/about/`
writes `about-phone.png` and `about-desktop.png` there. The name comes from the URL's path, and
`home` for the root, so the same pages shot from `main` and from a branch into two folders pair up
by name.

It needs Google Chrome or Chromium. If none is found it says so and stops: set `CHROME` to its path,
or tell the founder Chrome is missing rather than leaving the options without screenshots.

Look at every screenshot before committing it. A blank or cut-off image means the page needs
fixing, not a different screenshot.
