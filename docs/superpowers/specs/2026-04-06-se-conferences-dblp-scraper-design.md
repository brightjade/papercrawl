# Design: DBLP Scraper for SE Conferences

## Overview

Add support for the four top-tier software engineering conferences (ICSE, FSE, ASE, ISSTA) for years 2023–2025 using the DBLP JSON search API as a unified data source.

## Conferences & Scope

| Conference | Years | Notes |
|---|---|---|
| ICSE | 2023, 2024, 2025 | Traditional IEEE/ACM proceedings |
| FSE | 2023, 2024, 2025 | Traditional in 2023; PACMSE journal in 2024+ |
| ASE | 2023, 2024, 2025 | Traditional IEEE/ACM proceedings (DBLP key prefix: `kbse`) |
| ISSTA | 2023, 2024, 2025 | Traditional in 2023–2024; PACMSE journal in 2025+ |

2026 editions are not yet indexed on DBLP. They can be added later as one-line config entries.

All papers from the main proceedings page are included (research + SEIP + NIER + tools). Workshops are excluded (separate DBLP keys).

## Data Source: DBLP JSON Search API

**Endpoint**: `https://dblp.org/search/publ/api?q=toc:<bht-key>&h=1000&format=json&f=0`

- No authentication required. CC0 licensed metadata.
- `h=1000` max hits per page; `f` for offset-based pagination.
- Rate limit: 1 second between requests.

### Response structure

```
result.hits.@total          → total paper count
result.hits.hit[].info      → paper record
  .title                    → paper title (has trailing ".")
  .authors.author[].text    → author name (may have disambiguation suffix)
  .ee                       → electronic edition URL (DOI link to publisher)
  .doi                      → DOI string
  .number                   → issue label for PACMSE entries ("FSE" or "ISSTA")
```

### Field mapping

| DBLP field | `Paper` field | Transform |
|---|---|---|
| `info.title` | `title` | Strip trailing `.` |
| `info.authors.author[].text` | `authors` | Strip disambiguation suffix (regex `\s+\d{4}$`) |
| `info.ee` | `link` | Use as-is (DOI URL to publisher page) |
| — | `selection` | Always `"main"` |

### PACMSE handling

FSE and ISSTA transitioned from traditional conference proceedings to the PACMSE journal model:

- **FSE 2024**: PACMSE vol 1 — all 121 papers are FSE, no filtering needed.
- **FSE 2025 + ISSTA 2025**: PACMSE vol 2 — shared volume. Filter by `info.number` field (`"FSE"` or `"ISSTA"`).

## Conference Registry

```python
DBLP_CONFERENCES = {
    "icse_2023":  {"key": "db/conf/icse/icse2023.bht"},
    "icse_2024":  {"key": "db/conf/icse/icse2024.bht"},
    "icse_2025":  {"key": "db/conf/icse/icse2025.bht"},

    "fse_2023":   {"key": "db/conf/sigsoft/fse2023.bht"},
    "fse_2024":   {"key": "db/journals/pacmse/pacmse1.bht"},
    "fse_2025":   {"key": "db/journals/pacmse/pacmse2.bht", "number": "FSE"},

    "ase_2023":   {"key": "db/conf/kbse/ase2023.bht"},
    "ase_2024":   {"key": "db/conf/kbse/ase2024.bht"},
    "ase_2025":   {"key": "db/conf/kbse/ase2025.bht"},

    "issta_2023":  {"key": "db/conf/issta/issta2023.bht"},
    "issta_2024":  {"key": "db/conf/issta/issta2024.bht"},
    "issta_2025":  {"key": "db/journals/pacmse/pacmse2.bht", "number": "ISSTA"},
}
```

Adding a new conference or year = one line in this dict.

## Module Structure

### New file: `ppr/scrapers/dblp.py`

```
_clean_author(name: str) -> str
    Strip DBLP disambiguation suffix (e.g., "Hao Zhong 0001" → "Hao Zhong").
    Regex: re.sub(r"\s+\d{4}$", "", name)

_fetch_dblp(key: str, number: str | None) -> list[dict]
    Call DBLP search API with toc: query.
    Paginate with h=1000 and f offset until all results fetched.
    If number is set, filter results where info.number == number.
    Rate limit: 1 sec sleep between paginated requests.
    Returns list of raw info dicts.

_scrape_dblp(conf_id: str) -> list[Paper]
    Look up conf_id in DBLP_CONFERENCES.
    Call _fetch_dblp with key and optional number.
    Map each result to Paper(title, link, authors, selection="main").
    Return list[Paper].

SCRAPERS = {conf_id: partial(_scrape_dblp, conf_id) for conf_id in DBLP_CONFERENCES}
```

### Modified: `ppr/scrapers/__init__.py`

```python
from ppr.scrapers.dblp import SCRAPERS as DBLP_SCRAPERS
SCRAPERS = {**ACL_SCRAPERS, **AAAI_SCRAPERS, **USENIX_SCRAPERS, **DBLP_SCRAPERS}
```

### Modified: `scripts/build_data.py`

Add venue name mappings:

```python
"icse": "ICSE",
"fse": "FSE",
"ase": "ASE",
"issta": "ISSTA",
```

## No Other Changes Required

- **CLI** (`ppr/cli.py`): Already dispatches scraper-based conferences via the `SCRAPERS` dict. No changes.
- **Enrichment** (`ppr/citations.py`): Works on any `papers.jsonl`. No changes.
- **Models** (`ppr/models.py`): Paper dataclass already has all needed fields. No changes.
- **Config** (`ppr/config.py`): Only used for OpenReview. No changes.

## Usage

```bash
uv run ppr crawl icse_2024 fse_2024 ase_2024 issta_2024
uv run ppr enrich icse_2024 fse_2024 ase_2024 issta_2024
./run.sh icse_2024 fse_2024 ase_2024 issta_2024 --enrich
```
