from ppr.scrapers.dblp import _clean_author


class TestCleanAuthor:
    def test_strips_four_digit_suffix(self):
        assert _clean_author("Hao Zhong 0001") == "Hao Zhong"

    def test_strips_different_suffix(self):
        assert _clean_author("Wei Meng 0003") == "Wei Meng"

    def test_no_suffix_unchanged(self):
        assert _clean_author("John Smith") == "John Smith"

    def test_name_ending_in_digits_not_suffix(self):
        # Only strip if preceded by space and exactly 4 digits at end
        assert _clean_author("Agent 47") == "Agent 47"

    def test_empty_string(self):
        assert _clean_author("") == ""


from unittest.mock import patch, MagicMock
from ppr.scrapers.dblp import _fetch_dblp


def _make_dblp_response(hits: list[dict], total: int) -> dict:
    """Build a minimal DBLP API response."""
    return {
        "result": {
            "hits": {
                "@total": str(total),
                "@sent": str(len(hits)),
                "@first": "0",
                "hit": [{"info": h} for h in hits],
            }
        }
    }


class TestFetchDblp:
    @patch("ppr.scrapers.dblp.requests.get")
    def test_returns_paper_info_dicts(self, mock_get):
        hits = [
            {
                "title": "Paper One.",
                "authors": {"author": [{"text": "Alice 0001"}]},
                "ee": "https://doi.org/10.1145/1",
                "venue": "ICSE",
                "year": "2024",
            },
            {
                "title": "Paper Two.",
                "authors": {"author": [{"text": "Bob"}]},
                "ee": "https://doi.org/10.1145/2",
                "venue": "ICSE",
                "year": "2024",
            },
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_dblp_response(hits, total=2)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_dblp("db/conf/icse/icse2024.bht")
        assert len(result) == 2
        assert result[0]["title"] == "Paper One."
        assert result[1]["authors"]["author"][0]["text"] == "Bob"

    @patch("ppr.scrapers.dblp.requests.get")
    def test_filters_by_number(self, mock_get):
        hits = [
            {
                "title": "FSE Paper.",
                "authors": {"author": [{"text": "Alice"}]},
                "ee": "https://doi.org/10.1145/1",
                "number": "FSE",
            },
            {
                "title": "ISSTA Paper.",
                "authors": {"author": [{"text": "Bob"}]},
                "ee": "https://doi.org/10.1145/2",
                "number": "ISSTA",
            },
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_dblp_response(hits, total=2)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_dblp("db/journals/pacmse/pacmse2.bht", number="FSE")
        assert len(result) == 1
        assert result[0]["title"] == "FSE Paper."

    @patch("ppr.scrapers.dblp.time.sleep")
    @patch("ppr.scrapers.dblp.requests.get")
    def test_paginates_when_more_than_1000(self, mock_get, mock_sleep):
        # First page: 1000 hits out of 1200 total
        page1_hits = [{"title": f"P{i}.", "authors": {"author": [{"text": "A"}]}, "ee": "https://x"} for i in range(1000)]
        resp1 = MagicMock()
        resp1.json.return_value = _make_dblp_response(page1_hits, total=1200)
        resp1.raise_for_status = MagicMock()

        # Second page: remaining 200
        page2_hits = [{"title": f"Q{i}.", "authors": {"author": [{"text": "B"}]}, "ee": "https://y"} for i in range(200)]
        resp2 = MagicMock()
        resp2.json.return_value = _make_dblp_response(page2_hits, total=1200)
        resp2.raise_for_status = MagicMock()

        mock_get.side_effect = [resp1, resp2]

        result = _fetch_dblp("db/conf/kbse/ase2025.bht")
        assert len(result) == 1200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("ppr.scrapers.dblp.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"hits": {"@total": "0", "@sent": "0", "@first": "0"}}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_dblp("db/conf/icse/icse2099.bht")
        assert result == []
