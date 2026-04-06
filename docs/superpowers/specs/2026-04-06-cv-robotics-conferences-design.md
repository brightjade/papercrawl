# Add CV, Robotics, and Additional Conferences

## Overview

Add 11 new conference venues (CVPR, ICCV, ECCV, WACV, ICRA, IROS, RSS, IJCAI, CoRL, EACL, COLING) spanning computer vision, robotics, and NLP. Uses a mix of new scrapers and extensions to existing modules.

## Conference-to-Source Mapping

| Source | Conferences |
|---|---|
| OpenReview (new YAML configs) | CoRL 2023, 2024 |
| New CVF scraper (`cvf.py`) | CVPR 2023-2025, ICCV 2023+2025, WACV 2023-2026, ECCV 2024 |
| New RSS scraper (`rss.py`) | RSS 2025 |
| DBLP (expand `dblp.py`) | ICRA 2023-2025, IROS 2023-2025, RSS 2023-2024, IJCAI 2023-2025 |
| ACL scraper (extend `acl.py`) | COLING 2024-2025, EACL 2023-2024 |
| Unchanged | ICLR, NeurIPS, ICML, COLM, ACL, EMNLP, NAACL, AAAI, USENIX Security, SE conferences |

## New Module: `ppr/scrapers/cvf.py`

Three sub-scrapers under one module, all producing `Paper` objects with `selection="main"`.

### 1. CVF Open Access Parser

- Source: `openaccess.thecvf.com`
- Conferences: CVPR 2023-2025, ICCV 2023, WACV 2023-2025
- URL patterns:
  - CVPR/ICCV: `https://openaccess.thecvf.com/{CONF}{YEAR}?day=all`
  - WACV: `https://openaccess.thecvf.com/WACV{YEAR}` (no day param needed)
- HTML structure: Each paper has a title link, comma-separated authors, and `[pdf]` link
- PDF URLs derivable from title link: replace `/html/` with `/papers/` and `.html` with `.pdf`
- Single page, no pagination, no JS rendering required

### 2. CVF Accepted Papers Parser

- Source: `{conf}.thecvf.com/Conferences/{year}/AcceptedPapers`
- Conferences: ICCV 2025, WACV 2026 (not yet on CVF Open Access)
- HTML structure: Repeating `<strong>Title</strong>` + `<em>Author1 · Author2</em>` blocks
- No PDF links available (pre-publication)
- Authors separated by `·` (middle dot, U+00B7)

### 3. ECVA Parser

- Source: `https://www.ecva.net/papers.php`
- Conferences: ECCV 2024
- HTML structure: Paper entries with title as `<a>` tag, authors as text, PDF link relative to `ecva.net`
- Single flat page, all papers listed
- ECCV is NOT on CVF Open Access (returns 404)

### SCRAPERS dict

```python
CVF_CONFERENCES = {
    # CVF Open Access
    "cvpr_2023": {"url": "https://openaccess.thecvf.com/CVPR2023?day=all", "parser": "openaccess"},
    "cvpr_2024": {"url": "https://openaccess.thecvf.com/CVPR2024?day=all", "parser": "openaccess"},
    "cvpr_2025": {"url": "https://openaccess.thecvf.com/CVPR2025?day=all", "parser": "openaccess"},
    "iccv_2023": {"url": "https://openaccess.thecvf.com/ICCV2023?day=all", "parser": "openaccess"},
    "wacv_2023": {"url": "https://openaccess.thecvf.com/WACV2023", "parser": "openaccess"},
    "wacv_2024": {"url": "https://openaccess.thecvf.com/WACV2024", "parser": "openaccess"},
    "wacv_2025": {"url": "https://openaccess.thecvf.com/WACV2025", "parser": "openaccess"},
    # CVF Accepted Papers (pre-publication)
    "iccv_2025": {"url": "https://iccv.thecvf.com/Conferences/2025/AcceptedPapers", "parser": "accepted"},
    "wacv_2026": {"url": "https://wacv.thecvf.com/Conferences/2026/AcceptedPapers", "parser": "accepted"},
    # ECVA
    "eccv_2024": {"url": "https://www.ecva.net/papers.php", "parser": "ecva"},
}
```

## New Module: `ppr/scrapers/rss.py`

- Source: `https://roboticsconference.org/program/papers/`
- Conference: RSS 2025
- HTML structure: `<table id="myTable">` with rows containing paper number, session, title (`<a>`), authors (comma-separated)
- Clean and simple to parse

```python
RSS_CONFERENCES = {
    "rss_2025": {"url": "https://roboticsconference.org/program/papers/"},
}
```

## Extend: `ppr/scrapers/dblp.py`

Add entries to `DBLP_CONFERENCES`:

```python
# Robotics
"icra_2023": {"key": "db/conf/icra/icra2023.bht"},
"icra_2024": {"key": "db/conf/icra/icra2024.bht"},
"icra_2025": {"key": "db/conf/icra/icra2025.bht"},
"iros_2023": {"key": "db/conf/iros/iros2023.bht"},
"iros_2024": {"key": "db/conf/iros/iros2024.bht"},
"iros_2025": {"key": "db/conf/iros/iros2025.bht"},
"rss_2023":  {"key": "db/conf/rss/rss2023.bht"},
"rss_2024":  {"key": "db/conf/rss/rss2024.bht"},
# AI
"ijcai_2023": {"key": "db/conf/ijcai/ijcai2023.bht"},
"ijcai_2024": {"key": "db/conf/ijcai/ijcai2024.bht"},
"ijcai_2025": {"key": "db/conf/ijcai/ijcai2025.bht"},
```

## Extend: `ppr/scrapers/acl.py`

### Fix: `" and "` author delimiter

The `_parse_paper_list` function (line ~38) splits authors on `","` only. COLING 2025 uses `" and "` between the last two authors. Fix: replace `" and "` with `", "` before splitting, or use regex to split on both.

### Add: COLING 2025

COLING 2025 conference website (`coling2025.org/program/main_conference_papers/`) uses the same `<li><strong>Title</strong><em>Authors</em></li>` pattern as existing ACL conferences.

### Add: ACL Anthology parser

EACL 2023-2024 and COLING 2024 (LREC-COLING) are only available on ACL Anthology, which uses a different Bootstrap HTML layout (`div.d-sm-flex > span.d-block > strong > a` for titles, `a[href="/people/..."]` for authors).

New function `_parse_anthology(url)` to handle this pattern.

Conference entries:
```python
"coling_2025": conference website (existing parser)
"coling_2024": ACL Anthology volume 2024.lrec-main (anthology parser)
"eacl_2024":   ACL Anthology volume 2024.eacl-long (anthology parser)
"eacl_2023":   ACL Anthology volume 2023.eacl-main (anthology parser)
```

## New OpenReview Configs

### `configs/corl_2024.yaml`

```yaml
conference:
  name: "CoRL"
  year: 2024
  venue_id: "<to be determined from OpenReview>"
  selections:
    main: "<venue string for accepted papers>"
```

### `configs/corl_2023.yaml`

Same structure. Venue IDs need to be looked up on OpenReview.

## Update: `scripts/build_data.py`

Add to `VENUE_NAMES`:
```python
"cvpr": "CVPR",
"iccv": "ICCV",
"eccv": "ECCV",
"wacv": "WACV",
"icra": "ICRA",
"iros": "IROS",
"rss": "RSS",
"ijcai": "IJCAI",
"corl": "CoRL",
"eacl": "EACL",
"coling": "COLING",
```

## Update: `ppr/scrapers/__init__.py`

Import and aggregate new scraper modules:
```python
from ppr.scrapers.cvf import SCRAPERS as CVF_SCRAPERS
from ppr.scrapers.rss import SCRAPERS as RSS_SCRAPERS

SCRAPERS = {**ACL_SCRAPERS, **AAAI_SCRAPERS, **USENIX_SCRAPERS, **DBLP_SCRAPERS, **CVF_SCRAPERS, **RSS_SCRAPERS}
```

## Files Summary

| Action | File |
|---|---|
| Create | `ppr/scrapers/cvf.py` |
| Create | `ppr/scrapers/rss.py` |
| Create | `configs/corl_2023.yaml` |
| Create | `configs/corl_2024.yaml` |
| Modify | `ppr/scrapers/dblp.py` |
| Modify | `ppr/scrapers/acl.py` |
| Modify | `ppr/scrapers/__init__.py` |
| Modify | `scripts/build_data.py` |

## Not in Scope

- CVPR 2026, RSS 2025 via DBLP (not yet indexed; CVPR 2026 not yet published anywhere)
- Abstracts from CVF (only on individual paper pages; Semantic Scholar enrichment handles this)
- Track-level info for CV conferences (CVF Open Access doesn't distinguish oral/poster)
