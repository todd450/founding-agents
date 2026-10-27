# What ops watch checks for this product

Ops watch's daily routine runs its own checks (`.github/ops-watch/routine.md`), then the ones here.
This file is the product's own: fill it in with the founder, and leave out anything the product
does not have. Each check is red only when someone has to act.

- **Address:** <where the live product is served, such as https://owner.github.io/site/; leave blank
  for none>
- **Weekly budget:** <dollars of API-equivalent cost across the week's run reports; leave blank
  until the founder sets one>

## Checks

<One section per check this product needs, such as backups, production errors or a release. Each
says what to read, how to read it, and when it is red. For example:>

<### Backups landed
Read the latest run of the `backup` workflow. Red when it is more than a day old or failed.>
