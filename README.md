# ORC - Conference Paper Crawler

Retrieve accepted paper metadata from ML/DL/NLP conferences. Uses the OpenReview API for ML conferences and web scraping for ACL-family conferences.

## Install

```bash
uv sync
```

## Authentication

OpenReview conferences require a free account. Sign up at https://openreview.net/signup, then:

```bash
cp .env.example .env
```

Fill in your credentials in `.env`. Not needed for ACL-family conferences (scraped from public websites).

## Usage

```bash
# Crawl one or more conferences
uv run orc crawl iclr_2025
uv run orc crawl iclr_2025 neurips_2025 emnlp_2025

# Fetch citation counts (with progress bar)
uv run orc citations iclr_2025

# Pipeline: crawl + citations for multiple conferences
./run.sh iclr_2025 neurips_2025 emnlp_2025 --citations

# Discover OpenReview venue IDs for a new conference
uv run orc discover "ICLR.cc/2025/Conference"
```

## Available conferences

| ID | Source | Selections |
|---|---|---|
| `iclr_2025` | OpenReview | oral, spotlight, poster |
| `iclr_2026` | OpenReview | oral, poster |
| `neurips_2025` | OpenReview | oral, spotlight, poster |
| `icml_2025` | OpenReview | oral, spotlight, poster |
| `colm_2025` | OpenReview | all |
| `emnlp_2025` | Web scrape | main, findings, industry |
| `acl_2025` | Web scrape | main, findings, industry |
| `naacl_2025` | Web scrape | main, findings, industry |

## Output

All output goes to `outputs/<conference_id>/`:

```
outputs/iclr_2025/
  papers.jsonl                    # all accepted papers
  papers_with_citations.jsonl     # sorted by citation count (after running citations)
```

OpenReview papers include title, authors, selection, keywords, abstract, PDF link, and forum ID. Web-scraped papers include title, authors, and selection.

## Testing

```bash
uv run pytest tests/
```
