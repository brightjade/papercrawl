# paper-explorer

Retrieve accepted paper metadata from ML/DL/NLP/CV/Robotics/Security/SE conferences. Uses the OpenReview API, web scraping, CVF Open Access, and the DBLP API.

## Getting Started

### 1. Install uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager used to manage dependencies.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installing, restart your terminal so the `uv` command is available.

### 2. Clone and install dependencies

```bash
git clone https://github.com/brightjade/paper-explorer.git
cd paper-explorer
uv sync
```

This creates a virtual environment and installs all required packages automatically.

### 3. Set up OpenReview credentials (optional)

Only needed if you want to crawl OpenReview conferences (ICLR, NeurIPS, ICML, COLM, CoRL). Other conferences are scraped from public websites and don't require authentication.

1. Create a free account at https://openreview.net/signup
2. Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

3. Edit `.env` with your OpenReview username and password.

## Usage

```bash
# Crawl one or more conferences
uv run ppr crawl iclr_2025
uv run ppr crawl iclr_2025 neurips_2025 icml_2025

# Enrich with citation counts and abstracts
uv run ppr enrich iclr_2025
uv run ppr enrich iclr_2025 neurips_2025 icml_2025

# Validate paper counts against DBLP
uv run ppr validate iclr_2025
uv run ppr validate iclr_2025 neurips_2025 --tolerance 0.15

# Build static JSON for web app
./build.sh
```

## Available conferences

Conference ID format: `<venue>_<year>` (e.g., `iclr_2025`). Selections indicate available paper tracks.

### ML

| Conference | 2026 | 2025 | 2024 | 2023 |
|---|---|---|---|---|
| ICLR | oral, poster | oral, spotlight, poster | oral, spotlight, poster | oral, spotlight, poster |
| NeurIPS | | oral, spotlight, poster | oral, spotlight, poster | oral, spotlight, poster |
| ICML | | oral, spotlight, poster | oral, spotlight, poster | oral, poster |
| AAAI | | main | main | main |
| IJCAI | | main | main | main |

NeurIPS also includes `datasets_oral`, `datasets_spotlight`, `datasets_poster` tracks.

### NLP

| Conference | 2025 | 2024 | 2023 |
|---|---|---|---|
| ACL | main, findings, industry | main, findings | main, findings, industry |
| EMNLP | main, findings, industry | main, findings, industry | main, findings, industry |
| NAACL | main, findings, industry | main, findings, industry | |
| COLM | main | main | |
| EACL | | main, findings | main, findings |
| COLING | main | main | |

### CV (CVF / ECVA)

| Conference | 2026 | 2025 | 2024 | 2023 |
|---|---|---|---|---|
| CVPR | | main | main | main |
| ICCV | | main | | main |
| ECCV | | | main | |
| WACV | main | main | main | main |

### Robotics

| Conference | 2025 | 2024 | 2023 |
|---|---|---|---|
| CoRL | oral, poster | main | oral, poster |
| ICRA | main | main | main |
| IROS | main | main | main |
| RSS | main | main | main |

### Security

| Conference | 2025 | 2024 | 2023 |
|---|---|---|---|
| USENIX Security | main | main | main |

### Software Engineering (DBLP)

| Conference | 2025 | 2024 | 2023 |
|---|---|---|---|
| ICSE | main | main | main |
| FSE | main | main | main |
| ASE | main | main | main |
| ISSTA | main | main | main |

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
