"""Per-conference enrichment: path selection, merging, guards, atomic writes."""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from tqdm import tqdm

from ppr.models import Paper
from ppr.s2_client import S2Client

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Lowercase and collapse whitespace, for cross-source title comparison."""
    return " ".join(title.lower().split())


def apply_enrichment(paper: Paper, entry: dict | None) -> Paper:
    """Merge one raw Semantic Scholar record into `paper`, in place.

    A None entry — or one with no citation count — means the API had nothing to
    say, so the existing record is left exactly as it was. Crawl-owned fields
    (title, authors, link, selection, keywords, forum_id) are never touched.
    """
    if entry is None or entry.get("citationCount") is None:
        return paper

    paper.citation_count = entry.get("citationCount")
    paper.influential_citation_count = entry.get("influentialCitationCount")
    paper.reference_count = entry.get("referenceCount")
    paper.publication_date = entry.get("publicationDate") or ""
    paper.fields_of_study = entry.get("fieldsOfStudy") or []

    pdf = entry.get("openAccessPdf")
    paper.open_access_pdf = pdf.get("url", "") if isinstance(pdf, dict) else ""

    paper.external_ids = entry.get("externalIds") or {}

    tldr = entry.get("tldr")
    tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""
    if tldr_text:
        paper.tldr = tldr_text

    if not paper.abstract and entry.get("abstract"):
        paper.abstract = entry["abstract"]

    return paper


def match_status_for(query_title: str, entry: dict | None) -> str:
    """Classify a title-based lookup result."""
    if entry is None:
        return "not_found"
    if normalize_title(query_title) == normalize_title(entry.get("title", "")):
        return "matched"
    logger.warning(
        "Title mismatch for '%s' — got '%s'", query_title, entry.get("title", "")
    )
    return "mismatch"


def carry_over(raw: Paper, prior: Paper) -> Paper:
    """Copy prior enrichment onto a freshly-crawled paper, in place.

    The raw crawl is authoritative for identity (title, authors, link,
    selection, keywords, forum_id); the enriched file holds the only copy of
    previous enrichment. Carrying it over means a paper whose refresh lookup
    comes back empty keeps its old values instead of silently losing them.
    """
    raw.citation_count = prior.citation_count
    raw.influential_citation_count = prior.influential_citation_count
    raw.reference_count = prior.reference_count
    raw.tldr = prior.tldr
    raw.publication_date = prior.publication_date
    raw.fields_of_study = prior.fields_of_study
    raw.open_access_pdf = prior.open_access_pdf
    raw.external_ids = prior.external_ids
    raw.match_status = prior.match_status
    if not raw.abstract and prior.abstract:
        raw.abstract = prior.abstract
    return raw


# A re-crawl that returns less than this fraction of the previously enriched
# paper count is treated as a failed crawl rather than a real shrinkage.
MIN_RAW_RATIO = 0.5


def read_papers(path: Path) -> list[Paper]:
    """Read a JSONL paper file. A missing or empty file reads as no papers."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [Paper.from_dict(json.loads(line)) for line in f if line.strip()]


def check_guards(raw: list[Paper], enriched: list[Paper]) -> str | None:
    """Decide whether it is safe to overwrite an existing enriched file.

    Returns a human-readable reason to skip, or None to proceed. Both guards
    compare against existing enrichment, so a conference being enriched for the
    first time is never blocked.
    """
    if not enriched:
        return None
    if not raw:
        return (
            f"papers.jsonl is empty or missing while papers_enriched.jsonl holds "
            f"{len(enriched)} papers — refusing to overwrite. Re-crawl first."
        )
    if len(raw) < MIN_RAW_RATIO * len(enriched):
        return (
            f"papers.jsonl has {len(raw)} papers, under "
            f"{MIN_RAW_RATIO:.0%} of the {len(enriched)} already enriched — "
            f"refusing to overwrite. Re-crawl first."
        )
    return None


def write_enriched(papers: list[Paper], path: Path) -> None:
    """Sort by citation count descending and replace `path` atomically.

    Writing to a temp file and renaming means an interrupted or failing run
    leaves the previous enriched file untouched.
    """
    ordered = sorted(
        papers,
        key=lambda p: p.citation_count if p.citation_count is not None else -1,
        reverse=True,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for paper in ordered:
                f.write(paper.to_json() + "\n")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# Semantic Scholar's own venue strings, for bulk prefetch. Only entries verified
# against the live API belong here — a prefix that is absent simply skips
# prefetch and falls back to per-title matching, which is always correct.
S2_VENUE_NAMES: dict[str, str] = {
    "icml": "International Conference on Machine Learning",
    "cvpr": "CVPR",
}


@dataclass
class EnrichResult:
    conf_id: str
    status: str  # "enriched" | "skipped" | "nothing-to-do"
    path: str = ""  # "refresh" | "id-cold" | "title-cold" | ""
    total: int = 0
    refreshed: int = 0
    cold: int = 0
    kept: int = 0
    reason: str = ""


def corpus_id_of(paper: Paper) -> str | None:
    """The paper's Semantic Scholar corpus ID, if a previous run found one."""
    corpus = (paper.external_ids or {}).get("CorpusId")
    return f"CorpusId:{corpus}" if corpus else None


def doi_id_of(paper: Paper) -> str | None:
    """A DOI recorded by the crawler, if this venue's source provides one."""
    prefix = "https://doi.org/"
    if paper.link and paper.link.startswith(prefix):
        return f"DOI:{paper.link[len(prefix):]}"
    return None


def route_papers(
    raw: list[Paper],
    prior_by_title: dict[str, Paper],
    *,
    full: bool,
    retry_unmatched: bool,
) -> tuple[list[Paper], list[Paper], list[Paper], list[Paper]]:
    """Split raw papers into (refresh, doi_cold, title_cold, kept).

    Papers are mutated in place: each one that has prior enrichment receives it
    via carry_over before being routed, so a lookup that comes back empty falls
    back to the previous values rather than to nothing.
    """
    refresh: list[Paper] = []
    doi_cold: list[Paper] = []
    title_cold: list[Paper] = []
    kept: list[Paper] = []

    for paper in raw:
        prior = prior_by_title.get(normalize_title(paper.title))
        if prior is not None and not full:
            carry_over(paper, prior)

        def _cold(p: Paper) -> None:
            (doi_cold if doi_id_of(p) else title_cold).append(p)

        if full:
            _cold(paper)
        elif prior is None:
            _cold(paper)
        elif corpus_id_of(prior):
            refresh.append(paper)
        elif retry_unmatched:
            _cold(paper)
        else:
            kept.append(paper)

    return refresh, doi_cold, title_cold, kept


def _dominant_path(refresh: list, doi_cold: list, title_cold: list) -> str:
    """Label the run by whichever path handled the most papers."""
    counts = {"refresh": len(refresh), "id-cold": len(doi_cold), "title-cold": len(title_cold)}
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] else ""


async def _run_batch(
    client: S2Client,
    http: httpx.AsyncClient,
    papers: list[Paper],
    id_of,
    *,
    set_match_status: bool,
) -> None:
    """Look papers up by ID and merge the results in place."""
    if not papers:
        return
    ids = [id_of(p) for p in papers]
    entries = await client.get_batch(http, ids)
    for paper, entry in zip(papers, entries):
        apply_enrichment(paper, entry)
        if set_match_status:
            paper.match_status = "matched" if entry else "not_found"


async def _run_title_cold(
    client: S2Client,
    http: httpx.AsyncClient,
    papers: list[Paper],
    conf_id: str,
) -> None:
    """Prefetch the venue in bulk, then match the remainder one at a time."""
    if not papers:
        return

    prefix, _, year_str = conf_id.rpartition("_")
    venue = S2_VENUE_NAMES.get(prefix)
    index: dict[str, dict] = {}
    if venue and year_str.isdigit():
        for entry in await client.bulk_search(http, venue, int(year_str)):
            title = entry.get("title")
            if title:
                index.setdefault(normalize_title(title), entry)
        logger.info(
            "Bulk prefetch for %s returned %d indexed papers", conf_id, len(index)
        )

    misses: list[Paper] = []
    for paper in papers:
        entry = index.get(normalize_title(paper.title))
        if entry is None:
            misses.append(paper)
            continue
        apply_enrichment(paper, entry)
        paper.match_status = "matched"

    if misses:
        logger.info(
            "%s: %d papers not covered by bulk prefetch, matching by title",
            conf_id,
            len(misses),
        )
    for paper in tqdm(misses, desc=f"Matching {conf_id}", unit="paper"):
        entry = await client.match_title(http, paper.title)
        apply_enrichment(paper, entry)
        paper.match_status = match_status_for(paper.title, entry)


async def enrich_conference(
    conf_id: str,
    client: S2Client,
    data_dir: Path,
    *,
    full: bool = False,
    retry_unmatched: bool = False,
) -> EnrichResult:
    """Enrich a single conference, choosing the cheapest workable path."""
    conf_dir = data_dir / conf_id
    raw = read_papers(conf_dir / "papers.jsonl")
    enriched = read_papers(conf_dir / "papers_enriched.jsonl")

    reason = check_guards(raw, enriched)
    if reason:
        logger.warning("Skipping %s: %s", conf_id, reason)
        return EnrichResult(conf_id, "skipped", reason=reason)

    if not raw:
        return EnrichResult(conf_id, "nothing-to-do")

    prior_by_title = {normalize_title(p.title): p for p in enriched}
    refresh, doi_cold, title_cold, kept = route_papers(
        raw, prior_by_title, full=full, retry_unmatched=retry_unmatched
    )

    async with httpx.AsyncClient(timeout=60.0) as http:
        await _run_batch(client, http, refresh, corpus_id_of, set_match_status=False)
        await _run_batch(client, http, doi_cold, doi_id_of, set_match_status=True)
        await _run_title_cold(client, http, title_cold, conf_id)

    write_enriched(raw, conf_dir / "papers_enriched.jsonl")

    return EnrichResult(
        conf_id=conf_id,
        status="enriched",
        path=_dominant_path(refresh, doi_cold, title_cold),
        total=len(raw),
        refreshed=len(refresh),
        cold=len(doi_cold) + len(title_cold),
        kept=len(kept),
    )


async def enrich_all(
    conf_ids: list[str],
    client: S2Client,
    data_dir: Path,
    *,
    full: bool = False,
    retry_unmatched: bool = False,
) -> list[EnrichResult]:
    """Enrich each conference in turn. One failure never stops the rest."""
    results = []
    for conf_id in conf_ids:
        logger.info("Enriching %s...", conf_id)
        try:
            results.append(
                await enrich_conference(
                    conf_id,
                    client,
                    data_dir,
                    full=full,
                    retry_unmatched=retry_unmatched,
                )
            )
        except Exception as exc:  # keep going; the summary reports the failure
            logger.exception("Failed to enrich %s", conf_id)
            results.append(EnrichResult(conf_id, "skipped", reason=str(exc)))
    return results


def format_enrich_summary(results: list[EnrichResult]) -> str:
    """Render the per-conference outcome table.

    Skips are printed, not merely logged, so a silently skipped conference can
    never be mistaken for a successful refresh.
    """
    lines = [
        "",
        f"{'Conference':<24} {'Status':<14} {'Path':<11} "
        f"{'Total':>7} {'Refresh':>8} {'Cold':>7} {'Kept':>6}  Note",
        "-" * 100,
    ]
    for r in results:
        lines.append(
            f"{r.conf_id:<24} {r.status:<14} {r.path:<11} "
            f"{r.total:>7} {r.refreshed:>8} {r.cold:>7} {r.kept:>6}  {r.reason}"
        )
    skipped = sum(1 for r in results if r.status == "skipped")
    enriched = sum(1 for r in results if r.status == "enriched")
    lines.append("")
    lines.append(f"{enriched} enriched, {skipped} skipped, {len(results)} total.")
    return "\n".join(lines)
