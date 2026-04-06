# CV, Robotics & Additional Conferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 11 new conference venues (CVPR, ICCV, ECCV, WACV, ICRA, IROS, RSS, IJCAI, CoRL, EACL, COLING) to the paper-explorer pipeline.

**Architecture:** New scrapers for CVF/ECVA/RSS, extend existing DBLP + ACL scrapers, add OpenReview configs for CoRL. All scrapers produce `list[Paper]` and register in a `SCRAPERS` dict. The CLI dispatches to scrapers by checking `conf_id in SCRAPERS` first, then falling back to OpenReview YAML configs.

**Tech Stack:** Python 3, requests, BeautifulSoup4, pytest, OpenReview API (v1 for CoRL)

---

## Task 1: Add DBLP Entries for Robotics + IJCAI

**Files:**
- Modify: `ppr/scrapers/dblp.py:83-100` (DBLP_CONFERENCES dict)
- Modify: `tests/test_dblp.py:234-241` (TestScrapersDict.test_expected_conference_ids)

- [ ] **Step 1: Update the expected conference IDs test**

In `tests/test_dblp.py`, update `TestScrapersDict.test_expected_conference_ids` to include new IDs:

```python
def test_expected_conference_ids(self):
    expected = {
        "icse_2023", "icse_2024", "icse_2025",
        "fse_2023", "fse_2024", "fse_2025",
        "ase_2023", "ase_2024", "ase_2025",
        "issta_2023", "issta_2024", "issta_2025",
        # Robotics
        "icra_2023", "icra_2024", "icra_2025",
        "iros_2023", "iros_2024", "iros_2025",
        "rss_2023", "rss_2024",
        # AI
        "ijcai_2023", "ijcai_2024", "ijcai_2025",
    }
    assert expected == set(DBLP_CONFERENCES.keys())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dblp.py::TestScrapersDict::test_expected_conference_ids -v`
Expected: FAIL — the new IDs aren't in DBLP_CONFERENCES yet.

- [ ] **Step 3: Add entries to DBLP_CONFERENCES**

In `ppr/scrapers/dblp.py`, add after the ISSTA entries (line ~99):

```python
    # Robotics
    "icra_2023": {"key": "db/conf/icra/icra2023.bht"},
    "icra_2024": {"key": "db/conf/icra/icra2024.bht"},
    "icra_2025": {"key": "db/conf/icra/icra2025.bht"},
    "iros_2023": {"key": "db/conf/iros/iros2023.bht"},
    "iros_2024": {"key": "db/conf/iros/iros2024.bht"},
    "iros_2025": {"key": "db/conf/iros/iros2025.bht"},
    "rss_2023": {"key": "db/conf/rss/rss2023.bht"},
    "rss_2024": {"key": "db/conf/rss/rss2024.bht"},
    # AI
    "ijcai_2023": {"key": "db/conf/ijcai/ijcai2023.bht"},
    "ijcai_2024": {"key": "db/conf/ijcai/ijcai2024.bht"},
    "ijcai_2025": {"key": "db/conf/ijcai/ijcai2025.bht"},
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dblp.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ppr/scrapers/dblp.py tests/test_dblp.py
git commit -m "feat(dblp): add ICRA, IROS, RSS, IJCAI conferences"
```

---

## Task 2: Create CoRL OpenReview Configs

CoRL uses OpenReview API **v1** (Blind_Submission invitation). The existing codebase supports v1 via `api_version: 1` in the YAML config.

**Files:**
- Create: `configs/corl_2023.yaml`
- Create: `configs/corl_2024.yaml`

- [ ] **Step 1: Create `configs/corl_2023.yaml`**

```yaml
conference:
  name: "CoRL"
  year: 2023
  venue_id: "robot-learning.org/CoRL/2023/Conference"
  api_version: 1
  selections:
    oral: "CoRL 2023 Oral"
    poster: "CoRL 2023 Poster"
```

- [ ] **Step 2: Create `configs/corl_2024.yaml`**

```yaml
conference:
  name: "CoRL"
  year: 2024
  venue_id: "robot-learning.org/CoRL/2024/Conference"
  api_version: 1
  selections:
    oral: "CoRL 2024 Oral"
    spotlight: "CoRL 2024 Spotlight"
    poster: "CoRL 2024 Poster"
```

- [ ] **Step 3: Verify configs load**

Run: `uv run python -c "from ppr.config import CrawlConfig; c = CrawlConfig.from_yaml('configs/corl_2024.yaml'); print(c)"`
Expected: Prints CrawlConfig with venue_id `robot-learning.org/CoRL/2024/Conference`, api_version=1.

- [ ] **Step 4: Commit**

```bash
git add configs/corl_2023.yaml configs/corl_2024.yaml
git commit -m "feat(openreview): add CoRL 2023-2024 configs"
```

---

## Task 3: Create CVF Scraper — Open Access Parser

The CVF Open Access site (`openaccess.thecvf.com`) lists papers with title, authors, and PDF links on a single HTML page. CVPR/ICCV use `?day=all`, WACV uses the root page.

**Files:**
- Create: `ppr/scrapers/cvf.py`
- Create: `tests/test_cvf.py`

- [ ] **Step 1: Write test for CVF Open Access HTML parsing**

Create `tests/test_cvf.py`:

```python
from ppr.scrapers.cvf import _parse_openaccess


# Minimal HTML fixture matching CVF Open Access structure.
# Each paper is a <dt> with title link + <dd> with authors and PDF link.
OPENACCESS_HTML = """
<html><body>
<dl>
<dt class="ptitle"><br>
<a href="content/CVPR2025/html/Smith_Great_Paper_CVPR_2025_paper.html">A Great Paper About Vision</a></dt>
<dd>
<div class="bibref">Smith, Alice; Jones, Bob</div>
<div><a href="content/CVPR2025/papers/Smith_Great_Paper_CVPR_2025_paper.pdf">pdf</a>
<a href="https://arxiv.org/abs/2501.00001">arXiv</a></div>
</dd>
<dt class="ptitle"><br>
<a href="content/CVPR2025/html/Lee_Another_Study_CVPR_2025_paper.html">Another Study on Transformers</a></dt>
<dd>
<div class="bibref">Lee, Carol</div>
<div><a href="content/CVPR2025/papers/Lee_Another_Study_CVPR_2025_paper.pdf">pdf</a></div>
</dd>
</dl>
</body></html>
"""


class TestParseOpenaccess:
    def test_extracts_papers(self):
        papers = _parse_openaccess(OPENACCESS_HTML, "https://openaccess.thecvf.com")
        assert len(papers) == 2

    def test_paper_title(self):
        papers = _parse_openaccess(OPENACCESS_HTML, "https://openaccess.thecvf.com")
        assert papers[0].title == "A Great Paper About Vision"

    def test_paper_authors(self):
        papers = _parse_openaccess(OPENACCESS_HTML, "https://openaccess.thecvf.com")
        assert papers[0].authors == ["Alice Smith", "Bob Jones"]

    def test_single_author(self):
        papers = _parse_openaccess(OPENACCESS_HTML, "https://openaccess.thecvf.com")
        assert papers[1].authors == ["Carol Lee"]

    def test_paper_pdf_link(self):
        papers = _parse_openaccess(OPENACCESS_HTML, "https://openaccess.thecvf.com")
        assert papers[0].link == "https://openaccess.thecvf.com/content/CVPR2025/papers/Smith_Great_Paper_CVPR_2025_paper.pdf"

    def test_selection_is_main(self):
        papers = _parse_openaccess(OPENACCESS_HTML, "https://openaccess.thecvf.com")
        assert papers[0].selection == "main"
```

**Note on HTML structure:** The CVF Open Access site uses `<dl>` (definition list) markup. Each paper is a `<dt class="ptitle">` containing an `<a>` for the title, followed by a `<dd>` containing a `<div class="bibref">` with "Last, First; Last, First" author format, and a `<div>` with PDF/arXiv links. The test HTML fixture above matches this structure. The actual HTML must be verified during implementation by fetching a real page — adjust the fixture and parser if the real structure differs.

**Note on author format:** CVF uses "Last, First" format separated by semicolons. The parser should convert to "First Last" format (e.g., "Smith, Alice" → "Alice Smith").

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cvf.py::TestParseOpenaccess -v`
Expected: FAIL — `_parse_openaccess` doesn't exist yet.

- [ ] **Step 3: Implement the Open Access parser**

Create `ppr/scrapers/cvf.py`:

```python
"""Scraper for CV conferences from CVF Open Access, CVF accepted-papers pages, and ECVA.

Covers CVPR, ICCV, WACV (via openaccess.thecvf.com or conference accepted-papers pages)
and ECCV (via ecva.net).
"""

import logging
from functools import partial

import requests
from bs4 import BeautifulSoup

from ppr.models import Paper

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


def _flip_name(name: str) -> str:
    """Convert 'Last, First Middle' to 'First Middle Last'."""
    parts = name.split(",", 1)
    if len(parts) == 2:
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name.strip()


def _parse_openaccess(html: str, base_url: str) -> list[Paper]:
    """Parse papers from a CVF Open Access HTML page.

    Structure: <dt class="ptitle"><a>Title</a></dt>
               <dd><div class="bibref">Last, First; Last, First</div>
                   <div><a href="...pdf">pdf</a></div></dd>
    """
    soup = BeautifulSoup(html, "html.parser")
    papers = []

    for dt in soup.select("dt.ptitle"):
        a = dt.find("a")
        if not a:
            continue
        title = a.get_text(strip=True)

        dd = dt.find_next_sibling("dd")
        if not dd:
            continue

        # Authors from <div class="bibref"> in "Last, First; Last, First" format
        bibref = dd.select_one("div.bibref")
        if bibref:
            authors = [_flip_name(n) for n in bibref.get_text().split(";") if n.strip()]
        else:
            authors = []

        # PDF link — first <a> whose href contains '/papers/' and ends with .pdf
        pdf_link = ""
        for link in dd.find_all("a"):
            href = link.get("href", "")
            if "/papers/" in href and href.endswith(".pdf"):
                if not href.startswith("http"):
                    href = f"{base_url}/{href}"
                pdf_link = href
                break

        papers.append(Paper(
            title=title,
            link=pdf_link,
            authors=authors,
            selection="main",
        ))

    return papers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cvf.py::TestParseOpenaccess -v`
Expected: All PASS.

- [ ] **Step 5: Verify parser against real CVF page**

Run a quick sanity check against the real site:

```bash
uv run python -c "
import requests
from ppr.scrapers.cvf import _parse_openaccess
resp = requests.get('https://openaccess.thecvf.com/WACV2025', timeout=60)
papers = _parse_openaccess(resp.text, 'https://openaccess.thecvf.com')
print(f'Found {len(papers)} papers')
if papers:
    p = papers[0]
    print(f'  Title: {p.title}')
    print(f'  Authors: {p.authors}')
    print(f'  Link: {p.link}')
"
```

Expected: Should find ~930 papers with valid titles, authors in "First Last" format, and PDF links. **If the HTML structure differs from the test fixture, update the fixture and parser accordingly before proceeding.**

- [ ] **Step 6: Commit**

```bash
git add ppr/scrapers/cvf.py tests/test_cvf.py
git commit -m "feat(cvf): add CVF Open Access parser for CVPR/ICCV/WACV"
```

---

## Task 4: CVF Scraper — Accepted Papers Parser

For conferences not yet on CVF Open Access (ICCV 2025, WACV 2026). These pages use `<strong>Title</strong>` + `<em>Author1 · Author2</em>` blocks.

**Files:**
- Modify: `ppr/scrapers/cvf.py` (add `_parse_accepted` function)
- Modify: `tests/test_cvf.py` (add tests)

- [ ] **Step 1: Write test for accepted papers parser**

Add to `tests/test_cvf.py`:

```python
from ppr.scrapers.cvf import _parse_accepted


ACCEPTED_HTML = """
<html><body>
<div id="content">
<strong>Vision Transformers for 3D Reconstruction</strong>
<em>Alice Smith · Bob Jones · Carol Lee</em>
Poster Session 3 &amp; Exhibit Hall
Exhibit Hall I #42

<strong>Learning to Grasp</strong>
<img src="/static/core/img/award.svg" title="Highlight">
<em>Dave Wilson · Eve Zhang</em>
Poster Session 1 &amp; Exhibit Hall
Exhibit Hall II #7
</div>
</body></html>
"""


class TestParseAccepted:
    def test_extracts_papers(self):
        papers = _parse_accepted(ACCEPTED_HTML)
        assert len(papers) == 2

    def test_paper_title(self):
        papers = _parse_accepted(ACCEPTED_HTML)
        assert papers[0].title == "Vision Transformers for 3D Reconstruction"

    def test_authors_split_on_middledot(self):
        papers = _parse_accepted(ACCEPTED_HTML)
        assert papers[0].authors == ["Alice Smith", "Bob Jones", "Carol Lee"]

    def test_no_pdf_link(self):
        papers = _parse_accepted(ACCEPTED_HTML)
        assert papers[0].link == ""

    def test_selection_is_main(self):
        papers = _parse_accepted(ACCEPTED_HTML)
        assert papers[0].selection == "main"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cvf.py::TestParseAccepted -v`
Expected: FAIL — `_parse_accepted` doesn't exist.

- [ ] **Step 3: Implement the accepted papers parser**

Add to `ppr/scrapers/cvf.py`:

```python
def _parse_accepted(html: str) -> list[Paper]:
    """Parse papers from CVF accepted-papers pages.

    Structure: <strong>Title</strong> followed by <em>Author1 · Author2</em>.
    Used for ICCV/WACV conferences not yet on CVF Open Access.
    """
    soup = BeautifulSoup(html, "html.parser")
    papers = []

    for strong in soup.find_all("strong"):
        title = strong.get_text(strip=True)
        if not title:
            continue

        # Find the next <em> before the next <strong>
        em = None
        for el in strong.next_elements:
            if el.name == "strong" and el != strong:
                break
            if el.name == "em":
                em = el
                break
        if not em:
            continue

        authors_text = em.get_text(strip=True)
        authors = [a.strip() for a in authors_text.split("\u00b7") if a.strip()]

        if not authors:
            continue

        papers.append(Paper(
            title=title,
            link="",
            authors=authors,
            selection="main",
        ))

    return papers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cvf.py::TestParseAccepted -v`
Expected: All PASS.

- [ ] **Step 5: Verify against real accepted papers page**

```bash
uv run python -c "
import requests
from ppr.scrapers.cvf import _parse_accepted
resp = requests.get('https://wacv.thecvf.com/Conferences/2026/AcceptedPapers', timeout=60,
    headers={'User-Agent': 'Mozilla/5.0'})
papers = _parse_accepted(resp.text)
print(f'Found {len(papers)} papers')
if papers:
    p = papers[0]
    print(f'  Title: {p.title}')
    print(f'  Authors: {p.authors}')
"
```

Expected: Should find papers with valid titles and authors. **If the HTML structure differs, update the fixture and parser accordingly.**

- [ ] **Step 6: Commit**

```bash
git add ppr/scrapers/cvf.py tests/test_cvf.py
git commit -m "feat(cvf): add accepted-papers parser for ICCV 2025, WACV 2026"
```

---

## Task 5: CVF Scraper — ECVA Parser for ECCV

ECCV is on `ecva.net/papers.php`, not CVF Open Access. Different HTML structure.

**Files:**
- Modify: `ppr/scrapers/cvf.py` (add `_parse_ecva` function)
- Modify: `tests/test_cvf.py` (add tests)

- [ ] **Step 1: Write test for ECVA parser**

Add to `tests/test_cvf.py`:

```python
from ppr.scrapers.cvf import _parse_ecva


ECVA_HTML = """
<html><body>
<dl>
<dt class="ptitle"><br>
<a href="papers/eccv_2024/papers_ECCV/html/00004_ECCV_2024_paper.php">Diffusion Models for Video Generation</a></dt>
<dd>
<div class="bibref">Wang, Xin; Park, Soo-Yeon</div>
<div>[<a href="papers/eccv_2024/papers_ECCV/papers/00004.pdf">pdf</a>]
[<a href="https://link.springer.com/chapter/10.1007/978-3-031-73232-4_1">DOI</a>]</div>
</dd>
<dt class="ptitle"><br>
<a href="papers/eccv_2024/papers_ECCV/html/00006_ECCV_2024_paper.php">Self-Supervised Depth Estimation</a></dt>
<dd>
<div class="bibref">Kim, Jun</div>
<div>[<a href="papers/eccv_2024/papers_ECCV/papers/00006.pdf">pdf</a>]</div>
</dd>
</dl>
</body></html>
"""


class TestParseEcva:
    def test_extracts_papers(self):
        papers = _parse_ecva(ECVA_HTML)
        assert len(papers) == 2

    def test_paper_title(self):
        papers = _parse_ecva(ECVA_HTML)
        assert papers[0].title == "Diffusion Models for Video Generation"

    def test_paper_authors(self):
        papers = _parse_ecva(ECVA_HTML)
        assert papers[0].authors == ["Xin Wang", "Soo-Yeon Park"]

    def test_paper_pdf_link(self):
        papers = _parse_ecva(ECVA_HTML)
        assert papers[0].link == "https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/00004.pdf"

    def test_selection_is_main(self):
        papers = _parse_ecva(ECVA_HTML)
        assert papers[0].selection == "main"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cvf.py::TestParseEcva -v`
Expected: FAIL.

- [ ] **Step 3: Implement the ECVA parser**

Add to `ppr/scrapers/cvf.py`:

```python
ECVA_BASE_URL = "https://www.ecva.net"


def _parse_ecva(html: str) -> list[Paper]:
    """Parse papers from ecva.net/papers.php.

    Same <dt>/<dd>/<div class="bibref"> structure as CVF Open Access,
    but PDF hrefs are relative to ecva.net.
    """
    soup = BeautifulSoup(html, "html.parser")
    papers = []

    for dt in soup.select("dt.ptitle"):
        a = dt.find("a")
        if not a:
            continue
        title = a.get_text(strip=True)

        dd = dt.find_next_sibling("dd")
        if not dd:
            continue

        bibref = dd.select_one("div.bibref")
        if bibref:
            authors = [_flip_name(n) for n in bibref.get_text().split(";") if n.strip()]
        else:
            authors = []

        pdf_link = ""
        for link in dd.find_all("a"):
            href = link.get("href", "")
            if href.endswith(".pdf") and "papers" in href:
                if not href.startswith("http"):
                    href = f"{ECVA_BASE_URL}/{href}"
                pdf_link = href
                break

        papers.append(Paper(
            title=title,
            link=pdf_link,
            authors=authors,
            selection="main",
        ))

    return papers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cvf.py::TestParseEcva -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add ppr/scrapers/cvf.py tests/test_cvf.py
git commit -m "feat(cvf): add ECVA parser for ECCV 2024"
```

---

## Task 6: CVF Scraper — Conference Registry & SCRAPERS Dict

Wire up the parsers to a `SCRAPERS` dict so the CLI can dispatch to them.

**Files:**
- Modify: `ppr/scrapers/cvf.py` (add scraping functions, conference config, SCRAPERS dict)
- Modify: `tests/test_cvf.py` (add SCRAPERS tests)

- [ ] **Step 1: Write test for SCRAPERS dict**

Add to `tests/test_cvf.py`:

```python
from ppr.scrapers.cvf import CVF_CONFERENCES, SCRAPERS


class TestCvfScrapersDict:
    def test_all_conferences_registered(self):
        for conf_id in CVF_CONFERENCES:
            assert conf_id in SCRAPERS, f"{conf_id} not in SCRAPERS"

    def test_expected_conference_ids(self):
        expected = {
            "cvpr_2023", "cvpr_2024", "cvpr_2025",
            "iccv_2023", "iccv_2025",
            "wacv_2023", "wacv_2024", "wacv_2025", "wacv_2026",
            "eccv_2024",
        }
        assert expected == set(CVF_CONFERENCES.keys())

    def test_scrapers_are_callable(self):
        for conf_id, scraper in SCRAPERS.items():
            assert callable(scraper), f"{conf_id} scraper is not callable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cvf.py::TestCvfScrapersDict -v`
Expected: FAIL — CVF_CONFERENCES and SCRAPERS don't exist yet.

- [ ] **Step 3: Add conference registry and scraping functions**

Add to `ppr/scrapers/cvf.py`:

```python
CVF_BASE_URL = "https://openaccess.thecvf.com"

CVF_CONFERENCES = {
    # CVF Open Access (published proceedings)
    "cvpr_2023": {"url": f"{CVF_BASE_URL}/CVPR2023?day=all", "parser": "openaccess"},
    "cvpr_2024": {"url": f"{CVF_BASE_URL}/CVPR2024?day=all", "parser": "openaccess"},
    "cvpr_2025": {"url": f"{CVF_BASE_URL}/CVPR2025?day=all", "parser": "openaccess"},
    "iccv_2023": {"url": f"{CVF_BASE_URL}/ICCV2023?day=all", "parser": "openaccess"},
    "wacv_2023": {"url": f"{CVF_BASE_URL}/WACV2023", "parser": "openaccess"},
    "wacv_2024": {"url": f"{CVF_BASE_URL}/WACV2024", "parser": "openaccess"},
    "wacv_2025": {"url": f"{CVF_BASE_URL}/WACV2025", "parser": "openaccess"},
    # CVF Accepted Papers (pre-publication)
    "iccv_2025": {"url": "https://iccv.thecvf.com/Conferences/2025/AcceptedPapers", "parser": "accepted"},
    "wacv_2026": {"url": "https://wacv.thecvf.com/Conferences/2026/AcceptedPapers", "parser": "accepted"},
    # ECVA
    "eccv_2024": {"url": "https://www.ecva.net/papers.php", "parser": "ecva"},
}


def _scrape_cvf(conf_id: str) -> list[Paper]:
    """Scrape papers for a CVF/ECVA conference."""
    conf = CVF_CONFERENCES[conf_id]
    url = conf["url"]
    parser_type = conf["parser"]

    logger.info("Scraping %s from %s (parser=%s)", conf_id, url, parser_type)
    response = requests.get(url, headers=HEADERS, timeout=120)
    response.raise_for_status()

    if parser_type == "openaccess":
        papers = _parse_openaccess(response.text, CVF_BASE_URL)
    elif parser_type == "accepted":
        papers = _parse_accepted(response.text)
    elif parser_type == "ecva":
        papers = _parse_ecva(response.text)
    else:
        raise ValueError(f"Unknown parser type: {parser_type}")

    logger.info("Found %d papers for %s", len(papers), conf_id)
    return papers


SCRAPERS = {conf_id: partial(_scrape_cvf, conf_id) for conf_id in CVF_CONFERENCES}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cvf.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add ppr/scrapers/cvf.py tests/test_cvf.py
git commit -m "feat(cvf): add conference registry and SCRAPERS dict"
```

---

## Task 7: Create RSS Scraper

RSS 2025 papers are listed in a `<table id="myTable">` at `roboticsconference.org/program/papers/`.

**Files:**
- Create: `ppr/scrapers/rss.py`
- Create: `tests/test_rss.py`

- [ ] **Step 1: Write tests**

Create `tests/test_rss.py`:

```python
from ppr.scrapers.rss import _parse_rss, RSS_CONFERENCES, SCRAPERS


RSS_HTML = """
<html><body>
<table id="myTable">
<thead><tr><th>#</th><th>Session</th><th>Title</th><th>Authors</th></tr></thead>
<tbody>
<tr>
<td>1</td>
<td>Perception and Navigation</td>
<td><a href="/program/papers/1/">LiDAR-based SLAM for Autonomous Driving</a></td>
<td>Alice Smith, Bob Jones, Carol Lee</td>
</tr>
<tr>
<td>2</td>
<td>VLA Models</td>
<td><a href="/program/papers/2/">Learning Dexterous Manipulation</a></td>
<td>Dave Wilson</td>
</tr>
</tbody>
</table>
</body></html>
"""


class TestParseRss:
    def test_extracts_papers(self):
        papers = _parse_rss(RSS_HTML)
        assert len(papers) == 2

    def test_paper_title(self):
        papers = _parse_rss(RSS_HTML)
        assert papers[0].title == "LiDAR-based SLAM for Autonomous Driving"

    def test_paper_authors(self):
        papers = _parse_rss(RSS_HTML)
        assert papers[0].authors == ["Alice Smith", "Bob Jones", "Carol Lee"]

    def test_single_author(self):
        papers = _parse_rss(RSS_HTML)
        assert papers[1].authors == ["Dave Wilson"]

    def test_paper_link(self):
        papers = _parse_rss(RSS_HTML)
        assert papers[0].link == "https://roboticsconference.org/program/papers/1/"

    def test_selection_is_main(self):
        papers = _parse_rss(RSS_HTML)
        assert papers[0].selection == "main"


class TestRssScrapersDict:
    def test_expected_conference_ids(self):
        assert set(RSS_CONFERENCES.keys()) == {"rss_2025"}

    def test_all_registered(self):
        for conf_id in RSS_CONFERENCES:
            assert conf_id in SCRAPERS

    def test_scrapers_are_callable(self):
        for conf_id, scraper in SCRAPERS.items():
            assert callable(scraper)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_rss.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement RSS scraper**

Create `ppr/scrapers/rss.py`:

```python
"""Scraper for RSS (Robotics: Science and Systems) conference papers.

RSS 2025 lists papers in an HTML table at roboticsconference.org.
"""

import logging
from functools import partial

import requests
from bs4 import BeautifulSoup

from ppr.models import Paper

logger = logging.getLogger(__name__)

RSS_BASE_URL = "https://roboticsconference.org"

RSS_CONFERENCES = {
    "rss_2025": {"url": f"{RSS_BASE_URL}/program/papers/"},
}


def _parse_rss(html: str) -> list[Paper]:
    """Parse papers from RSS program page.

    Structure: <table id="myTable"> with rows containing
    [number, session, title (<a>), authors (comma-separated)].
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="myTable")
    if not table:
        return []

    papers = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        title_a = cells[2].find("a")
        if not title_a:
            continue

        title = title_a.get_text(strip=True)
        href = title_a.get("href", "")
        if href and not href.startswith("http"):
            href = f"{RSS_BASE_URL}{href}"

        authors_text = cells[3].get_text(strip=True)
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]

        papers.append(Paper(
            title=title,
            link=href,
            authors=authors,
            selection="main",
        ))

    logger.info("Parsed %d papers from RSS", len(papers))
    return papers


def _scrape_rss(conf_id: str) -> list[Paper]:
    """Scrape papers for an RSS conference."""
    conf = RSS_CONFERENCES[conf_id]
    url = conf["url"]
    logger.info("Scraping %s from %s", conf_id, url)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    papers = _parse_rss(response.text)
    logger.info("Found %d papers for %s", len(papers), conf_id)
    return papers


SCRAPERS = {conf_id: partial(_scrape_rss, conf_id) for conf_id in RSS_CONFERENCES}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_rss.py -v`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add ppr/scrapers/rss.py tests/test_rss.py
git commit -m "feat(rss): add RSS 2025 scraper"
```

---

## Task 8: Extend ACL Scraper — Fix Author Delimiter + Add COLING 2025

The `_parse_paper_list` function splits authors only on commas, but COLING 2025 uses `" and "` between the last two authors. Also add COLING 2025 entry.

**Files:**
- Modify: `ppr/scrapers/acl.py:38` (fix author splitting)
- Modify: `ppr/scrapers/acl.py:230-239` (add COLING 2025 to SCRAPERS)

- [ ] **Step 1: Write test for author delimiter fix**

Create `tests/test_acl.py`:

```python
from ppr.scrapers.acl import _parse_paper_list
from bs4 import BeautifulSoup


class TestParseAuthorDelimiter:
    def test_comma_separated(self):
        html = '<ul><li><strong>Title</strong><em>Alice, Bob, Carol</em></li></ul>'
        soup = BeautifulSoup(html, "html.parser")
        papers = _parse_paper_list(soup, "main")
        assert papers[0].authors == ["Alice", "Bob", "Carol"]

    def test_and_separator(self):
        html = '<ul><li><strong>Title</strong><em>Alice, Bob and Carol</em></li></ul>'
        soup = BeautifulSoup(html, "html.parser")
        papers = _parse_paper_list(soup, "main")
        assert papers[0].authors == ["Alice", "Bob", "Carol"]

    def test_comma_and_mixed(self):
        html = '<ul><li><strong>Title</strong><em>Alice Smith, Bob Jones and Carol Lee</em></li></ul>'
        soup = BeautifulSoup(html, "html.parser")
        papers = _parse_paper_list(soup, "main")
        assert papers[0].authors == ["Alice Smith", "Bob Jones", "Carol Lee"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_acl.py::TestParseAuthorDelimiter::test_and_separator -v`
Expected: FAIL — `" and "` is not split, so last author will be `"Bob and Carol"`.

- [ ] **Step 3: Fix author splitting in `_parse_paper_list`**

In `ppr/scrapers/acl.py`, change line 38 from:

```python
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]
```

to:

```python
        authors_text = authors_text.replace(" and ", ", ")
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]
```

Also apply the same fix to `_parse_paper_paragraphs` at line 123. Change:

```python
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]
```

to:

```python
        authors_text = authors_text.replace(" and ", ", ")
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_acl.py -v`
Expected: All PASS.

- [ ] **Step 5: Add COLING 2025 scraper function and entry**

Add to `ppr/scrapers/acl.py` before the SCRAPERS dict:

```python
def scrape_coling_2025() -> list[Paper]:
    return _scrape_separate_pages("https://coling2025.org", {
        "main": "/program/main_conference_papers/",
        "industry": "/program/industry_track_papers/",
        "demo": "/program/demo_papers/",
    })
```

Add to the SCRAPERS dict:

```python
    "coling_2025": scrape_coling_2025,
```

- [ ] **Step 6: Commit**

```bash
git add ppr/scrapers/acl.py tests/test_acl.py
git commit -m "feat(acl): fix 'and' author delimiter, add COLING 2025"
```

---

## Task 9: Extend ACL Scraper — ACL Anthology Parser for EACL + COLING 2024

EACL 2023-2024 and COLING 2024 (LREC-COLING) are only on ACL Anthology, which uses a different Bootstrap HTML layout.

**Files:**
- Modify: `ppr/scrapers/acl.py` (add `_parse_anthology` function and entries)
- Modify: `tests/test_acl.py` (add tests)

- [ ] **Step 1: Write test for Anthology parser**

Add to `tests/test_acl.py`:

```python
from ppr.scrapers.acl import _parse_anthology


ANTHOLOGY_HTML = """
<html><body>
<section id="main">
<p class="d-sm-flex align-items-stretch">
<span class="d-block">
<strong><a href="/2024.eacl-long.1/">Efficient Fine-tuning of Language Models</a></strong><br/>
<a href="/people/a/alice-smith/">Alice Smith</a> |
<a href="/people/b/bob-jones/">Bob Jones</a>
</span>
</p>
<p class="d-sm-flex align-items-stretch">
<span class="d-block">
<strong><a href="/2024.eacl-long.2/">Multilingual Evaluation Benchmarks</a></strong><br/>
<a href="/people/c/carol-lee/">Carol Lee</a>
</span>
</p>
</section>
</body></html>
"""


class TestParseAnthology:
    def test_extracts_papers(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert len(papers) == 2

    def test_paper_title(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].title == "Efficient Fine-tuning of Language Models"

    def test_paper_authors(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].authors == ["Alice Smith", "Bob Jones"]

    def test_single_author(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[1].authors == ["Carol Lee"]

    def test_paper_link(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].link == "https://aclanthology.org/2024.eacl-long.1/"

    def test_selection(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].selection == "main"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_acl.py::TestParseAnthology -v`
Expected: FAIL.

- [ ] **Step 3: Implement the Anthology parser**

Add to `ppr/scrapers/acl.py`:

```python
ANTHOLOGY_BASE_URL = "https://aclanthology.org"


def _parse_anthology(html: str, selection: str) -> list[Paper]:
    """Parse papers from ACL Anthology volume pages.

    Structure: <p class="d-sm-flex ..."><span class="d-block">
               <strong><a href="/VOLUME.N/">Title</a></strong><br/>
               <a href="/people/...">Author</a> | <a>Author2</a>
               </span></p>
    """
    soup = BeautifulSoup(html, "html.parser")
    papers = []

    for p in soup.select("p.d-sm-flex"):
        strong = p.find("strong")
        if not strong:
            continue
        title_a = strong.find("a")
        if not title_a:
            continue
        title = title_a.get_text(strip=True)
        href = title_a.get("href", "")
        if href and not href.startswith("http"):
            href = f"{ANTHOLOGY_BASE_URL}{href}"

        # Authors are <a> tags inside the <span> after the <strong>
        span = p.find("span", class_="d-block")
        if not span:
            continue
        authors = []
        for a in span.find_all("a"):
            if a.find_parent("strong"):
                continue  # skip the title link
            author_href = a.get("href", "")
            if "/people/" in author_href:
                authors.append(a.get_text(strip=True))

        if not authors:
            continue

        papers.append(Paper(
            title=title,
            link=href,
            authors=authors,
            selection=selection,
        ))

    return papers


def _scrape_anthology(url: str, selection: str) -> list[Paper]:
    """Scrape papers from an ACL Anthology volume page."""
    logger.info("Scraping anthology: %s", url)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return _parse_anthology(response.text, selection)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_acl.py::TestParseAnthology -v`
Expected: All PASS.

- [ ] **Step 5: Add EACL and COLING 2024 scraper entries**

Add scraper functions and SCRAPERS entries to `ppr/scrapers/acl.py`:

```python
def scrape_eacl_2023() -> list[Paper]:
    return _scrape_anthology(
        f"{ANTHOLOGY_BASE_URL}/volumes/2023.eacl-main/", "main"
    )


def scrape_eacl_2024() -> list[Paper]:
    return _scrape_anthology(
        f"{ANTHOLOGY_BASE_URL}/volumes/2024.eacl-long/", "main"
    )


def scrape_coling_2024() -> list[Paper]:
    return _scrape_anthology(
        f"{ANTHOLOGY_BASE_URL}/volumes/2024.lrec-main/", "main"
    )
```

Add to the SCRAPERS dict:

```python
    "eacl_2023": scrape_eacl_2023,
    "eacl_2024": scrape_eacl_2024,
    "coling_2024": scrape_coling_2024,
```

- [ ] **Step 6: Verify against real Anthology page**

```bash
uv run python -c "
from ppr.scrapers.acl import _scrape_anthology
papers = _scrape_anthology('https://aclanthology.org/volumes/2024.eacl-long/', 'main')
print(f'Found {len(papers)} papers')
if papers:
    print(f'  Title: {papers[0].title}')
    print(f'  Authors: {papers[0].authors}')
    print(f'  Link: {papers[0].link}')
"
```

Expected: Should find ~181 papers with valid titles, authors, and anthology links. **If the HTML structure differs, update the fixture and parser accordingly.**

- [ ] **Step 7: Commit**

```bash
git add ppr/scrapers/acl.py tests/test_acl.py
git commit -m "feat(acl): add ACL Anthology parser for EACL/COLING 2024"
```

---

## Task 10: Integration — Wire Up Scrapers and Build Data

Connect new scraper modules to the main pipeline.

**Files:**
- Modify: `ppr/scrapers/__init__.py`
- Modify: `scripts/build_data.py:9-23` (VENUE_NAMES)
- Modify: `tests/test_build_data.py` (add venue name tests)

- [ ] **Step 1: Write tests for new venue names**

Add to `tests/test_build_data.py`:

```python
    def test_cvpr(self):
        assert parse_conference_id("cvpr_2025") == ("CVPR", 2025)

    def test_iccv(self):
        assert parse_conference_id("iccv_2023") == ("ICCV", 2023)

    def test_eccv(self):
        assert parse_conference_id("eccv_2024") == ("ECCV", 2024)

    def test_wacv(self):
        assert parse_conference_id("wacv_2025") == ("WACV", 2025)

    def test_icra(self):
        assert parse_conference_id("icra_2024") == ("ICRA", 2024)

    def test_iros(self):
        assert parse_conference_id("iros_2024") == ("IROS", 2024)

    def test_rss(self):
        assert parse_conference_id("rss_2024") == ("RSS", 2024)

    def test_ijcai(self):
        assert parse_conference_id("ijcai_2024") == ("IJCAI", 2024)

    def test_corl(self):
        assert parse_conference_id("corl_2024") == ("CoRL", 2024)

    def test_eacl(self):
        assert parse_conference_id("eacl_2024") == ("EACL", 2024)

    def test_coling(self):
        assert parse_conference_id("coling_2024") == ("COLING", 2024)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_build_data.py::TestParseConferenceId::test_cvpr -v`
Expected: FAIL — `parse_conference_id("cvpr_2025")` returns `("CVPR", 2025)` from the `.upper()` fallback, which actually passes. But `test_corl` will FAIL because `"corl".upper()` returns `"CORL"`, not `"CoRL"`. Run: `uv run pytest tests/test_build_data.py::TestParseConferenceId::test_corl -v`
Expected: FAIL.

- [ ] **Step 3: Add venue names to build_data.py**

In `scripts/build_data.py`, add to `VENUE_NAMES` dict after the ISSTA entry:

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

- [ ] **Step 4: Update `ppr/scrapers/__init__.py`**

Replace the file contents with:

```python
from ppr.scrapers.acl import SCRAPERS as ACL_SCRAPERS
from ppr.scrapers.aaai import SCRAPERS as AAAI_SCRAPERS
from ppr.scrapers.usenix import SCRAPERS as USENIX_SCRAPERS
from ppr.scrapers.dblp import SCRAPERS as DBLP_SCRAPERS
from ppr.scrapers.cvf import SCRAPERS as CVF_SCRAPERS
from ppr.scrapers.rss import SCRAPERS as RSS_SCRAPERS

SCRAPERS = {
    **ACL_SCRAPERS,
    **AAAI_SCRAPERS,
    **USENIX_SCRAPERS,
    **DBLP_SCRAPERS,
    **CVF_SCRAPERS,
    **RSS_SCRAPERS,
}
```

- [ ] **Step 5: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add ppr/scrapers/__init__.py scripts/build_data.py tests/test_build_data.py
git commit -m "feat: integrate new scrapers and add venue names"
```

---

## Task 11: End-to-End Smoke Test

Verify the full pipeline works by crawling one small conference from each new source.

**Files:** None (verification only)

- [ ] **Step 1: Test DBLP scraper (RSS 2023 — small, 113 papers)**

```bash
uv run ppr crawl rss_2023
```

Expected: `outputs/rss_2023/papers.jsonl` created with ~113 papers.

- [ ] **Step 2: Test CVF Open Access scraper (WACV 2025 — ~930 papers)**

```bash
uv run ppr crawl wacv_2025
```

Expected: `outputs/wacv_2025/papers.jsonl` created with ~930 papers.

- [ ] **Step 3: Test CVF Accepted Papers scraper (WACV 2026)**

```bash
uv run ppr crawl wacv_2026
```

Expected: `outputs/wacv_2026/papers.jsonl` created with papers (count depends on current site state).

- [ ] **Step 4: Test RSS scraper (RSS 2025 — ~163 papers)**

```bash
uv run ppr crawl rss_2025
```

Expected: `outputs/rss_2025/papers.jsonl` created with ~163 papers.

- [ ] **Step 5: Test ACL Anthology scraper (EACL 2024 — ~181 papers)**

```bash
uv run ppr crawl eacl_2024
```

Expected: `outputs/eacl_2024/papers.jsonl` created with ~181 papers.

- [ ] **Step 6: Spot-check output quality**

```bash
uv run python -c "
import json
for conf in ['rss_2023', 'wacv_2025', 'rss_2025', 'eacl_2024']:
    with open(f'outputs/{conf}/papers.jsonl') as f:
        papers = [json.loads(l) for l in f if l.strip()]
    p = papers[0]
    print(f'{conf}: {len(papers)} papers')
    print(f'  Title: {p[\"title\"]}')
    print(f'  Authors: {p.get(\"authors\", [])}')
    print(f'  Link: {p.get(\"link\", \"\")}')
    print()
"
```

Expected: Each conference has reasonable paper counts, titles are clean (no HTML entities), authors are `["First Last", ...]` format, links are present where expected.
