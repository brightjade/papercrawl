# DBLP Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a DBLP-based scraper to fetch papers from ICSE, FSE, ASE, and ISSTA (2023–2025).

**Architecture:** Single `ppr/scrapers/dblp.py` module using the DBLP JSON search API. A config dict maps conference IDs to DBLP `toc:` keys. One generic scrape function handles all conferences, with optional PACMSE `number` filtering for FSE 2025 and ISSTA 2025.

**Tech Stack:** `requests` (HTTP), `re` (author name cleanup), existing `Paper` dataclass.

**Spec:** `docs/superpowers/specs/2026-04-06-se-conferences-dblp-scraper-design.md`

---

### Task 1: Test and implement `_clean_author`

**Files:**
- Create: `tests/test_dblp.py`
- Create: `ppr/scrapers/dblp.py`

- [ ] **Step 1: Write failing tests for `_clean_author`**

```python
# tests/test_dblp.py
from ppr.scrapers.dblp import _clean_author


class TestCleanAuthor:
    def test_strips_four_digit_suffix(self):
        assert _clean_author("Hao Zhong 0001") == "Hao Zhong"

    def test_strips_different_suffix(self):
        assert _clean_author("Wei Meng 0003") == "Wei Meng"

    def test_no_suffix_unchanged(self):
        assert _clean_author("John Smith") == "John Smith"

    def test_name_ending_in_digits_not_suffix(self):
        # Only strip if preceded by space and exactly 4 digits at end
        assert _clean_author("Agent 47") == "Agent 47"

    def test_empty_string(self):
        assert _clean_author("") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dblp.py::TestCleanAuthor -v`
Expected: FAIL with `ImportError` (module doesn't exist yet)

- [ ] **Step 3: Implement `_clean_author`**

Create `ppr/scrapers/dblp.py` with the initial content:

```python
"""Scraper for SE conferences (ICSE, FSE, ASE, ISSTA) via the DBLP API.

DBLP provides a free JSON search API with CC0-licensed metadata.
All four conferences are indexed, including PACMSE journal articles
for FSE 2024+ and ISSTA 2025+.
"""

import re


def _clean_author(name: str) -> str:
    """Strip DBLP disambiguation suffix from author name.

    DBLP appends ' 0001', ' 0002', etc. to disambiguate authors with
    identical names. E.g., 'Hao Zhong 0001' -> 'Hao Zhong'.
    """
    return re.sub(r"\s+\d{4}$", "", name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dblp.py::TestCleanAuthor -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_dblp.py ppr/scrapers/dblp.py
git commit -m "feat(dblp): add _clean_author with tests"
```

---

### Task 2: Test and implement `_fetch_dblp`

**Files:**
- Modify: `ppr/scrapers/dblp.py`
- Modify: `tests/test_dblp.py`

- [ ] **Step 1: Write failing tests for `_fetch_dblp`**

Append to `tests/test_dblp.py`:

```python
from unittest.mock import patch, MagicMock
from ppr.scrapers.dblp import _fetch_dblp


def _make_dblp_response(hits: list[dict], total: int) -> dict:
    """Build a minimal DBLP API response."""
    return {
        "result": {
            "hits": {
                "@total": str(total),
                "@sent": str(len(hits)),
                "@first": "0",
                "hit": [{"info": h} for h in hits],
            }
        }
    }


class TestFetchDblp:
    @patch("ppr.scrapers.dblp.requests.get")
    def test_returns_paper_info_dicts(self, mock_get):
        hits = [
            {
                "title": "Paper One.",
                "authors": {"author": [{"text": "Alice 0001"}]},
                "ee": "https://doi.org/10.1145/1",
                "venue": "ICSE",
                "year": "2024",
            },
            {
                "title": "Paper Two.",
                "authors": {"author": [{"text": "Bob"}]},
                "ee": "https://doi.org/10.1145/2",
                "venue": "ICSE",
                "year": "2024",
            },
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_dblp_response(hits, total=2)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_dblp("db/conf/icse/icse2024.bht")
        assert len(result) == 2
        assert result[0]["title"] == "Paper One."
        assert result[1]["authors"]["author"][0]["text"] == "Bob"

    @patch("ppr.scrapers.dblp.requests.get")
    def test_filters_by_number(self, mock_get):
        hits = [
            {
                "title": "FSE Paper.",
                "authors": {"author": [{"text": "Alice"}]},
                "ee": "https://doi.org/10.1145/1",
                "number": "FSE",
            },
            {
                "title": "ISSTA Paper.",
                "authors": {"author": [{"text": "Bob"}]},
                "ee": "https://doi.org/10.1145/2",
                "number": "ISSTA",
            },
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_dblp_response(hits, total=2)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_dblp("db/journals/pacmse/pacmse2.bht", number="FSE")
        assert len(result) == 1
        assert result[0]["title"] == "FSE Paper."

    @patch("ppr.scrapers.dblp.time.sleep")
    @patch("ppr.scrapers.dblp.requests.get")
    def test_paginates_when_more_than_1000(self, mock_get, mock_sleep):
        # First page: 1000 hits out of 1200 total
        page1_hits = [{"title": f"P{i}.", "authors": {"author": [{"text": "A"}]}, "ee": "https://x"} for i in range(1000)]
        resp1 = MagicMock()
        resp1.json.return_value = _make_dblp_response(page1_hits, total=1200)
        resp1.raise_for_status = MagicMock()

        # Second page: remaining 200
        page2_hits = [{"title": f"Q{i}.", "authors": {"author": [{"text": "B"}]}, "ee": "https://y"} for i in range(200)]
        resp2 = MagicMock()
        resp2.json.return_value = _make_dblp_response(page2_hits, total=1200)
        resp2.raise_for_status = MagicMock()

        mock_get.side_effect = [resp1, resp2]

        result = _fetch_dblp("db/conf/kbse/ase2025.bht")
        assert len(result) == 1200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("ppr.scrapers.dblp.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"hits": {"@total": "0", "@sent": "0", "@first": "0"}}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_dblp("db/conf/icse/icse2099.bht")
        assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dblp.py::TestFetchDblp -v`
Expected: FAIL with `ImportError` (`_fetch_dblp` not defined)

- [ ] **Step 3: Implement `_fetch_dblp`**

Add to `ppr/scrapers/dblp.py`:

```python
import logging
import time

import requests

logger = logging.getLogger(__name__)

DBLP_API_URL = "https://dblp.org/search/publ/api"
HITS_PER_PAGE = 1000


def _fetch_dblp(key: str, number: str | None = None) -> list[dict]:
    """Fetch all paper records from DBLP for a given toc key.

    Args:
        key: DBLP bibliography key (e.g., 'db/conf/icse/icse2024.bht').
        number: If set, filter results to entries whose 'number' field
                matches (used for PACMSE volumes shared by FSE/ISSTA).

    Returns:
        List of raw DBLP info dicts.
    """
    all_hits: list[dict] = []
    offset = 0

    while True:
        params = {
            "q": f"toc:{key}:",
            "h": HITS_PER_PAGE,
            "f": offset,
            "format": "json",
        }
        logger.info("DBLP API: key=%s offset=%d", key, offset)
        resp = requests.get(DBLP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        hits_data = data["result"]["hits"]
        total = int(hits_data["@total"])

        if total == 0:
            break

        for hit in hits_data.get("hit", []):
            all_hits.append(hit["info"])

        offset += HITS_PER_PAGE
        if offset >= total:
            break

        time.sleep(1)

    if number:
        all_hits = [h for h in all_hits if h.get("number") == number]

    logger.info("Fetched %d papers (total on DBLP: %s)", len(all_hits), total)
    return all_hits
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dblp.py::TestFetchDblp -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ppr/scrapers/dblp.py tests/test_dblp.py
git commit -m "feat(dblp): add _fetch_dblp with pagination and PACMSE filtering"
```

---

### Task 3: Test and implement `_scrape_dblp` and SCRAPERS dict

**Files:**
- Modify: `ppr/scrapers/dblp.py`
- Modify: `tests/test_dblp.py`

- [ ] **Step 1: Write failing tests for `_scrape_dblp`**

Append to `tests/test_dblp.py`:

```python
from ppr.scrapers.dblp import _scrape_dblp, SCRAPERS, DBLP_CONFERENCES


class TestScrapeDblp:
    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_maps_dblp_to_paper_objects(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "title": "Some Great Paper.",
                "authors": {"author": [
                    {"text": "Alice Smith 0001"},
                    {"text": "Bob Jones"},
                ]},
                "ee": "https://doi.org/10.1145/12345",
            },
        ]
        papers = _scrape_dblp("icse_2024")
        assert len(papers) == 1
        p = papers[0]
        assert p.title == "Some Great Paper"
        assert p.authors == ["Alice Smith", "Bob Jones"]
        assert p.link == "https://doi.org/10.1145/12345"
        assert p.selection == "main"

    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_strips_trailing_dot_from_title(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "title": "Title With Dot.",
                "authors": {"author": [{"text": "Alice"}]},
                "ee": "https://doi.org/10.1145/1",
            },
        ]
        papers = _scrape_dblp("icse_2024")
        assert papers[0].title == "Title With Dot"

    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_handles_single_author(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "title": "Solo Paper.",
                "authors": {"author": {"text": "Solo Author 0002"}},
                "ee": "https://doi.org/10.1145/1",
            },
        ]
        papers = _scrape_dblp("icse_2024")
        assert papers[0].authors == ["Solo Author"]

    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_skips_entries_without_ee(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "title": "No Link Paper.",
                "authors": {"author": [{"text": "Alice"}]},
            },
        ]
        papers = _scrape_dblp("icse_2024")
        assert len(papers) == 0

    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_handles_ee_as_list(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "title": "Multi Link.",
                "authors": {"author": [{"text": "Alice"}]},
                "ee": ["https://doi.org/10.1145/1", "https://doi.org/10.1145/2"],
            },
        ]
        papers = _scrape_dblp("icse_2024")
        assert len(papers) == 1
        assert papers[0].link == "https://doi.org/10.1145/1"

    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_passes_number_for_pacmse(self, mock_fetch):
        mock_fetch.return_value = []
        _scrape_dblp("fse_2025")
        mock_fetch.assert_called_once_with(
            "db/journals/pacmse/pacmse2.bht", number="FSE"
        )

    @patch("ppr.scrapers.dblp._fetch_dblp")
    def test_no_number_for_traditional(self, mock_fetch):
        mock_fetch.return_value = []
        _scrape_dblp("icse_2024")
        mock_fetch.assert_called_once_with(
            "db/conf/icse/icse2024.bht", number=None
        )


class TestScrapersDict:
    def test_all_conferences_registered(self):
        for conf_id in DBLP_CONFERENCES:
            assert conf_id in SCRAPERS, f"{conf_id} not in SCRAPERS"

    def test_expected_conference_ids(self):
        expected = {
            "icse_2023", "icse_2024", "icse_2025",
            "fse_2023", "fse_2024", "fse_2025",
            "ase_2023", "ase_2024", "ase_2025",
            "issta_2023", "issta_2024", "issta_2025",
        }
        assert expected == set(DBLP_CONFERENCES.keys())

    def test_scrapers_are_callable(self):
        for conf_id, scraper in SCRAPERS.items():
            assert callable(scraper), f"{conf_id} scraper is not callable"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_dblp.py::TestScrapeDblp tests/test_dblp.py::TestScrapersDict -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement `_scrape_dblp`, conference registry, and SCRAPERS dict**

Add to `ppr/scrapers/dblp.py`:

```python
from functools import partial

from ppr.models import Paper

DBLP_CONFERENCES = {
    # ICSE (traditional proceedings)
    "icse_2023": {"key": "db/conf/icse/icse2023.bht"},
    "icse_2024": {"key": "db/conf/icse/icse2024.bht"},
    "icse_2025": {"key": "db/conf/icse/icse2025.bht"},
    # FSE (traditional 2023, PACMSE 2024+)
    "fse_2023": {"key": "db/conf/sigsoft/fse2023.bht"},
    "fse_2024": {"key": "db/journals/pacmse/pacmse1.bht"},
    "fse_2025": {"key": "db/journals/pacmse/pacmse2.bht", "number": "FSE"},
    # ASE (traditional proceedings, DBLP key prefix is 'kbse')
    "ase_2023": {"key": "db/conf/kbse/ase2023.bht"},
    "ase_2024": {"key": "db/conf/kbse/ase2024.bht"},
    "ase_2025": {"key": "db/conf/kbse/ase2025.bht"},
    # ISSTA (traditional 2023-2024, PACMSE 2025+)
    "issta_2023": {"key": "db/conf/issta/issta2023.bht"},
    "issta_2024": {"key": "db/conf/issta/issta2024.bht"},
    "issta_2025": {"key": "db/journals/pacmse/pacmse2.bht", "number": "ISSTA"},
}


def _scrape_dblp(conf_id: str) -> list[Paper]:
    """Scrape all papers for a conference from DBLP."""
    conf = DBLP_CONFERENCES[conf_id]
    hits = _fetch_dblp(conf["key"], number=conf.get("number"))

    papers = []
    for hit in hits:
        ee = hit.get("ee")
        if not ee:
            continue

        # Handle ee being a string or a list (DBLP sometimes returns a list)
        if isinstance(ee, list):
            ee = ee[0]

        title = hit.get("title", "")
        if title.endswith("."):
            title = title[:-1]

        # Authors can be a single dict or a list of dicts
        authors_raw = hit.get("authors", {}).get("author", [])
        if isinstance(authors_raw, dict):
            authors_raw = [authors_raw]
        authors = [_clean_author(a["text"]) for a in authors_raw]

        papers.append(Paper(
            title=title,
            link=ee,
            authors=authors,
            selection="main",
        ))

    logger.info("Scraped %d papers for %s", len(papers), conf_id)
    return papers


SCRAPERS = {conf_id: partial(_scrape_dblp, conf_id) for conf_id in DBLP_CONFERENCES}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dblp.py -v`
Expected: All tests PASS (TestCleanAuthor + TestFetchDblp + TestScrapeDblp + TestScrapersDict)

- [ ] **Step 5: Commit**

```bash
git add ppr/scrapers/dblp.py tests/test_dblp.py
git commit -m "feat(dblp): add _scrape_dblp, conference registry, and SCRAPERS dict"
```

---

### Task 4: Register DBLP scraper in `__init__.py`

**Files:**
- Modify: `ppr/scrapers/__init__.py`

- [ ] **Step 1: Update `__init__.py`**

Replace the full content of `ppr/scrapers/__init__.py` with:

```python
from ppr.scrapers.acl import SCRAPERS as ACL_SCRAPERS
from ppr.scrapers.aaai import SCRAPERS as AAAI_SCRAPERS
from ppr.scrapers.usenix import SCRAPERS as USENIX_SCRAPERS
from ppr.scrapers.dblp import SCRAPERS as DBLP_SCRAPERS

SCRAPERS = {**ACL_SCRAPERS, **AAAI_SCRAPERS, **USENIX_SCRAPERS, **DBLP_SCRAPERS}
```

- [ ] **Step 2: Verify import works**

Run: `uv run python -c "from ppr.scrapers import SCRAPERS; print([k for k in SCRAPERS if k.startswith(('icse', 'fse', 'ase', 'issta'))])"`
Expected: Prints list of 12 conference IDs

- [ ] **Step 3: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add ppr/scrapers/__init__.py
git commit -m "feat(dblp): register DBLP scraper in scrapers __init__"
```

---

### Task 5: Add venue mappings to `build_data.py` and update tests

**Files:**
- Modify: `scripts/build_data.py:8-18`
- Modify: `tests/test_build_data.py`

- [ ] **Step 1: Write failing tests for new venue names**

Add to `tests/test_build_data.py` in the `TestParseConferenceId` class:

```python
    def test_icse(self):
        assert parse_conference_id("icse_2024") == ("ICSE", 2024)

    def test_fse(self):
        assert parse_conference_id("fse_2024") == ("FSE", 2024)

    def test_ase(self):
        assert parse_conference_id("ase_2024") == ("ASE", 2024)

    def test_issta(self):
        assert parse_conference_id("issta_2024") == ("ISSTA", 2024)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_data.py::TestParseConferenceId -v`
Expected: The new tests PASS even without changes because `parse_conference_id` falls back to `prefix.upper()`. But let's add the explicit mappings for consistency.

- [ ] **Step 3: Add venue mappings to `build_data.py`**

In `scripts/build_data.py`, add these entries to the `VENUE_NAMES` dict (after the `"usenix_security"` line):

```python
    "icse": "ICSE",
    "fse": "FSE",
    "ase": "ASE",
    "issta": "ISSTA",
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_data.py tests/test_build_data.py
git commit -m "feat(build): add ICSE/FSE/ASE/ISSTA venue name mappings"
```

---

### Task 6: Smoke test with real DBLP API

**Files:** None (manual verification)

- [ ] **Step 1: Test a single small conference**

Run: `uv run ppr crawl issta_2023`
Expected: Outputs `outputs/issta_2023/papers.jsonl` with papers. Check count is reasonable (expect ~50-170 papers). Verify a few entries have sensible titles, authors, and DOI links.

- [ ] **Step 2: Inspect output**

Run: `head -3 outputs/issta_2023/papers.jsonl | python -m json.tool`
Expected: Each line is valid JSON with `title`, `link` (DOI URL), `authors` (clean names, no disambiguation suffixes), and `selection: "main"`.

- [ ] **Step 3: Test a PACMSE conference (shared volume filtering)**

Run: `uv run ppr crawl fse_2025`
Expected: Only FSE papers, not ISSTA papers. Count should be ~100-140.

- [ ] **Step 4: Test crawling multiple conferences at once**

Run: `uv run ppr crawl icse_2024 ase_2024`
Expected: Both `outputs/icse_2024/papers.jsonl` and `outputs/ase_2024/papers.jsonl` created successfully.

- [ ] **Step 5: Commit smoke test outputs (optional)**

If outputs look correct:
```bash
git add outputs/
git commit -m "data: add initial SE conference paper data"
```
