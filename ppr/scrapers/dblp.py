"""Scraper for SE conferences (ICSE, FSE, ASE, ISSTA) via the DBLP API.

DBLP provides a free JSON search API with CC0-licensed metadata.
All four conferences are indexed, including PACMSE journal articles
for FSE 2024+ and ISSTA 2025+.
"""

import html
import logging
import re
import time
from functools import partial

import requests

from ppr.models import Paper


def _clean_author(name: str) -> str:
    """Strip DBLP disambiguation suffix from author name.

    DBLP appends ' 0001', ' 0002', etc. to disambiguate authors with
    identical names. E.g., 'Hao Zhong 0001' -> 'Hao Zhong'.
    """
    return re.sub(r"\s+\d{4}$", "", name)


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
    total = 0

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

        title = html.unescape(hit.get("title", ""))
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
