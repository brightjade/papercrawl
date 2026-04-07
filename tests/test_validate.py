import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from ppr.validate import (
    DBLP_VALIDATION_KEYS,
    DBLP_SOURCE_IDS,
    ValidationResult,
    fetch_dblp_count,
    validate_conference,
)


def _make_dblp_response(total: int, hits: list[dict] | None = None) -> dict:
    """Build a minimal DBLP API response."""
    if hits is None:
        hits = [
            {"info": {"title": f"Paper {i}.", "type": "Conference and Workshop Papers"}}
            for i in range(min(total, 1000))
        ]
    return {
        "result": {
            "hits": {
                "@total": str(total),
                "@sent": str(len(hits)),
                "@first": "0",
                "hit": hits,
            }
        }
    }


class TestFetchDblpCount:
    @patch("ppr.validate.requests.get")
    def test_single_key_counts_papers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_dblp_response(150)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        count = fetch_dblp_count(["db/conf/iclr/iclr2023.bht"])
        assert count == 150

    @patch("ppr.validate.time.sleep")
    @patch("ppr.validate.requests.get")
    def test_multiple_keys_sums_counts(self, mock_get, mock_sleep):
        resp1 = MagicMock()
        resp1.json.return_value = _make_dblp_response(100)
        resp1.raise_for_status = MagicMock()
        resp2 = MagicMock()
        resp2.json.return_value = _make_dblp_response(50)
        resp2.raise_for_status = MagicMock()
        mock_get.side_effect = [resp1, resp2]

        count = fetch_dblp_count(["key1.bht", "key2.bht"])
        assert count == 150

    @patch("ppr.validate.requests.get")
    def test_zero_total_returns_zero(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {"hits": {"@total": "0", "@sent": "0", "@first": "0"}}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        count = fetch_dblp_count(["db/conf/colm/colm2024.bht"])
        assert count == 0

    @patch("ppr.validate.time.sleep")
    @patch("ppr.validate.requests.get")
    def test_paginates_when_more_than_1000(self, mock_get, mock_sleep):
        page1_hits = [
            {"info": {"title": f"P{i}.", "type": "Conference and Workshop Papers"}}
            for i in range(1000)
        ]
        resp1 = MagicMock()
        resp1.json.return_value = _make_dblp_response(1200, page1_hits)
        resp1.raise_for_status = MagicMock()

        page2_hits = [
            {"info": {"title": f"Q{i}.", "type": "Conference and Workshop Papers"}}
            for i in range(200)
        ]
        resp2 = MagicMock()
        resp2.json.return_value = _make_dblp_response(1200, page2_hits)
        resp2.raise_for_status = MagicMock()

        mock_get.side_effect = [resp1, resp2]

        count = fetch_dblp_count(["db/conf/cvpr/cvpr2023.bht"])
        assert count == 1200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("ppr.validate.requests.get")
    def test_subtracts_editorship_entries(self, mock_get):
        hits = [
            {"info": {"title": "Proceedings", "type": "Editorship"}},
            {"info": {"title": "Paper 1.", "type": "Conference and Workshop Papers"}},
            {"info": {"title": "Paper 2.", "type": "Conference and Workshop Papers"}},
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_dblp_response(3, hits)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        count = fetch_dblp_count(["db/conf/iclr/iclr2023.bht"])
        assert count == 2


class TestValidateConference:
    def test_pass_when_counts_match(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "iclr_2023"
        conf_dir.mkdir()
        papers_file = conf_dir / "papers.jsonl"
        papers_file.write_text(
            "\n".join(json.dumps({"title": f"P{i}", "link": "", "authors": []}) for i in range(100))
        )
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)

        with patch("ppr.validate.fetch_dblp_count", return_value=100):
            result = validate_conference("iclr_2023")

        assert result.status == "PASS"
        assert result.scraped == 100
        assert result.dblp == 100

    def test_fail_when_counts_differ_beyond_tolerance(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "iclr_2023"
        conf_dir.mkdir()
        papers_file = conf_dir / "papers.jsonl"
        papers_file.write_text(
            "\n".join(json.dumps({"title": f"P{i}", "link": "", "authors": []}) for i in range(200))
        )
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)

        with patch("ppr.validate.fetch_dblp_count", return_value=100):
            result = validate_conference("iclr_2023", tolerance=0.1)

        assert result.status == "FAIL"
        assert result.scraped == 200
        assert result.dblp == 100

    def test_pass_within_tolerance(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "iclr_2023"
        conf_dir.mkdir()
        papers_file = conf_dir / "papers.jsonl"
        papers_file.write_text(
            "\n".join(json.dumps({"title": f"P{i}", "link": "", "authors": []}) for i in range(105))
        )
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)

        with patch("ppr.validate.fetch_dblp_count", return_value=100):
            result = validate_conference("iclr_2023", tolerance=0.1)

        assert result.status == "PASS"

    def test_skip_dblp_sourced_conference(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)
        result = validate_conference("icse_2024")
        assert result.status == "SKIP"

    def test_no_data_when_not_in_dblp(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "colm_2024"
        conf_dir.mkdir()
        (conf_dir / "papers.jsonl").write_text('{"title":"P","link":"","authors":[]}\n')
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)

        result = validate_conference("colm_2024")
        assert result.status == "NO_DATA"

    def test_no_data_when_no_output_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)
        result = validate_conference("iclr_2023")
        assert result.status == "NO_DATA"

    def test_no_data_when_dblp_returns_zero(self, tmp_path, monkeypatch):
        conf_dir = tmp_path / "iclr_2023"
        conf_dir.mkdir()
        (conf_dir / "papers.jsonl").write_text('{"title":"P","link":"","authors":[]}\n')
        monkeypatch.setattr("ppr.validate.OUTPUTS_DIR", tmp_path)

        with patch("ppr.validate.fetch_dblp_count", return_value=0):
            result = validate_conference("iclr_2023")

        assert result.status == "NO_DATA"


class TestMappingConsistency:
    def test_dblp_source_ids_matches_scraper(self):
        """DBLP_SOURCE_IDS must exactly match the conferences in dblp.py."""
        from ppr.scrapers.dblp import DBLP_CONFERENCES

        assert DBLP_SOURCE_IDS == set(DBLP_CONFERENCES.keys())

    def test_no_overlap_between_source_and_validation(self):
        """A conference should not be both DBLP-sourced and have validation keys."""
        overlap = DBLP_SOURCE_IDS & set(DBLP_VALIDATION_KEYS.keys())
        assert overlap == set(), f"Overlap: {overlap}"
