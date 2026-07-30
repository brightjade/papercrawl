"""Find conference-years that have published a list we have not registered."""

import logging
from pathlib import Path

from ppr.venues import REGISTRY_STEM

logger = logging.getLogger(__name__)

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"


def known_conference_ids() -> set[str]:
    """Every conference ID the project has registered a source for.

    Derived from committed files -- OpenReview configs plus the scraper
    registry -- rather than from `data/`. A conference is known once it is
    registered, not once it happens to have been crawled, and `data/` is
    gitignored, so a CI checkout would not have it to scan.
    """
    from ppr.scrapers import SCRAPERS

    ids = {p.stem for p in CONFIGS_DIR.glob("*.yaml") if p.stem != REGISTRY_STEM}
    return ids | set(SCRAPERS.keys())


def _matches_cadence(year: int, cadence: str) -> bool:
    if cadence == "biennial-odd":
        return year % 2 == 1
    if cadence == "biennial-even":
        return year % 2 == 0
    return True


def missing_years(
    prefix: str, cadence: str, known_ids: set[str], today_year: int
) -> list[int]:
    """Conference-years for `prefix` that could plausibly exist but are unregistered.

    Looks from the venue's earliest known year through next year -- the extra
    year catches a venue that publishes ahead of schedule, as OpenReview venues
    routinely do. A venue with nothing registered yields nothing: there is no
    baseline to extrapolate from, and an unregistered venue is caught by the
    registry drift test instead.
    """
    known = {
        int(cid.rsplit("_", 1)[1])
        for cid in known_ids
        if cid.rsplit("_", 1)[0] == prefix and cid.rsplit("_", 1)[1].isdigit()
    }
    if not known:
        return []

    return [
        year
        for year in range(min(known), today_year + 2)
        if _matches_cadence(year, cadence) and year not in known
    ]
