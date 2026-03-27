import asyncio
import json

import httpx
import pytest
import respx

from citations import CitationFetcher, SEMANTIC_SCHOLAR_URL
from models import Paper


class TestCitationFetcher:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_success(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"title": "Test", "citationCount": 42}]},
            )
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Test Paper")
        assert result == 42

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_not_found(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Unknown Paper")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_rate_limit_then_success(self):
        route = respx.get(SEMANTIC_SCHOLAR_URL)
        route.side_effect = [
            httpx.Response(429),
            httpx.Response(
                200,
                json={"data": [{"title": "Test", "citationCount": 10}]},
            ),
        ]
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Test")
        assert result == 10

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_all(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"title": "T", "citationCount": 5}]},
            )
        )
        fetcher = CitationFetcher(max_concurrency=2)
        results = await fetcher.fetch_all(["Paper A", "Paper B", "Paper C"])
        assert len(results) == 3
        assert all(r == 5 for r in results)

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_server_error(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(500)
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Fail Paper")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_and_stream(self, tmp_path):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"title": "T", "citationCount": 7}]},
            )
        )
        papers = [
            Paper(title="A", link="L1", authors=["X"], selection="oral"),
            Paper(title="B", link="L2", authors=["Y"], selection="poster"),
        ]
        output = tmp_path / "citations.jsonl"
        fetcher = CitationFetcher(max_concurrency=2)
        results = await fetcher.fetch_and_stream(papers, output)

        assert len(results) == 2
        assert all(p.citation_count == 7 for p in results)

        # Check file was written
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert data["citation_count"] == 7
