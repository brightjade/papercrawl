# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                        # Install dependencies
uv run ppr crawl iclr_2025                     # Crawl one conference
uv run ppr crawl iclr_2025 neurips_2025        # Crawl multiple (one OpenReview login)
uv run ppr enrich iclr_2025 neurips_2025        # Enrich with Semantic Scholar metadata
uv run ppr validate iclr_2025                  # Validate paper count against DBLP
./build.sh                                     # Build static JSON for web app
uv run pytest tests/                           # Run all tests
uv run pytest tests/test_models.py::TestPaper::test_to_dict_full  # Single test
```

## Convention

Conference ID = config filename without `.yaml` (for OpenReview) or key in `SCRAPERS` dict (for ACL-family / AAAI / USENIX / DBLP). Everything derives from it:

- Config: `configs/<id>.yaml` (OpenReview only)
- Scraper: `ppr.scrapers.SCRAPERS[<id>]` (ACL-family / AAAI / USENIX / DBLP)
- Output: `data/<id>/papers.jsonl`
- Enriched: `data/<id>/papers_enriched.jsonl` (sorted by citation count, with abstracts)

## Architecture

Multiple data sources, one output format:

- **OpenReview conferences** (ICLR, NeurIPS, ICML, COLM, CoRL): conference ID -> YAML config -> `OpenReviewAPIClient` -> API (`get_all_notes` with invitation + venueid) -> filter by `venue` field -> `Paper` with `selection` tag
- **ACL-family conferences** (EMNLP, ACL, NAACL, EACL, COLING): conference ID -> `ppr.scrapers.acl.SCRAPERS` -> scrape `<li><strong>Title</strong><em>Authors</em></li>` from conference website -> `Paper` with `selection` tag
- **AAAI**: conference ID -> `ppr.scrapers.aaai.SCRAPERS` -> scrape OJS issue pages from `ojs.aaai.org` -> `Paper` with `selection` tag
- **USENIX Security**: conference ID -> `ppr.scrapers.usenix.SCRAPERS` -> scrape `article.node-paper` from `technical-sessions` page -> `Paper` with `selection` tag. Requires browser User-Agent header.
- **CV conferences** (CVPR, ICCV, ECCV, WACV): conference ID -> `ppr.scrapers.cvf.SCRAPERS` -> CVF Open Access / ECVA for ECCV -> `Paper` with `selection` tag
- **Robotics conferences** (ICRA, IROS): conference ID -> `ppr.scrapers.dblp.SCRAPERS` -> DBLP JSON API. RSS 2025 uses dedicated `ppr.scrapers.rss` scraper; RSS 2023-2024 use DBLP.
- **SE conferences** (ICSE, FSE, ASE, ISSTA): conference ID -> `ppr.scrapers.dblp.SCRAPERS` -> DBLP JSON search API (`toc:` query) -> `Paper` with `selection` tag. No auth needed. FSE 2024+ and ISSTA 2025+ use PACMSE journal keys with `number` field filtering.
- **IJCAI**: conference ID -> `ppr.scrapers.dblp.SCRAPERS` -> DBLP JSON API.

All produce JSONL. Enrichment (citations + abstracts via Semantic Scholar) works the same for all sources. OpenReview abstracts are preserved; Semantic Scholar abstracts fill in papers that lack them.

### Key modules

All source code lives in the `ppr/` package:

- `ppr/cli.py` -- Entry point (`ppr`) with subcommands: `crawl`, `enrich`, `validate`. `crawl` accepts multiple conference IDs, logs into OpenReview once, scrapes ACL-family conferences without auth.
- `ppr/api_client.py` -- `create_openreview_client()` logs in once, `OpenReviewAPIClient` takes the client + config. Fetches all accepted papers in one API call, filters by `venue` string client-side.
- `ppr/scrapers/` -- Web scrapers for conferences not on OpenReview. Each module exports a `SCRAPERS` dict mapping conference IDs to scraper functions. `ppr/scrapers/__init__.py` aggregates all scrapers.
  - `acl.py` -- ACL-family (EMNLP, ACL, NAACL). Handles both separate-page and single-page layouts. Skips entries without authors (filters footer noise).
  - `aaai.py` -- AAAI proceedings from `ojs.aaai.org`. Scrapes multiple OJS issue pages per year (technical tracks + special tracks).
  - `usenix.py` -- USENIX Security. Scrapes `technical-sessions` page. Parses `Name1 and Name2,Affiliation;Name3,Affiliation` author format. Needs browser UA to avoid 403.
  - `dblp.py` -- SE conferences (ICSE, FSE, ASE, ISSTA), robotics (ICRA, IROS, RSS 2023-2024), and IJCAI via DBLP JSON API. Config dict maps conference IDs to `toc:` keys. Handles PACMSE journal volumes (shared by FSE/ISSTA) via `number` field filtering. Strips DBLP author disambiguation suffixes and HTML entities.
  - `cvf.py` -- CV conferences (CVPR, ICCV, WACV) from CVF Open Access, ECCV from ECVA. Parses paper lists with author metadata.
  - `rss.py` -- RSS 2025 from the RSS website (earlier years use DBLP).
- `ppr/citations.py` -- Async enrichment (citations + abstracts) via Semantic Scholar with `httpx` + `asyncio.Semaphore`. Rate-limited to 1 req/sec. Streams results to a temp file with tqdm progress bar, then writes sorted final file. Preserves existing abstracts (e.g., from OpenReview). Supports resume: if tmp file exists, skips already-enriched papers.
- `ppr/validate.py` -- Cross-references scraped paper counts against DBLP proceedings data. Maps conference IDs to DBLP toc keys, fetches counts via paginated API, compares with configurable tolerance (default 10%). Skips DBLP-sourced conferences (circular validation).
- `ppr/models.py` -- `Paper` dataclass with `selection` field. `to_dict()` excludes `None` and empty-string fields.
- `ppr/config.py` -- `CrawlConfig` from YAML. `conference_id` derived from filename, output path derived from that.

### OpenReview API notes

- All accepted papers share one `venueid` (e.g., `ICLR.cc/2025/Conference`), not per-track IDs
- Track type is in `venue` content field (e.g., `"ICLR 2025 Oral"`)
- Casing varies: ICLR 2025 title case, NeurIPS 2025 lowercase, ICML 2025 uses `spotlightposter`
- Auth mandatory (free account). Login rate-limited to 3/min -- `crawl` reuses one login for all OpenReview conferences.
