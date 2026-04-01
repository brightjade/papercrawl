import asyncio
import logging
import random
from pathlib import Path

import httpx
from tqdm import tqdm

from models import Paper

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


class CitationFetcher:
    def __init__(self, api_key: str | None = None, max_concurrency: int = 1):
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.headers = {"x-api-key": api_key} if api_key else {}
        self._last_request_time: float = 0.0

    async def _rate_limit(self) -> None:
        """Enforce minimum 1-second gap between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _fetch_one(self, client: httpx.AsyncClient, title: str) -> dict:
        """Fetch metadata for a single paper. Returns a dict of enrichment fields."""
        params = {
            "query": title,
            "fields": "title,citationCount,abstract,influentialCitationCount,referenceCount,tldr,publicationDate,fieldsOfStudy,openAccessPdf,externalIds",
            "limit": 1,
        }
        max_retries = 5

        async with self.semaphore:
            for attempt in range(max_retries):
                await self._rate_limit()
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
                    entry = data["data"][0]

                    # Extract tldr text from nested object
                    tldr_obj = entry.get("tldr")
                    tldr_text = tldr_obj.get("text", "") if isinstance(tldr_obj, dict) else ""

                    # Extract open access PDF URL from nested object
                    pdf_obj = entry.get("openAccessPdf")
                    pdf_url = pdf_obj.get("url", "") if isinstance(pdf_obj, dict) else ""

                    return {
                        "citation_count": entry.get("citationCount"),
                        "abstract": entry.get("abstract"),
                        "influential_citation_count": entry.get("influentialCitationCount"),
                        "reference_count": entry.get("referenceCount"),
                        "tldr": tldr_text,
                        "publication_date": entry.get("publicationDate") or "",
                        "fields_of_study": entry.get("fieldsOfStudy") or [],
                        "open_access_pdf": pdf_url,
                        "external_ids": entry.get("externalIds") or {},
                    }

                except httpx.HTTPStatusError:
                    await asyncio.sleep(2 ** attempt)
                except (KeyError, IndexError, TypeError):
                    return {}
                except httpx.RequestError:
                    await asyncio.sleep(2 ** attempt)

        return {}

    async def fetch_and_stream(
        self,
        papers: list[Paper],
        output_path: Path,
        append: bool = False,
    ) -> list[Paper]:
        """Fetch citations for all papers, streaming results to disk
        as they complete. Returns papers with citation_count set."""
        total = len(papers)
        results: list[Paper] = [None] * total  # type: ignore
        progress = tqdm(total=total, desc="Enriching papers", unit="paper")

        async def _process(idx: int, paper: Paper, client: httpx.AsyncClient, f):
            enrichment = await self._fetch_one(client, paper.title)
            if enrichment:
                paper.citation_count = enrichment.get("citation_count")
                paper.influential_citation_count = enrichment.get("influential_citation_count")
                paper.reference_count = enrichment.get("reference_count")
                paper.publication_date = enrichment.get("publication_date", "")
                paper.fields_of_study = enrichment.get("fields_of_study", [])
                paper.open_access_pdf = enrichment.get("open_access_pdf", "")
                paper.external_ids = enrichment.get("external_ids", {})
                if enrichment.get("tldr"):
                    paper.tldr = enrichment["tldr"]
                if not paper.abstract and enrichment.get("abstract"):
                    paper.abstract = enrichment["abstract"]
            results[idx] = paper
            line = paper.to_json() + "\n"
            f.write(line)
            f.flush()
            progress.update(1)
            found = paper.citation_count if paper.citation_count is not None else "?"
            progress.set_postfix_str(f"last: {found} cites")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(output_path, mode, encoding="utf-8") as f:
            async with httpx.AsyncClient(timeout=30.0) as client:
                tasks = [
                    _process(i, paper, client, f)
                    for i, paper in enumerate(papers)
                ]
                await asyncio.gather(*tasks)

        progress.close()
        return results

    async def fetch_all(self, titles: list[str]) -> list[dict]:
        """Simple batch fetch without streaming."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [self._fetch_one(client, t) for t in titles]
            return await asyncio.gather(*tasks)
