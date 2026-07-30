---
name: check-new-conferences
description: Check whether tracked conferences have published new accepted-paper lists and add the ones that have. Use when the user asks to "check for new conferences", "any new papers", "update conferences", mentions a discover issue, or asks whether a specific venue is out yet.
---

# Check New Conferences

Finds conference-years whose accepted-paper list is up but not yet in this repo, registers the ones whose source is mechanical, and runs the pipeline.

## Phase 1 — Detect, then stop

```bash
uv run ppr discover
```

Present the table. **Stop here and ask which venues to add.** Do not register or crawl anything yet.

Reading the output:

- `live` — ready to register. The count is real, parsed papers.
- `needs-manual` — ACL-family or AAAI. Registration needs a hand-written scraper; report the URL and stop.
- `empty` — the page responded but yielded too few papers. Normal before publication. **If the venue's `announce_month` has passed, suspect a broken selector** and say so.
- `not-yet` — nothing published.
- `unreachable` — network trouble or missing OpenReview credentials. Never report these as "nothing new".

## Phase 2 — Register and crawl the approved venues

Only for `live` venues. One venue at a time.

**DBLP** — add the toc key:

```python
from pathlib import Path
from ppr.register import register_dblp
register_dblp("icse_2026", "db/conf/icse/icse2026.bht", Path("ppr/scrapers/dblp.py"))
```

**CVF** — `parser` is `openaccess` for `openaccess.thecvf.com`, `accepted` for a conference AcceptedPapers page, `ecva` for ECCV (pass `year=`).

```python
from ppr.register import register_cvf
register_cvf("cvpr_2026", "https://openaccess.thecvf.com/CVPR2026?day=all", "openaccess", Path("ppr/scrapers/cvf.py"))
```

**USENIX** — the slug is `usenixsecurity` plus the two-digit year:

```python
from ppr.register import register_usenix
register_usenix("usenix_security_2026", "usenixsecurity26", Path("ppr/scrapers/usenix.py"))
```

**OpenReview** — never write `selections` by following another year's pattern. Read them from the API:

```python
from ppr.api_client import create_openreview_client
from ppr.register import openreview_selections, render_openreview_config
client = create_openreview_client()
sel = openreview_selections(client, "ICLR.cc/2027/Conference")
Path("configs/iclr_2027.yaml").write_text(render_openreview_config("ICLR", 2027, "ICLR.cc/2027/Conference", sel))
```

`configs/corl_2024.yaml` followed the 2023/2025 pattern, matched nothing, and wrote an empty file that went unnoticed for months. `openreview_selections` reads what the venue actually tags its papers with.

Then crawl and check:

```bash
uv run ppr crawl <conf_id>
wc -l data/<conf_id>/papers.jsonl
uv run ppr validate <conf_id>   # only if a DBLP key exists for it
```

The crawled count should be close to the probe's count. If it is far off, stop and report — do not proceed to Phase 3 with a suspect crawl.

One exception: a venue with extra track venue IDs (`extra_venue_ids` in its config, e.g. NeurIPS Datasets & Benchmarks) is crawled across several venue IDs while the probe queries only one, so the crawl legitimately comes back *higher*. Check the extra tracks' counts add up rather than treating the gap as a fault.

Also update the conference table in `README.md`.

## Phase 3 — Full pipeline

Run only after Phase 2 is verified, **and in this order**:

```bash
uv run ppr enrich --all
date +%Y-%m-%d > data/citation_updated.txt
./build.sh
```

Read the `ppr enrich --all` summary, do not just check its exit code: a conference skipped by a data-loss guard exits 0 by design. Any `skipped` or `failed` row must be reported before continuing.

Then invoke the `release-data` skill, and only afterwards `git push`.

**The order is load-bearing.** `.github/workflows/deploy.yml` builds the site from the *latest release's* `data.zip` when `main` is pushed. Pushing before releasing deploys the new code against stale data.

## Never

- Report `unreachable` venues as "nothing new" — that hides both outages and missing credentials.
- Write OpenReview `selections` from a pattern.
- Push before releasing data.
