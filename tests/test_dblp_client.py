"""Tests for the one implementation of how the project talks to DBLP."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from ppr import dblp_client
from ppr.dblp_client import MAX_RETRIES, MIN_INTERVAL, DblpUnavailable, query

PARAMS = {"q": "toc:db/conf/icse/icse2026.bht:", "h": 1, "f": 0, "format": "json"}
PAYLOAD = {"result": {"hits": {"@total": "245"}}}


def _response(status=200, payload=None, headers=None):
    r = MagicMock()
    r.status_code = status
    # A real dict, not an auto-vivified MagicMock attribute: `.get(...)` on an
    # unconfigured MagicMock returns another MagicMock rather than `None`,
    # which would make Retry-After parsing see a bogus non-None value.
    r.headers = headers or {}
    r.json = lambda: payload if payload is not None else PAYLOAD
    return r


@pytest.fixture(autouse=True)
def reset_pacing(monkeypatch):
    """The request clock is module state shared by every caller; a test must not
    inherit the previous test's turn."""
    monkeypatch.setattr(dblp_client, "_last_request", 0.0)


@pytest.fixture
def slept(monkeypatch):
    calls: list[float] = []
    monkeypatch.setattr("ppr.dblp_client.time.sleep", lambda s: calls.append(s))
    return calls


class TestQuery:
    def test_returns_the_parsed_payload(self, slept):
        with patch("ppr.dblp_client.requests.get", return_value=_response()) as g:
            assert query(PARAMS) == PAYLOAD
        assert g.call_args.kwargs["params"] == PARAMS

    @pytest.mark.parametrize("status", sorted(dblp_client.RETRYABLE_STATUSES))
    def test_retries_every_retryable_status_then_succeeds(self, slept, status):
        with patch("ppr.dblp_client.requests.get", side_effect=[_response(status), _response()]):
            assert query(PARAMS) == PAYLOAD

    def test_persistent_throttling_raises_rather_than_returning_a_number(self, slept):
        """The whole point of the exception: a throttled query reported as a
        count makes `ppr validate` announce a mismatch that is not real."""
        with patch("ppr.dblp_client.requests.get", return_value=_response(429)) as g:
            with pytest.raises(DblpUnavailable) as exc:
                query(PARAMS)
        assert "429" in str(exc.value)
        assert g.call_count == MAX_RETRIES

    def test_network_error_is_retried_then_raises(self, slept):
        with patch("ppr.dblp_client.requests.get", side_effect=requests.RequestException("boom")):
            with pytest.raises(DblpUnavailable) as exc:
                query(PARAMS)
        assert "RequestException" in str(exc.value)

    def test_network_error_recovers_on_a_retry(self, slept):
        with patch(
            "ppr.dblp_client.requests.get",
            side_effect=[requests.RequestException("boom"), _response()],
        ):
            assert query(PARAMS) == PAYLOAD

    def test_a_non_retryable_error_raises_immediately(self, slept):
        with patch("ppr.dblp_client.requests.get", return_value=_response(404)) as g:
            with pytest.raises(DblpUnavailable) as exc:
                query(PARAMS)
        assert "404" in str(exc.value)
        assert g.call_count == 1

    def test_unparseable_body_raises(self, slept):
        r = _response()
        r.json = MagicMock(side_effect=ValueError("not json"))
        with patch("ppr.dblp_client.requests.get", return_value=r):
            with pytest.raises(DblpUnavailable):
                query(PARAMS)

    def test_retry_after_is_honored_over_the_backoff_guess(self, slept):
        """DBLP's own Retry-After is a measurement; 2**attempt is a guess that
        should only apply when the server does not say."""
        throttled = _response(429, headers={"Retry-After": "30"})
        with patch("ppr.dblp_client.requests.get", side_effect=[throttled, _response()]):
            assert query(PARAMS) == PAYLOAD
        assert 30.0 in slept

    def test_a_retry_after_http_date_falls_back_to_the_backoff(self, slept):
        throttled = _response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})
        with patch("ppr.dblp_client.requests.get", side_effect=[throttled, _response()]):
            assert query(PARAMS) == PAYLOAD
        assert slept


class TestPacing:
    def test_consecutive_queries_are_spaced_by_the_crawl_delay(self, slept):
        """Two calls back to back with no real wait between them, so the second
        must sleep close to the full interval. An implementation that
        under-sleeps (a hardcoded 1s, say) fails this."""
        with patch("ppr.dblp_client.requests.get", return_value=_response()):
            query(PARAMS)
            query(PARAMS)
        assert max(slept) > MIN_INTERVAL - 0.05
        assert max(slept) <= MIN_INTERVAL

    def test_pacing_is_shared_across_callers(self, slept):
        """`ppr validate` and the discovery sweep hit one host from one machine.
        Pacing that each module tracked separately would not be pacing at all,
        which is why the clock lives in this module and not in either caller."""
        from ppr import discover, validate

        assert validate.dblp_client is dblp_client
        assert discover.dblp_client is dblp_client
