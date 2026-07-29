import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from ppr.s2_client import (
    BATCH_CHUNK_SIZE,
    MATCH_URL,
    S2Client,
)


@pytest.fixture
def no_sleep(monkeypatch):
    """Make backoff instant so retry tests do not actually wait."""
    monkeypatch.setattr("ppr.s2_client.asyncio.sleep", AsyncMock())


def _client() -> S2Client:
    return S2Client(min_interval=0.0)


class TestMatchTitle:
    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_raw_entry(self):
        respx.get(MATCH_URL).mock(
            return_value=httpx.Response(
                200, json={"data": [{"title": "Test Paper", "citationCount": 42}]}
            )
        )
        async with httpx.AsyncClient() as client:
            entry = await _client().match_title(client, "Test Paper")
        assert entry == {"title": "Test Paper", "citationCount": 42}

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_returns_none(self):
        respx.get(MATCH_URL).mock(return_value=httpx.Response(404))
        async with httpx.AsyncClient() as client:
            entry = await _client().match_title(client, "Nonexistent")
        assert entry is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_data_returns_none(self):
        respx.get(MATCH_URL).mock(return_value=httpx.Response(200, json={"data": []}))
        async with httpx.AsyncClient() as client:
            entry = await _client().match_title(client, "Nothing")
        assert entry is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_then_success(self, no_sleep):
        route = respx.get(MATCH_URL)
        route.side_effect = [
            httpx.Response(429),
            httpx.Response(200, json={"data": [{"title": "T", "citationCount": 10}]}),
        ]
        async with httpx.AsyncClient() as client:
            entry = await _client().match_title(client, "T")
        assert entry["citationCount"] == 10

    @respx.mock
    @pytest.mark.asyncio
    async def test_403_is_retried_not_fatal(self, no_sleep):
        route = respx.get(MATCH_URL)
        route.side_effect = [
            httpx.Response(403),
            httpx.Response(200, json={"data": [{"title": "T", "citationCount": 1}]}),
        ]
        async with httpx.AsyncClient() as client:
            entry = await _client().match_title(client, "T")
        assert entry["citationCount"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_persistent_500_returns_none(self, no_sleep):
        respx.get(MATCH_URL).mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            entry = await _client().match_title(client, "Fail")
        assert entry is None


class TestClientConfig:
    def test_api_key_sets_header(self):
        assert S2Client(api_key="k").headers == {"x-api-key": "k"}

    def test_no_api_key_sends_no_header(self):
        assert S2Client().headers == {}

    def test_batch_chunk_size_is_api_maximum(self):
        assert BATCH_CHUNK_SIZE == 500

    @pytest.mark.asyncio
    async def test_rate_limit_spaces_requests(self):
        c = S2Client(min_interval=0.05)
        start = asyncio.get_event_loop().time()
        await c._rate_limit()
        await c._rate_limit()
        assert asyncio.get_event_loop().time() - start >= 0.05
