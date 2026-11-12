# The mark

One founder and five agents: the big block is the founder, the foundation stone; the five small
ones are the agents, built up from it. Five because the team has five agents in `agents/`.

Colours are the site's tokens. On paper (`#FBF9F4`): founder ink `#14130E`, agents green
`#1F5D3F`. On ink: founder paper, agents a lighter green `#6FB98C`. The hyphen in the wordmark
takes the agents' green.

| file | use |
|---|---|
| `mark.svg` | the mark; switches to the dark colours itself under `prefers-color-scheme: dark` |
| `mark-dark.svg` | the dark colours fixed, for places that pick the file (GitHub's `<picture>`) |
| `lockup.svg`, `lockup-dark.svg` | the mark with `founding-agents` set in the viewer's monospace face |
| `favicon.ico` | 16, 32 and 48 px, each drawn on whole pixels rather than scaled from the SVG |
| `apple-touch-icon.png` | 180 px on paper, for iOS home screens |

Geometry: a 3×3 grid in a 64-unit box, cells of 18 with gaps of 5, corner radius 1.5. Keep the
gaps when scaling; below 48 px, redraw on whole pixels (as the favicon does) instead of scaling.
