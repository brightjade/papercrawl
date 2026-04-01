# papercrawl

Retrieve accepted paper metadata from ML/DL/NLP/Security conferences. Uses the OpenReview API for ML conferences and web scraping for ACL-family and USENIX conferences.

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

# Fetch citation counts (with progress bar)
uv run ppr citations iclr_2025

# Pipeline: crawl + citations for multiple conferences
./run.sh iclr_2025 neurips_2025 emnlp_2025 --citations
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
| `colm_2024` | OpenReview | all |
| `colm_2025` | OpenReview | all |
| `aaai_2023` | Web scrape | accepted |
| `aaai_2024` | Web scrape | accepted |
| `aaai_2025` | Web scrape | accepted |
| `emnlp_2023` | Web scrape | main, findings, industry |
| `emnlp_2024` | Web scrape | main, findings, industry |
| `emnlp_2025` | Web scrape | main, findings, industry |
| `acl_2023` | Web scrape | main, findings, industry |
| `acl_2024` | Web scrape | main, findings |
| `acl_2025` | Web scrape | main, findings, industry |
| `naacl_2024` | Web scrape | main, findings, industry |
| `naacl_2025` | Web scrape | main, findings, industry |
| `usenix_security_2023` | Web scrape | accepted |
| `usenix_security_2024` | Web scrape | accepted |
| `usenix_security_2025` | Web scrape | accepted |

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
