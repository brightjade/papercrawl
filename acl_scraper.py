"""Scraper for ACL-family conference websites (EMNLP, ACL, NAACL).

These conferences don't publish accepted papers on OpenReview,
so we scrape their conference websites instead.
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from models import Paper

logger = logging.getLogger(__name__)


def _parse_paper_list(soup: BeautifulSoup, selection: str) -> list[Paper]:
    """Parse papers from a <ul> of <li><strong>Title</strong><em>Authors</em></li>."""
    papers = []
    for li in soup.select("li"):
        strong = li.find("strong")
        em = li.find("em")
        if not strong:
            continue
        title = strong.get_text(strip=True)
        authors_text = em.get_text(strip=True) if em else ""
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]
        if not authors:
            continue
        papers.append(Paper(
            title=title,
            link="",
            authors=authors,
            selection=selection,
        ))
    return papers


def _scrape_separate_pages(base_url: str, pages: dict[str, str]) -> list[Paper]:
    """Scrape conferences where each track has its own URL (EMNLP, ACL)."""
    all_papers = []
    for selection, path in pages.items():
        url = f"{base_url}{path}"
        logger.info("Scraping %s from %s", selection, url)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        papers = _parse_paper_list(soup, selection)
        logger.info("  Found %d papers", len(papers))
        all_papers.extend(papers)
    return all_papers


def _scrape_single_page(url: str, section_map: dict[str, str]) -> list[Paper]:
    """Scrape conferences where all tracks are on one page with headings (NAACL)."""
    logger.info("Scraping all tracks from %s", url)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    all_papers = []
    for heading in soup.find_all(re.compile(r"^h[1-4]$")):
        heading_text = heading.get_text(strip=True).lower()
        selection = None
        for pattern, sel_name in section_map.items():
            if pattern in heading_text:
                selection = sel_name
                break
        if selection is None:
            continue

        # Collect all <li> elements until the next heading
        papers = []
        for sibling in heading.find_next_siblings():
            if sibling.name and re.match(r"^h[1-4]$", sibling.name):
                break
            if sibling.name == "ul":
                papers.extend(_parse_paper_list(sibling, selection))
        logger.info("  %s: %d papers", selection, len(papers))
        all_papers.extend(papers)

    return all_papers


# Conference-specific scrapers

def scrape_emnlp_2025() -> list[Paper]:
    return _scrape_separate_pages("https://2025.emnlp.org", {
        "main": "/program/main_papers/",
        "findings": "/program/find_papers/",
        "industry": "/program/ind_papers/",
    })


def scrape_acl_2025() -> list[Paper]:
    return _scrape_separate_pages("https://2025.aclweb.org", {
        "main": "/program/main_papers/",
        "findings": "/program/find_papers/",
        "industry": "/program/ind_papers/",
    })


def scrape_naacl_2025() -> list[Paper]:
    return _scrape_single_page(
        "https://2025.naacl.org/program/accepted_papers/",
        {
            "long paper": "main",
            "short paper": "main",
            "findings": "findings",
            "industry": "industry",
        },
    )


SCRAPERS = {
    "emnlp_2025": scrape_emnlp_2025,
    "acl_2025": scrape_acl_2025,
    "naacl_2025": scrape_naacl_2025,
}
