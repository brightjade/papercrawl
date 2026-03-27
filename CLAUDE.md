# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                        # Install dependencies
uv run orc crawl iclr_2025                     # Crawl one conference
uv run orc crawl iclr_2025 neurips_2025        # Crawl multiple (one OpenReview login)
uv run orc citations iclr_2025                 # Fetch citation counts
uv run orc discover "ICLR.cc/2025/Conference"  # Find venue IDs
./run.sh iclr_2025 neurips_2025 --citations    # Pipeline script
uv run pytest tests/                           # Run all tests
uv run pytest tests/test_models.py::TestPaper::test_to_dict_full  # Single test
```

## Convention

Conference ID = config filename without `.yaml` (for OpenReview) or key in `SCRAPERS` dict (for ACL-family). Everything derives from it:

- Config: `configs/<id>.yaml` (OpenReview only)
- Scraper: `acl_scraper.SCRAPERS[<id>]` (ACL-family only)
- Output: `outputs/<id>/papers.jsonl`
- Citations: `outputs/<id>/papers_with_citations.jsonl` (sorted by citation count)

## Architecture

Two data sources, one output format:

- **OpenReview conferences** (ICLR, NeurIPS, ICML, COLM): conference ID -> YAML config -> `OpenReviewAPIClient` -> API (`get_all_notes` with invitation + venueid) -> filter by `venue` field -> `Paper` with `selection` tag
- **ACL-family conferences** (EMNLP, ACL, NAACL): conference ID -> `acl_scraper.SCRAPERS` -> scrape `<li><strong>Title</strong><em>Authors</em></li>` from conference website -> `Paper` with `selection` tag

Both produce JSONL. Citations work the same for both.

### Key modules

- `cli.py` -- Entry point (`orc`) with subcommands: `crawl`, `citations`, `discover`. `crawl` accepts multiple conference IDs, logs into OpenReview once, scrapes ACL-family conferences without auth.
- `api_client.py` -- `create_openreview_client()` logs in once, `OpenReviewAPIClient` takes the client + config. Fetches all accepted papers in one API call, filters by `venue` string client-side.
- `acl_scraper.py` -- Web scraper for conferences not on OpenReview. `SCRAPERS` dict maps conference IDs to scraper functions. Handles both separate-page (EMNLP, ACL) and single-page (NAACL) layouts. Skips entries without authors (filters footer noise).
- `citations.py` -- Async citation fetching with `httpx` + `asyncio.Semaphore`. Streams results to a temp file with tqdm progress bar, then writes sorted final file.
- `models.py` -- `Paper` dataclass with `selection` field. `to_dict()` excludes `None` and empty-string fields.
- `config.py` -- `CrawlConfig` from YAML. `conference_id` derived from filename, output path derived from that.
- `run.sh` -- Shell script: passes all conferences to one `orc crawl`, then runs `orc citations` per conference if `--citations` is set.

### OpenReview API notes

- All accepted papers share one `venueid` (e.g., `ICLR.cc/2025/Conference`), not per-track IDs
- Track type is in `venue` content field (e.g., `"ICLR 2025 Oral"`)
- Casing varies: ICLR 2025 title case, NeurIPS 2025 lowercase, ICML 2025 uses `spotlightposter`
- Auth mandatory (free account). Login rate-limited to 3/min -- `crawl` reuses one login for all OpenReview conferences.
