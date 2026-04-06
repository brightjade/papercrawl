"""Scraper for SE conferences (ICSE, FSE, ASE, ISSTA) via the DBLP API.

DBLP provides a free JSON search API with CC0-licensed metadata.
All four conferences are indexed, including PACMSE journal articles
for FSE 2024+ and ISSTA 2025+.
"""

import logging
import re
import time

import requests


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
