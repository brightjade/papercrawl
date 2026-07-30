import json
from unittest.mock import MagicMock

import pytest

from ppr.api_client import OpenReviewAPIClient
from ppr.config import CrawlConfig
from ppr.models import Paper


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


import pytest

from ppr.api_client import EmptyCrawlError, OpenReviewAPIClient
from ppr.models import EmptyOverwriteError


class TestEmptyCrawlGuard:
    def _client(self, venue_values, selections):
        from unittest.mock import MagicMock

        notes = []
        for v in venue_values:
            n = MagicMock()
            n.content = {"venue": {"value": v}, "title": {"value": "T"},
                         "authors": {"value": ["A"]}}
            n.forum = "f"
            notes.append(n)
        or_client = MagicMock()
        or_client.get_all_notes.return_value = notes

        config = MagicMock()
        config.venue_id = "X/2026/Conference"
        config.api_version = 2
        config.selections = selections
        config.extra_venue_ids = []
        return OpenReviewAPIClient(config, or_client)

    def test_raises_when_every_note_is_filtered_away(self):
        """CoRL 2024: 264 notes, selections matching none of them."""
        client = self._client(["CoRL 2024"] * 264,
                              {"oral": "CoRL 2024 Oral", "poster": "CoRL 2024 Poster"})
        with pytest.raises(EmptyCrawlError) as exc:
            client.fetch_papers()
        assert "264" in str(exc.value)
        assert "CoRL 2024" in str(exc.value)  # names the venue strings actually seen

    def test_succeeds_when_selections_match(self):
        client = self._client(["CoRL 2024"] * 3, {"main": "CoRL 2024"})
        assert len(client.fetch_papers()) == 3

    def test_no_notes_at_all_is_not_an_error(self):
        client = self._client([], {"main": "X"})
        assert client.fetch_papers() == []


class TestSaveGuard:
    def _client(self, tmp_path):
        config = CrawlConfig(
            name="CoRL", year=2024, venue_id="X",
            selections={"poster": "X"},
            conference_id="corl_2024",
        )
        save_path = tmp_path / "papers.jsonl"
        config.get_save_path = lambda: save_path
        return OpenReviewAPIClient(config, MagicMock()), save_path

    def test_refuses_to_erase_an_existing_crawl(self, tmp_path):
        """`fetch_papers` returns `[]` on an OpenReviewException, so the save
        path is the second door onto the CoRL 2024 failure -- an empty file
        written over a good one while the log says "Saved 0 papers"."""
        client, save_path = self._client(tmp_path)
        client.save_papers([Paper(title="P1", link="L1", authors=["A"], selection="poster")])
        before = save_path.read_bytes()

        with pytest.raises(EmptyOverwriteError):
            client.save_papers([])

        assert save_path.read_bytes() == before

    def test_first_crawl_of_an_empty_venue_still_writes(self, tmp_path):
        client, save_path = self._client(tmp_path)
        client.save_papers([])
        assert save_path.exists() and save_path.read_text() == ""
