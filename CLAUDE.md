# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                        # Install dependencies
uv run ppr crawl iclr_2025                     # Crawl one conference
uv run ppr crawl iclr_2025 neurips_2025        # Crawl multiple (one OpenReview login)
uv run ppr enrich iclr_2025                    # Fetch citations & abstracts
./run.sh iclr_2025 neurips_2025 --enrich       # Pipeline script
uv run pytest tests/                           # Run all tests
uv run pytest tests/test_models.py::TestPaper::test_to_dict_full  # Single test
```

## Convention

Conference ID = config filename without `.yaml` (for OpenReview) or key in `SCRAPERS` dict (for ACL-family / AAAI / USENIX). Everything derives from it:

- Config: `configs/<id>.yaml` (OpenReview only)
- Scraper: `acl_scraper.SCRAPERS[<id>]` (ACL-family only)
- Output: `outputs/<id>/papers.jsonl`
- Enriched: `outputs/<id>/papers_with_citations.jsonl` (sorted by citation count, with abstracts)

## Architecture

Multiple data sources, one output format:

- **OpenReview conferences** (ICLR, NeurIPS, ICML, COLM): conference ID -> YAML config -> `OpenReviewAPIClient` -> API (`get_all_notes` with invitation + venueid) -> filter by `venue` field -> `Paper` with `selection` tag
- **ACL-family conferences** (EMNLP, ACL, NAACL): conference ID -> `acl_scraper.SCRAPERS` -> scrape `<li><strong>Title</strong><em>Authors</em></li>` from conference website -> `Paper` with `selection` tag
- **AAAI**: conference ID -> `aaai_scraper.SCRAPERS` -> scrape OJS issue pages from `ojs.aaai.org` -> `Paper` with `selection` tag
- **USENIX Security**: conference ID -> `usenix_scraper.SCRAPERS` -> scrape `article.node-paper` from `technical-sessions` page -> `Paper` with `selection` tag. Requires browser User-Agent header.

All produce JSONL. Enrichment (citations + abstracts via Semantic Scholar) works the same for all sources. OpenReview abstracts are preserved; Semantic Scholar abstracts fill in papers that lack them.

### Key modules

- `cli.py` -- Entry point (`ppr`) with subcommands: `crawl`, `enrich`. `crawl` accepts multiple conference IDs, logs into OpenReview once, scrapes ACL-family conferences without auth.
- `api_client.py` -- `create_openreview_client()` logs in once, `OpenReviewAPIClient` takes the client + config. Fetches all accepted papers in one API call, filters by `venue` string client-side.
- `acl_scraper.py` -- Web scraper for ACL-family conferences not on OpenReview. `SCRAPERS` dict maps conference IDs to scraper functions. Handles both separate-page (EMNLP, ACL) and single-page (NAACL) layouts. Skips entries without authors (filters footer noise).
- `aaai_scraper.py` -- Web scraper for AAAI proceedings from `ojs.aaai.org`. Scrapes multiple OJS issue pages per year (technical tracks + special tracks).
- `usenix_scraper.py` -- Web scraper for USENIX Security. Scrapes `technical-sessions` page (all papers on one page per year). Parses `Name1 and Name2,Affiliation;Name3,Affiliation` author format. Needs browser UA to avoid 403.
- `citations.py` -- Async enrichment (citations + abstracts) via Semantic Scholar with `httpx` + `asyncio.Semaphore`. Rate-limited to 1 req/sec. Streams results to a temp file with tqdm progress bar, then writes sorted final file. Preserves existing abstracts (e.g., from OpenReview). Supports resume: if tmp file exists, skips already-enriched papers.
- `models.py` -- `Paper` dataclass with `selection` field. `to_dict()` excludes `None` and empty-string fields.
- `config.py` -- `CrawlConfig` from YAML. `conference_id` derived from filename, output path derived from that.
- `run.sh` -- Shell script: passes all conferences to one `ppr crawl`, then runs `ppr enrich` per conference if `--enrich` is set.

### OpenReview API notes

- All accepted papers share one `venueid` (e.g., `ICLR.cc/2025/Conference`), not per-track IDs
- Track type is in `venue` content field (e.g., `"ICLR 2025 Oral"`)
- Casing varies: ICLR 2025 title case, NeurIPS 2025 lowercase, ICML 2025 uses `spotlightposter`
- Auth mandatory (free account). Login rate-limited to 3/min -- `crawl` reuses one login for all OpenReview conferences.
