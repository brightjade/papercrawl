"""Build static JSON data files from JSONL paper outputs for the web app."""

import json
import sys
from collections import defaultdict
from pathlib import Path

VENUE_NAMES = {
    "iclr": "ICLR",
    "neurips": "NeurIPS",
    "icml": "ICML",
    "colm": "COLM",
    "emnlp": "EMNLP",
    "acl": "ACL",
    "naacl": "NAACL",
    "aaai": "AAAI",
    "usenix_security": "USENIX Security",
}


def parse_conference_id(conf_id: str) -> tuple[str, int]:
    """Extract venue display name and year from conference ID like 'iclr_2025'."""
    year = int(conf_id.rsplit("_", 1)[1])
    prefix = conf_id.rsplit("_", 1)[0]
    venue = VENUE_NAMES.get(prefix, prefix.upper())
    return venue, year


def load_papers(conf_dir: Path) -> list[dict]:
    """Load papers from a conference directory, preferring enriched data."""
    enriched = conf_dir / "papers_with_citations.jsonl"
    plain = conf_dir / "papers.jsonl"
    source = enriched if enriched.exists() else plain
    if not source.exists():
        return []
    papers = []
    with open(source) as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))
    return papers


def build_manifest_entry(conf_id: str, papers: list[dict]) -> dict:
    """Build a manifest entry for one conference."""
    venue, year = parse_conference_id(conf_id)
    has_citations = any("citation_count" in p for p in papers)
    tracks = sorted({p.get("selection", "") for p in papers} - {""})

    top_papers = []
    if has_citations:
        sorted_papers = sorted(
            [p for p in papers if "citation_count" in p],
            key=lambda p: p["citation_count"],
            reverse=True,
        )
        top_papers = [
            {"title": p["title"], "citation_count": p["citation_count"]}
            for p in sorted_papers[:3]
        ]

    return {
        "id": conf_id,
        "venue": venue,
        "year": year,
        "paper_count": len(papers),
        "has_citations": has_citations,
        "tracks": tracks,
        "top_papers": top_papers,
    }


def build_author_index(all_papers: dict[str, list[dict]]) -> list[dict]:
    """Build author index across all conferences."""
    author_data: dict[str, dict] = defaultdict(
        lambda: {"conferences": set(), "paper_count": 0, "total_citations": 0}
    )
    for conf_id, papers in all_papers.items():
        for paper in papers:
            for author in paper.get("authors", []):
                entry = author_data[author]
                entry["conferences"].add(conf_id)
                entry["paper_count"] += 1
                entry["total_citations"] += paper.get("citation_count", 0)

    return sorted(
        [
            {
                "name": name,
                "conferences": sorted(data["conferences"]),
                "paper_count": data["paper_count"],
                "total_citations": data["total_citations"],
            }
            for name, data in author_data.items()
        ],
        key=lambda a: a["total_citations"],
        reverse=True,
    )


def build_trends(all_papers: dict[str, list[dict]]) -> dict:
    """Build keyword and venue trend data."""
    keywords_by_year: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    venue_counts_by_year: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for conf_id, papers in all_papers.items():
        venue, year = parse_conference_id(conf_id)
        year_str = str(year)
        venue_counts_by_year[year_str][venue] += len(papers)
        for paper in papers:
            for kw in paper.get("keywords", []):
                if kw:
                    keywords_by_year[year_str][kw.lower()] += 1

    # Keep only top 50 keywords per year to limit file size
    trimmed_keywords: dict[str, dict[str, int]] = {}
    for year, kws in keywords_by_year.items():
        top = sorted(kws.items(), key=lambda x: x[1], reverse=True)[:50]
        trimmed_keywords[year] = dict(top)

    return {
        "keywords_by_year": trimmed_keywords,
        "venue_counts_by_year": dict(venue_counts_by_year),
    }


def build_all(outputs_dir: Path, out_dir: Path) -> None:
    """Build all static JSON files from JSONL outputs."""
    out_dir.mkdir(parents=True, exist_ok=True)

    all_papers: dict[str, list[dict]] = {}
    manifest: list[dict] = []

    for conf_dir in sorted(outputs_dir.iterdir()):
        if not conf_dir.is_dir():
            continue
        conf_id = conf_dir.name
        papers = load_papers(conf_dir)
        if not papers:
            continue
        all_papers[conf_id] = papers
        manifest.append(build_manifest_entry(conf_id, papers))

        # Write per-conference file
        with open(out_dir / f"{conf_id}.json", "w") as f:
            json.dump(papers, f, ensure_ascii=False)

    # Sort manifest by year desc, then venue name
    manifest.sort(key=lambda m: (-m["year"], m["venue"]))

    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    with open(out_dir / "authors.json", "w") as f:
        json.dump(build_author_index(all_papers), f, ensure_ascii=False)

    with open(out_dir / "trends.json", "w") as f:
        json.dump(build_trends(all_papers), f, ensure_ascii=False, indent=2)

    print(f"Built {len(manifest)} conferences -> {out_dir}")


if __name__ == "__main__":
    outputs_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs")
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("web/public/data")
    build_all(outputs_dir, out_dir)
