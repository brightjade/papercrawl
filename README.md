# paper-explorer

Retrieve accepted paper metadata from ML/DL/NLP/Security/SE conferences. Uses the OpenReview API for ML conferences, web scraping for ACL-family/AAAI/USENIX conferences, and the DBLP API for software engineering conferences.

## Install

```bash
uv sync
```

## Authentication

OpenReview conferences require a free account. Sign up at https://openreview.net/signup, then:

```bash
cp .env.example .env
```

Fill in your credentials in `.env`. Not needed for non-OpenReview conferences (scraped from public websites).

## Usage

```bash
# Crawl one or more conferences
uv run ppr crawl iclr_2025
uv run ppr crawl iclr_2025 neurips_2025 emnlp_2025

# Enrich with citation counts and abstracts (with progress bar)
uv run ppr enrich iclr_2025

# Pipeline: crawl + enrich for multiple conferences
./run.sh iclr_2025 neurips_2025 emnlp_2025 --enrich

# Build static JSON for web app
./build.sh
```

## Available conferences

| ID | Source | Selections |
|---|---|---|
| `iclr_2023` | OpenReview | oral, spotlight, poster |
| `iclr_2024` | OpenReview | oral, spotlight, poster |
| `iclr_2025` | OpenReview | oral, spotlight, poster |
| `iclr_2026` | OpenReview | oral, poster |
| `neurips_2023` | OpenReview | oral, spotlight, poster |
| `neurips_2024` | OpenReview | oral, spotlight, poster |
| `neurips_2025` | OpenReview | oral, spotlight, poster |
| `icml_2023` | OpenReview | oral, poster |
| `icml_2024` | OpenReview | oral, spotlight, poster |
| `icml_2025` | OpenReview | oral, spotlight, poster |
| `colm_2024` | OpenReview | main |
| `colm_2025` | OpenReview | main |
| `aaai_2023` | Web scrape | main |
| `aaai_2024` | Web scrape | main |
| `aaai_2025` | Web scrape | main |
| `emnlp_2023` | Web scrape | main, findings, industry |
| `emnlp_2024` | Web scrape | main, findings, industry |
| `emnlp_2025` | Web scrape | main, findings, industry |
| `acl_2023` | Web scrape | main, findings, industry |
| `acl_2024` | Web scrape | main, findings |
| `acl_2025` | Web scrape | main, findings, industry |
| `naacl_2024` | Web scrape | main, findings, industry |
| `naacl_2025` | Web scrape | main, findings, industry |
| `usenix_security_2023` | Web scrape | main |
| `usenix_security_2024` | Web scrape | main |
| `usenix_security_2025` | Web scrape | main |
| `icse_2023` | DBLP API | main |
| `icse_2024` | DBLP API | main |
| `icse_2025` | DBLP API | main |
| `fse_2023` | DBLP API | main |
| `fse_2024` | DBLP API | main |
| `fse_2025` | DBLP API | main |
| `ase_2023` | DBLP API | main |
| `ase_2024` | DBLP API | main |
| `ase_2025` | DBLP API | main |
| `issta_2023` | DBLP API | main |
| `issta_2024` | DBLP API | main |
| `issta_2025` | DBLP API | main |

## Output

All output goes to `data/<conference_id>/`:

```
data/iclr_2025/
  papers.jsonl                    # all accepted papers
  papers_enriched.jsonl            # enriched with Semantic Scholar metadata (after running enrich)
```

OpenReview papers include title, authors, selection, keywords, abstract, PDF link, and forum ID. Web-scraped papers include title, authors, and selection. DBLP papers include title, authors, and DOI link. The `enrich` command adds citation counts and abstracts (from Semantic Scholar) to all papers. Existing abstracts (e.g., from OpenReview) are preserved. Enrichment is resumable — if interrupted, re-running `ppr enrich` picks up where it left off.

## Testing

```bash
uv run pytest tests/
```
