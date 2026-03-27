import logging
import os
from collections import Counter

import openreview

from config import CrawlConfig
from models import Paper

logger = logging.getLogger(__name__)


def create_openreview_client(
    username: str | None = None,
    password: str | None = None,
) -> openreview.api.OpenReviewClient:
    """Create and authenticate an OpenReview client (one login)."""
    resolved_username = username or os.environ.get("OPENREVIEW_USERNAME")
    resolved_password = password or os.environ.get("OPENREVIEW_PASSWORD")
    if not resolved_username or not resolved_password:
        logger.warning(
            "No OpenReview credentials provided. "
            "Set OPENREVIEW_USERNAME and OPENREVIEW_PASSWORD env vars "
            "or pass --username/--password. "
            "Sign up for free at https://openreview.net/signup"
        )
    return openreview.api.OpenReviewClient(
        baseurl="https://api2.openreview.net",
        username=resolved_username,
        password=resolved_password,
    )


class OpenReviewAPIClient:
    def __init__(
        self,
        config: CrawlConfig,
        client: openreview.api.OpenReviewClient,
    ):
        self.config = config
        self.client = client

    def fetch_papers(self, selections: dict[str, str] | None = None) -> list[Paper]:
        """Fetch accepted papers, tagged with their selection type.
        If selections is None, uses all selections from config."""
        sel_map = selections or self.config.selections
        invitation = f"{self.config.venue_id}/-/Submission"

        logger.info(
            "Fetching accepted papers for %s %s (invitation=%s)",
            self.config.name, self.config.year, invitation,
        )

        try:
            notes = self.client.get_all_notes(
                invitation=invitation,
                content={"venueid": self.config.venue_id},
            )
        except openreview.OpenReviewException as e:
            logger.error(
                "Failed to fetch papers: %s. "
                "Check that the venue ID is correct and credentials are valid.",
                e,
            )
            return []

        logger.info("Found %d accepted papers total", len(notes))

        # Reverse map: venue string -> selection name
        venue_to_selection = {v: k for k, v in sel_map.items()}

        papers = []
        for note in notes:
            venue_str = note.content.get("venue", {}).get("value", "")
            selection = venue_to_selection.get(venue_str)
            if selection is None:
                continue

            content = {
                k: v.get("value") for k, v in note.content.items()
            }
            paper = Paper(
                title=content.get("title", ""),
                link=f"https://openreview.net/pdf?id={note.forum}",
                authors=content.get("authors", []),
                selection=selection,
                keywords=content.get("keywords", []),
                abstract=content.get("abstract", ""),
                forum_id=note.forum,
            )
            papers.append(paper)

        counts = Counter(p.selection for p in papers)
        for sel, count in counts.most_common():
            logger.info("  %s: %d papers", sel, count)

        return papers

    def save_papers(self, papers: list[Paper]) -> None:
        save_path = self.config.get_save_path()
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            for paper in papers:
                f.write(paper.to_json() + "\n")

        logger.info("Saved %d papers to %s", len(papers), save_path)

    def discover_venue_ids(self, prefix: str) -> list[str]:
        """List venue IDs matching a prefix. Useful for finding the right
        venue ID strings when creating new configs."""
        logger.info("Discovering venue IDs with prefix: %s", prefix)
        try:
            venues = self.client.get_group(prefix)
        except openreview.OpenReviewException as e:
            logger.error("Could not find venue '%s': %s", prefix, e)
            return []
        if venues and hasattr(venues, "members"):
            return venues.members
        return []
