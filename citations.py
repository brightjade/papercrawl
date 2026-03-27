import asyncio
import json
import logging
import random
from pathlib import Path

import httpx
from tqdm import tqdm

from models import Paper

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class CitationFetcher:
    def __init__(self, api_key: str | None = None, max_concurrency: int = 5):
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.headers = {"x-api-key": api_key} if api_key else {}

    async def _fetch_one(
        self, client: httpx.AsyncClient, title: str
    ) -> int | None:
        params = {
            "query": title,
            "fields": "title,citationCount",
            "limit": 1,
        }
        max_retries = 5

        async with self.semaphore:
            for attempt in range(max_retries):
                try:
                    response = await client.get(
                        SEMANTIC_SCHOLAR_URL, params=params, headers=self.headers
                    )
                    if response.status_code == 429:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(wait)
                        continue

                    response.raise_for_status()
                    data = response.json()
                    return data["data"][0]["citationCount"]

                except httpx.HTTPStatusError:
                    await asyncio.sleep(2 ** attempt)
                except (KeyError, IndexError, TypeError):
                    return None
                except httpx.RequestError:
                    await asyncio.sleep(2 ** attempt)

        return None

    async def fetch_and_stream(
        self,
        papers: list[Paper],
        output_path: Path,
    ) -> list[Paper]:
        """Fetch citations for all papers, streaming results to disk
        as they complete. Returns papers with citation_count set."""
        total = len(papers)
        results: list[Paper] = [None] * total  # type: ignore
        progress = tqdm(total=total, desc="Fetching citations", unit="paper")

        async def _process(idx: int, paper: Paper, client: httpx.AsyncClient, f):
            count = await self._fetch_one(client, paper.title)
            paper.citation_count = count
            results[idx] = paper
            # Stream to disk immediately
            line = paper.to_json() + "\n"
            f.write(line)
            f.flush()
            progress.update(1)
            found = count if count is not None else "?"
            progress.set_postfix_str(f"last: {found} cites")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            async with httpx.AsyncClient(timeout=30.0) as client:
                tasks = [
                    _process(i, paper, client, f)
                    for i, paper in enumerate(papers)
                ]
                await asyncio.gather(*tasks)

        progress.close()
        return results

    async def fetch_all(self, titles: list[str]) -> list[int | None]:
        """Simple batch fetch without streaming (for backward compat)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [self._fetch_one(client, t) for t in titles]
            return await asyncio.gather(*tasks)
