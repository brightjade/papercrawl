"""Scraper for AAAI conference proceedings from ojs.aaai.org.

AAAI publishes proceedings through the AAAI Open Journal Systems (OJS).
Each volume is split into multiple issues (technical tracks + special tracks).
"""

import logging
from functools import partial

import requests
from bs4 import BeautifulSoup

from models import Paper

logger = logging.getLogger(__name__)

# Issue IDs for each year's main conference (technical tracks + special tracks).
# Excludes IAAI, EAAI, student abstracts, undergrad consortium, and demos.
AAAI_ISSUES = {
    "aaai_2023": list(range(548, 560)),   # Vol 37: tracks 1-11 (548-558), special (559)
    "aaai_2024": list(range(576, 596)),   # Vol 38: tracks 1-18 (576-593), special (594-595)
    "aaai_2025": list(range(624, 651)),   # Vol 39: tracks 1-25 (624-648), special (649-650)
}

BASE_URL = "https://ojs.aaai.org/index.php/AAAI/issue/view"


def _scrape_aaai_issue(issue_id: int) -> list[Paper]:
    """Scrape papers from a single OJS issue page."""
    url = f"{BASE_URL}/{issue_id}"
    logger.info("Scraping %s", url)
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    response = requests.get(url, timeout=30, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    papers = []
    for div in soup.select("div.obj_article_summary"):
        a = div.select_one("h3.title a")
        if not a:
            continue
        title = a.get_text(strip=True)
        if not title:
            continue
        authors_div = div.select_one("div.authors")
        if not authors_div:
            continue
        authors_text = authors_div.get_text(strip=True)
        authors = [auth.strip() for auth in authors_text.split(",") if auth.strip()]
        if not authors:
            continue
        link = a.get("href", "")
        papers.append(Paper(
            title=title,
            link=link,
            authors=authors,
            selection="accepted",
        ))
    return papers


def _scrape_aaai(conf_id: str) -> list[Paper]:
    """Scrape all issues for an AAAI conference year."""
    issue_ids = AAAI_ISSUES[conf_id]
    all_papers = []
    for issue_id in issue_ids:
        papers = _scrape_aaai_issue(issue_id)
        logger.info("  Issue %d: %d papers", issue_id, len(papers))
        all_papers.extend(papers)
    logger.info("Total: %d papers for %s", len(all_papers), conf_id)
    return all_papers


SCRAPERS = {conf_id: partial(_scrape_aaai, conf_id) for conf_id in AAAI_ISSUES}
