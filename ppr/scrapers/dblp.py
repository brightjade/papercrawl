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
