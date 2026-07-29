"""Single point of contact with the Semantic Scholar Graph API.

Owns pacing and retry so every endpoint inherits the same backoff behavior.
Returns raw API dicts; mapping onto `Paper` attributes belongs in ppr/enrich.py.
"""

import asyncio
import logging
import random

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://api.semanticscholar.org/graph/v1"
MATCH_URL = f"{API_BASE}/paper/search/match"
BATCH_URL = f"{API_BASE}/paper/batch"
BULK_URL = f"{API_BASE}/paper/search/bulk"

# POST /paper/batch accepts at most 500 IDs per request.
BATCH_CHUNK_SIZE = 500

ENRICHMENT_FIELDS = (
    "title,citationCount,abstract,influentialCitationCount,referenceCount,"
    "tldr,publicationDate,fieldsOfStudy,openAccessPdf,externalIds"
)

MAX_RETRIES = 8


class S2Client:
    def __init__(self, api_key: str | None = None, min_interval: float = 1.0):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key else {}
        self._min_interval = min_interval
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def _rate_limit(self) -> None:
        """Enforce a minimum gap between requests, across all callers."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    @staticmethod
    def _backoff(attempt: int) -> float:
        return (2**attempt) + random.uniform(0, 1)

    async def _request_with_retry(
        self, client: httpx.AsyncClient, method: str, url: str, **kwargs
    ) -> httpx.Response | None:
        """Issue one request, retrying throttles and transport errors.

        Semantic Scholar returns 403 (not 429) when its shared anonymous pool is
        saturated. That is transient and IP-independent, so it is retried rather
        than treated as an auth failure.
        """
        for attempt in range(MAX_RETRIES):
            await self._rate_limit()
            try:
                response = await client.request(
                    method, url, headers=self.headers, **kwargs
                )
            except httpx.RequestError as exc:
                logger.debug("Transport error on %s: %s", url, exc)
                await asyncio.sleep(self._backoff(attempt))
                continue

            if response.status_code in (429, 403) or response.status_code >= 500:
                await asyncio.sleep(self._backoff(attempt))
                continue

            return response

        logger.warning("Giving up on %s after %d attempts", url, MAX_RETRIES)
        return None

    async def match_title(
        self, client: httpx.AsyncClient, title: str
    ) -> dict | None:
        """Look one paper up by title. Returns the raw entry, or None."""
        response = await self._request_with_retry(
            client,
            "GET",
            MATCH_URL,
            params={"query": title, "fields": ENRICHMENT_FIELDS},
        )
        if response is None or response.status_code == 404:
            return None
        try:
            return response.json()["data"][0]
        except (KeyError, IndexError, TypeError, ValueError):
            return None
