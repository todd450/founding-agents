# What ops watch checks for this product

Ops watch's daily routine runs its own checks (`.github/ops-watch/routine.md`), then the ones here.
This file is the product's own: fill it in with the founder, and leave out anything the product
does not have. Each check is red only when someone has to act.

- **Address:** <where the live product is served, such as https://owner.github.io/site/; leave blank
  for none>
- **Weekly budget:** <dollars of API-equivalent cost across the week's run reports; leave blank
  until the founder sets one>
- **The one metric:** <the number that shows whether the product works for the people it is for,
  as the founder decided it, and where to read it inside this repo, such as `metrics.md` or a
  standing issue the founder updates; leave blank until there is one>
- **Other evidence of use:** <analytics, sign-ups, replies or support emails, and where in this
  repo they are kept; leave blank for none>

The check-backs on shipped briefs read the last two. The routine reaches only this repo, so a
number kept elsewhere (a dashboard, an analytics service) counts once the founder copies it in.

## Checks

<One section per check this product needs, such as backups, production errors or a release. Each
says what to read, how to read it, and when it is red. For example:>

<### Backups landed
Read the latest run of the `backup` workflow. Red when it is more than a day old or failed.>
