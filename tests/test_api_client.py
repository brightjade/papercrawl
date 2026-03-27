import json
from unittest.mock import MagicMock

import pytest

from api_client import OpenReviewAPIClient
from config import CrawlConfig
from models import Paper


def make_config():
    return CrawlConfig(
        name="ICLR", year=2025,
        venue_id="ICLR.cc/2025/Conference",
        selections={
            "oral": "ICLR 2025 Oral",
            "poster": "ICLR 2025 Poster",
        },
        conference_id="iclr_2025",
    )


def make_mock_note(forum_id="abc123", title="Test Paper", authors=None,
                   keywords=None, abstract="An abstract.",
                   venue="ICLR 2025 Oral"):
    note = MagicMock()
    note.forum = forum_id
    note.content = {
        "title": {"value": title},
        "authors": {"value": authors or ["Alice", "Bob"]},
        "keywords": {"value": keywords or ["ML"]},
        "abstract": {"value": abstract},
        "venueid": {"value": "ICLR.cc/2025/Conference"},
        "venue": {"value": venue},
    }
    return note


class TestOpenReviewAPIClient:
    def test_fetch_papers(self):
        mock_client = MagicMock()
        mock_client.get_all_notes.return_value = [
            make_mock_note("id1", "Paper One", venue="ICLR 2025 Oral"),
            make_mock_note("id2", "Paper Two", venue="ICLR 2025 Oral"),
            make_mock_note("id3", "Poster Paper", venue="ICLR 2025 Poster"),
        ]

        config = make_config()
        client = OpenReviewAPIClient(config, mock_client)
        papers = client.fetch_papers()

        assert len(papers) == 3
        orals = [p for p in papers if p.selection == "oral"]
        posters = [p for p in papers if p.selection == "poster"]
        assert len(orals) == 2
        assert len(posters) == 1
        assert orals[0].title == "Paper One"
        assert orals[0].forum_id == "id1"
        assert orals[0].link == "https://openreview.net/pdf?id=id1"
        assert orals[0].authors == ["Alice", "Bob"]
        assert orals[0].selection == "oral"

    def test_fetch_papers_filters_unknown_venues(self):
        mock_client = MagicMock()
        mock_client.get_all_notes.return_value = [
            make_mock_note("id1", "Oral", venue="ICLR 2025 Oral"),
            make_mock_note("id2", "Unknown", venue="ICLR 2025 Workshop"),
        ]

        config = make_config()
        client = OpenReviewAPIClient(config, mock_client)
        papers = client.fetch_papers()

        assert len(papers) == 1
        assert papers[0].selection == "oral"

    def test_save_papers(self, tmp_path):
        config = CrawlConfig(
            name="ICLR", year=2025, venue_id="X",
            selections={"oral": "X"},
            conference_id="iclr_2025",
        )
        save_path = tmp_path / "papers.jsonl"
        config.get_save_path = lambda: save_path

        client = OpenReviewAPIClient(config, MagicMock())
        papers = [
            Paper(title="P1", link="L1", authors=["A"], selection="oral", forum_id="id1"),
            Paper(title="P2", link="L2", authors=["B"], selection="poster", forum_id="id2"),
        ]
        client.save_papers(papers)

        assert save_path.exists()
        lines = save_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["title"] == "P1"
        assert json.loads(lines[0])["selection"] == "oral"

    def test_save_papers_write_mode_no_duplicates(self, tmp_path):
        config = CrawlConfig(
            name="ICLR", year=2025, venue_id="X",
            selections={"oral": "X"},
            conference_id="iclr_2025",
        )
        save_path = tmp_path / "papers.jsonl"
        config.get_save_path = lambda: save_path

        client = OpenReviewAPIClient(config, MagicMock())
        papers = [Paper(title="P1", link="L1", authors=["A"], selection="oral")]

        client.save_papers(papers)
        client.save_papers(papers)

        lines = save_path.read_text().strip().split("\n")
        assert len(lines) == 1
