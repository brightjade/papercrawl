from unittest.mock import MagicMock, patch

from ppr.validate import DBLP_VALIDATION_KEYS, DBLP_SOURCE_IDS, fetch_dblp_count


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

    @patch("ppr.validate.requests.get")
    def test_multiple_keys_sums_counts(self, mock_get):
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
