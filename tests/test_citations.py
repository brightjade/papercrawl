import asyncio
import json

import httpx
import pytest
import respx

from citations import CitationFetcher, SEMANTIC_SCHOLAR_URL
from models import Paper


def _match_response(entry: dict, status=200) -> httpx.Response:
    """Helper to wrap an entry in the match endpoint's response format."""
    return httpx.Response(status, json={"data": [entry]})


class TestCitationFetcher:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_success(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=_match_response({
                "title": "Test Paper",
                "citationCount": 42,
                "abstract": "An abstract.",
                "influentialCitationCount": 5,
                "referenceCount": 30,
                "tldr": {"model": "tldr@v2", "text": "A summary."},
                "publicationDate": "2025-01-15",
                "fieldsOfStudy": ["Computer Science"],
                "openAccessPdf": {"url": "https://example.com/paper.pdf"},
                "externalIds": {"ArXiv": "1234.5678"},
            })
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Test Paper")
        assert result["citation_count"] == 42
        assert result["abstract"] == "An abstract."
        assert result["influential_citation_count"] == 5
        assert result["reference_count"] == 30
        assert result["tldr"] == "A summary."
        assert result["publication_date"] == "2025-01-15"
        assert result["fields_of_study"] == ["Computer Science"]
        assert result["open_access_pdf"] == "https://example.com/paper.pdf"
        assert result["external_ids"] == {"ArXiv": "1234.5678"}
        assert result["match_status"] == "matched"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_not_found(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(404)
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Unknown Paper")
        assert result == {"match_status": "not_found"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_rate_limit_then_success(self):
        route = respx.get(SEMANTIC_SCHOLAR_URL)
        route.side_effect = [
            httpx.Response(429),
            _match_response({
                "title": "Test",
                "citationCount": 10,
                "abstract": None,
                "influentialCitationCount": None,
                "referenceCount": None,
                "tldr": None,
                "publicationDate": None,
                "fieldsOfStudy": None,
                "openAccessPdf": None,
                "externalIds": None,
            }),
        ]
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Test")
        assert result["citation_count"] == 10
        assert result["abstract"] is None
        assert result["match_status"] == "matched"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_all(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=_match_response({
                "title": "T",
                "citationCount": 5,
                "abstract": "Abs",
                "influentialCitationCount": 1,
                "referenceCount": 10,
                "tldr": {"text": "Summary"},
                "publicationDate": "2025-01-01",
                "fieldsOfStudy": ["CS"],
                "openAccessPdf": {"url": "https://example.com/p.pdf"},
                "externalIds": {"DOI": "10.x"},
            })
        )
        fetcher = CitationFetcher(max_concurrency=2)
        results = await fetcher.fetch_all(["T", "T", "T"])
        assert len(results) == 3
        assert all(r["citation_count"] == 5 for r in results)
        assert all(r["abstract"] == "Abs" for r in results)

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_server_error(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(500)
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "Fail Paper")
        assert result == {"match_status": "not_found"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_and_stream(self, tmp_path):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=_match_response({
                "title": "A",
                "citationCount": 7,
                "abstract": "Some abstract",
                "influentialCitationCount": 2,
                "referenceCount": 15,
                "tldr": {"text": "Short summary"},
                "publicationDate": "2025-03-01",
                "fieldsOfStudy": ["Computer Science"],
                "openAccessPdf": {"url": "https://example.com/paper.pdf"},
                "externalIds": {"ArXiv": "2501.00001"},
            })
        )
        papers = [
            Paper(title="A", link="L1", authors=["X"], selection="oral"),
            Paper(title="A", link="L2", authors=["Y"], selection="poster"),
        ]
        output = tmp_path / "citations.jsonl"
        fetcher = CitationFetcher(max_concurrency=2)
        results = await fetcher.fetch_and_stream(papers, output)

        assert len(results) == 2
        assert all(p.citation_count == 7 for p in results)
        assert all(p.abstract == "Some abstract" for p in results)
        assert all(p.influential_citation_count == 2 for p in results)
        assert all(p.reference_count == 15 for p in results)
        assert all(p.tldr == "Short summary" for p in results)
        assert all(p.fields_of_study == ["Computer Science"] for p in results)
        assert all(p.match_status == "matched" for p in results)

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert data["citation_count"] == 7
            assert data["influential_citation_count"] == 2
            assert data["tldr"] == "Short summary"
            assert data["match_status"] == "matched"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_and_stream_preserves_existing_abstract(self, tmp_path):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=_match_response({
                "title": "A",
                "citationCount": 3,
                "abstract": "S2 abstract",
                "influentialCitationCount": 1,
                "referenceCount": 5,
                "tldr": None,
                "publicationDate": None,
                "fieldsOfStudy": None,
                "openAccessPdf": None,
                "externalIds": None,
            })
        )
        papers = [
            Paper(title="A", link="L1", authors=["X"], selection="oral", abstract="OpenReview abstract"),
        ]
        output = tmp_path / "enriched.jsonl"
        fetcher = CitationFetcher(max_concurrency=2)
        results = await fetcher.fetch_and_stream(papers, output)

        assert results[0].abstract == "OpenReview abstract"
        assert results[0].citation_count == 3
        assert results[0].match_status == "matched"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_one_title_mismatch(self):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=_match_response({
                "title": "Completely Different Paper",
                "citationCount": 100,
                "abstract": "Wrong abstract.",
                "influentialCitationCount": 10,
                "referenceCount": 50,
                "tldr": {"text": "Wrong summary."},
                "publicationDate": "2025-01-01",
                "fieldsOfStudy": ["Biology"],
                "openAccessPdf": None,
                "externalIds": {},
            })
        )
        fetcher = CitationFetcher()
        async with httpx.AsyncClient() as client:
            result = await fetcher._fetch_one(client, "My Actual Paper Title")
        assert result["match_status"] == "mismatch"
        # Data is still returned so the user can inspect it
        assert result["citation_count"] == 100

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_and_stream_not_found_sets_status(self, tmp_path):
        respx.get(SEMANTIC_SCHOLAR_URL).mock(
            return_value=httpx.Response(404)
        )
        papers = [
            Paper(title="Nonexistent Paper", link="L1", authors=["X"], selection="oral"),
        ]
        output = tmp_path / "enriched.jsonl"
        fetcher = CitationFetcher(max_concurrency=1)
        results = await fetcher.fetch_and_stream(papers, output)

        assert results[0].match_status == "not_found"
        assert results[0].citation_count is None
