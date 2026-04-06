"""Scraper for RSS (Robotics: Science and Systems) conference papers.

The program/papers/ page lists all accepted papers in a table with columns:
[number, session, title (<a href>), authors (comma-separated)].
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

    Expected: <table id="myTable"> with rows [number, session, title (<a>), authors].
    Authors are comma-separated plain text; a hidden <div class="content"> duplicates
    the author text and is ignored.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="myTable")
    if not table:
        logger.warning("No <table id='myTable'> found on RSS page")
        return []

    papers = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            # Skip header row (<th>) and any malformed rows
            continue

        # Title is in the 3rd cell (index 2) as an <a> tag
        title_cell = cells[2]
        link_tag = title_cell.find("a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        if not title:
            continue

        href = link_tag.get("href", "")
        if href and not href.startswith("http"):
            href = f"{RSS_BASE_URL}{href}"

        # Authors are in the 4th cell (index 3), comma-separated plain text.
        # A hidden <div class="content"> duplicates the text — remove it first.
        author_cell = cells[3]
        hidden_div = author_cell.find("div", class_="content")
        if hidden_div:
            hidden_div.decompose()
        author_text = author_cell.get_text(strip=True)
        authors = [a.strip() for a in author_text.split(",") if a.strip()]

        papers.append(Paper(
            title=title,
            link=href,
            authors=authors,
            selection="main",
        ))

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
