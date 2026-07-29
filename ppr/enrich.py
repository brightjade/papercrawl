"""Per-conference enrichment: path selection, merging, guards, atomic writes."""

import json
import logging
import os
from pathlib import Path

from ppr.models import Paper

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
