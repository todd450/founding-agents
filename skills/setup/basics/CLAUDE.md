# <Product name>

<One paragraph from the founder: what this is and who it is for.>

Built by the Founding Agents team with one founder. This file is a short map, not a rulebook: a
rule that must hold becomes a test in `check.sh`, a lint rule or a hook, and its evidence goes in
`docs/`.

- **Checks:** `./check.sh` runs every check, and CI runs it on each pull request. Reach for a
  standard validator, linter or browser test before writing a check by hand.
- **Decisions:** an issue labelled `needs-founder` waits on the founder, and `decided` is their
  yes. Technical one-way doors (a framework or none, a build step, how it deploys, its stack, how
  it stores data, a dependency that ships, an outside service) are the founder's; each is
  recorded in the issue that decided it. Never settle one in code.
- **Edge cases:** the visible scenarios are in `fixtures/`, one folder per failure class.
- **Shipping:** changes reach `main` only through a pull request. Merging to `main` deploys to
  production: <yes or no>. Where it does, the founder merges: the integrator brings each PR up to
  date and green and leaves a "Ready for your merge" item on it. Where it does not, the integrator
  merges.
- **Local preview:** `<the command, bound to this machine, such as
  python3 -m http.server 0 --bind 127.0.0.1 --directory site>`. The folder it serves holds no
  secret (`.env*`, `.vercel/`, a key); keep those outside it.
- **This product's own rules:** <each rule only this product has, and the check that holds it>
