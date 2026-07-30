"""Tests for the CLI's own file handling.

Subcommand argument wiring is tested next to the module each subcommand drives
(`tests/test_discover.py` for `discover`, and so on); what lives here is the
behaviour `ppr/cli.py` itself owns.
"""

import pytest

from ppr import cli
from ppr.models import EmptyOverwriteError, Paper


def _paper(title: str) -> Paper:
    return Paper(title=title, link=f"https://x.test/{title}", authors=["A"], selection="main")


class TestSavePapers:
    def test_writes_under_the_conference_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli, "DATA_DIR", tmp_path)
        path = cli._save_papers([_paper("P1")], "ijcai_2026")
        assert path == tmp_path / "ijcai_2026" / "papers.jsonl"
        assert path.read_text(encoding="utf-8").strip() == _paper("P1").to_json()

    def test_refuses_to_erase_an_existing_crawl(self, tmp_path, monkeypatch):
        """A scraper that returns `[]` after a site redesign is the same failure
        as a swallowed API error, and must not truncate the last good crawl
        either -- the two save paths have to agree on that rule."""
        monkeypatch.setattr(cli, "DATA_DIR", tmp_path)
        saved = cli._save_papers([_paper("P1"), _paper("P2")], "ijcai_2026")
        before = saved.read_bytes()

        with pytest.raises(EmptyOverwriteError):
            cli._save_papers([], "ijcai_2026")

        assert saved.read_bytes() == before

    def test_first_crawl_of_a_venue_with_no_papers_still_writes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cli, "DATA_DIR", tmp_path)
        path = cli._save_papers([], "ijcai_2027")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == ""
