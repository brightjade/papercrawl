"""Scraper for ACL-family conference websites (EMNLP, ACL, NAACL).

These conferences don't publish accepted papers on OpenReview,
so we scrape their conference websites instead.
"""

import logging
import re

import requests
from bs4 import BeautifulSoup

from ppr.models import Paper

logger = logging.getLogger(__name__)


def _parse_paper_list(soup: BeautifulSoup, selection: str) -> list[Paper]:
    """Parse papers from <li> elements containing title and authors.
    Handles: <li><strong>Title</strong><em>Authors</em></li>
         and: <li><p><strong>Title</strong></p><p>Authors</p></li>"""
    papers = []
    for li in soup.select("li"):
        strong = li.find("strong")
        if not strong:
            continue
        title = strong.get_text(strip=True)
        # Try <em> first, then second <p> tag, then remaining text
        em = li.find("em")
        if em:
            authors_text = em.get_text(strip=True)
        else:
            ps = li.find_all("p")
            if len(ps) >= 2:
                authors_text = ps[1].get_text(strip=True)
            else:
                authors_text = ""
        authors_text = authors_text.replace(" and ", ", ")
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

        # Collect elements until the next heading
        papers = []
        for sibling in heading.find_next_siblings():
            if sibling.name and re.match(r"^h[1-4]$", sibling.name):
                break
            if sibling.name == "ul":
                parsed = _parse_paper_list(sibling, selection)
                if not parsed:
                    parsed = _parse_paper_paragraphs(sibling, selection)
                papers.extend(parsed)
            elif sibling.name == "p" and sibling.find("strong"):
                parsed = _parse_paper_paragraphs(
                    BeautifulSoup(str(sibling), "html.parser"), selection
                )
                papers.extend(parsed)
        logger.info("  %s: %d papers", selection, len(papers))
        all_papers.extend(papers)

    return all_papers


def _parse_paper_paragraphs(soup: BeautifulSoup, selection: str) -> list[Paper]:
    """Parse papers from <p><strong>Title</strong> Authors</p> format.
    Handles authors after <br/>, <em>, or as bare text after the title."""
    papers = []
    for p in soup.find_all("p"):
        strong = p.find("strong")
        if not strong:
            continue
        title = strong.get_text(strip=True)
        # Try authors from <em>, then after <br/>, then remaining text
        em = p.find("em")
        br = p.find("br")
        if em:
            authors_text = em.get_text(strip=True)
        elif br and br.next_sibling:
            authors_text = str(br.next_sibling).strip()
        else:
            full_text = p.get_text()
            authors_text = full_text[len(title):].strip()
        authors_text = authors_text.replace(" and ", ", ")
        authors = [a.strip() for a in authors_text.split(",") if a.strip()]
        papers.append(Paper(
            title=title,
            link="",
            authors=authors,
            selection=selection,
        ))
    return papers


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


def _scrape_paragraph_pages(base_url: str, pages: dict[str, str]) -> list[Paper]:
    """Scrape conferences using <p><strong>Title</strong><br/>Authors</p> format."""
    all_papers = []
    for selection, path in pages.items():
        url = f"{base_url}{path}"
        logger.info("Scraping %s from %s", selection, url)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        papers = _parse_paper_paragraphs(soup, selection)
        logger.info("  Found %d papers", len(papers))
        all_papers.extend(papers)
    return all_papers


def scrape_emnlp_2023() -> list[Paper]:
    return _scrape_paragraph_pages("https://2023.emnlp.org", {
        "main": "/program/accepted_main_conference/",
        "findings": "/program/accepted_findings/",
        "industry": "/program/industry/",
    })


def scrape_emnlp_2024() -> list[Paper]:
    return _scrape_paragraph_pages("https://2024.emnlp.org", {
        "main": "/program/accepted_main_conference/",
        "findings": "/program/accepted_findings/",
        "industry": "/program/industry/",
    })


def scrape_acl_2023() -> list[Paper]:
    return _scrape_paragraph_pages("https://2023.aclweb.org", {
        "main": "/program/accepted_main_conference/",
        "findings": "/program/accepted_findings/",
        "industry": "/program/accepted_industry_track/",
    })


def scrape_acl_2024() -> list[Paper]:
    return _scrape_separate_pages("https://2024.aclweb.org", {
        "main": "/program/main_conference_papers/",
        "findings": "/program/finding_papers/",
    })


def scrape_naacl_2024() -> list[Paper]:
    papers = _scrape_single_page(
        "https://2024.naacl.org/program/accepted_papers/",
        {
            "long paper": "main",
            "short paper": "main",
            "findings": "findings",
        },
    )
    # Industry track is on a separate page -- parse all <li> directly
    url = "https://2024.naacl.org/program/accepted_papers_industry/"
    logger.info("Scraping industry from %s", url)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    industry = _parse_paper_list(soup, "industry")
    logger.info("  Found %d papers", len(industry))
    papers.extend(industry)
    return papers


def scrape_coling_2025() -> list[Paper]:
    return _scrape_separate_pages("https://coling2025.org", {
        "main": "/program/main_conference_papers/",
        "industry": "/program/industry_track_papers/",
        "demo": "/program/demo_papers/",
    })


SCRAPERS = {
    "emnlp_2023": scrape_emnlp_2023,
    "acl_2023": scrape_acl_2023,
    "emnlp_2024": scrape_emnlp_2024,
    "acl_2024": scrape_acl_2024,
    "naacl_2024": scrape_naacl_2024,
    "coling_2025": scrape_coling_2025,
    "emnlp_2025": scrape_emnlp_2025,
    "acl_2025": scrape_acl_2025,
    "naacl_2025": scrape_naacl_2025,
}
