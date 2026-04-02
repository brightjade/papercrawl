"""Scraper for USENIX Security conference accepted papers.

USENIX publishes accepted papers on their Drupal-based website.
The technical-sessions page lists all papers with titles, authors, and affiliations.
Requires a browser User-Agent header to avoid 403 responses.
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

USENIX_CONFERENCES = {
    "usenix_security_2023": "usenixsecurity23",
    "usenix_security_2024": "usenixsecurity24",
    "usenix_security_2025": "usenixsecurity25",
}


def _parse_authors(text: str) -> list[str]:
    """Parse authors from USENIX format: 'Name1 and Name2,Affil;Name3,Affil'.

    Authors and affiliations are separated by commas within semicolon-delimited
    groups. Multiple authors in the same group are separated by 'and' or commas
    before the affiliation.
    """
    authors = []
    for group in text.split(";"):
        name_part = group.strip().split(",", 1)[0].strip()
        for name in name_part.replace(" and ", ", ").split(","):
            name = name.strip()
            if name:
                authors.append(name)
    return authors


def _scrape_usenix(conf_id: str) -> list[Paper]:
    """Scrape all accepted papers from a USENIX Security technical-sessions page."""
    slug = USENIX_CONFERENCES[conf_id]
    url = f"https://www.usenix.org/conference/{slug}/technical-sessions"
    logger.info("Scraping %s from %s", conf_id, url)

    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    papers = []
    for article in soup.select("article.node-paper"):
        link_tag = article.select_one("h2 a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        if href and not href.startswith("http"):
            href = f"https://www.usenix.org{href}"

        auth_div = article.select_one(".field-name-field-paper-people-text")
        if auth_div:
            authors = _parse_authors(auth_div.get_text(strip=True))
        else:
            authors = []

        if not title:
            continue

        papers.append(Paper(
            title=title,
            link=href,
            authors=authors,
            selection="accepted",
        ))

    logger.info("Found %d papers for %s", len(papers), conf_id)
    return papers


SCRAPERS = {conf_id: partial(_scrape_usenix, conf_id) for conf_id in USENIX_CONFERENCES}
