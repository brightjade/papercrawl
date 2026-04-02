import json
import os
import tempfile
from pathlib import Path

import pytest

from scripts.build_data import (
    parse_conference_id,
    load_papers,
    build_manifest_entry,
    build_author_index,
    build_trends,
    build_all,
)


@pytest.fixture
def sample_outputs(tmp_path):
    """Create a minimal outputs directory with two conferences."""
    iclr_dir = tmp_path / "iclr_2025"
    iclr_dir.mkdir()
    papers = [
        {
            "title": "Paper A",
            "authors": ["Alice", "Bob"],
            "selection": "oral",
            "keywords": ["nlp", "transformers"],
            "abstract": "Abstract A",
            "link": "https://example.com/a",
            "citation_count": 100,
        },
        {
            "title": "Paper B",
            "authors": ["Bob", "Carol"],
            "selection": "poster",
            "keywords": ["vision"],
            "abstract": "Abstract B",
            "link": "https://example.com/b",
            "citation_count": 50,
        },
        {
            "title": "Paper C",
            "authors": ["Alice"],
            "selection": "poster",
            "keywords": ["nlp"],
            "abstract": "",
            "link": "https://example.com/c",
            "citation_count": 10,
        },
    ]
    with open(iclr_dir / "papers_enriched.jsonl", "w") as f:
        for p in papers:
            f.write(json.dumps(p) + "\n")

    acl_dir = tmp_path / "acl_2025"
    acl_dir.mkdir()
    papers2 = [
        {
            "title": "Paper D",
            "authors": ["Alice", "Dave"],
            "selection": "main",
            "keywords": ["nlp"],
        },
    ]
    with open(acl_dir / "papers.jsonl", "w") as f:
        for p in papers2:
            f.write(json.dumps(p) + "\n")

    return tmp_path


class TestParseConferenceId:
    def test_iclr(self):
        assert parse_conference_id("iclr_2025") == ("ICLR", 2025)

    def test_neurips(self):
        assert parse_conference_id("neurips_2024") == ("NeurIPS", 2024)

    def test_usenix_security(self):
        assert parse_conference_id("usenix_security_2023") == ("USENIX Security", 2023)

    def test_colm(self):
        assert parse_conference_id("colm_2024") == ("COLM", 2024)


class TestLoadPapers:
    def test_prefers_enriched(self, sample_outputs):
        papers = load_papers(sample_outputs / "iclr_2025")
        assert len(papers) == 3
        assert papers[0]["citation_count"] == 100

    def test_falls_back_to_plain(self, sample_outputs):
        papers = load_papers(sample_outputs / "acl_2025")
        assert len(papers) == 1
        assert "citation_count" not in papers[0]


class TestBuildManifestEntry:
    def test_with_citations(self, sample_outputs):
        papers = load_papers(sample_outputs / "iclr_2025")
        entry = build_manifest_entry("iclr_2025", papers)
        assert entry["id"] == "iclr_2025"
        assert entry["venue"] == "ICLR"
        assert entry["year"] == 2025
        assert entry["paper_count"] == 3
        assert entry["has_citations"] is True
        assert sorted(entry["tracks"]) == ["oral", "poster"]
        assert len(entry["top_papers"]) == 3
        assert entry["top_papers"][0]["citation_count"] == 100

    def test_without_citations(self, sample_outputs):
        papers = load_papers(sample_outputs / "acl_2025")
        entry = build_manifest_entry("acl_2025", papers)
        assert entry["has_citations"] is False
        assert entry["top_papers"] == []


class TestBuildAuthorIndex:
    def test_aggregation(self, sample_outputs):
        all_papers = {
            "iclr_2025": load_papers(sample_outputs / "iclr_2025"),
            "acl_2025": load_papers(sample_outputs / "acl_2025"),
        }
        authors = build_author_index(all_papers)
        alice = next(a for a in authors if a["name"] == "Alice")
        assert alice["paper_count"] == 3
        assert alice["total_citations"] == 110
        assert sorted(alice["conferences"]) == ["acl_2025", "iclr_2025"]

        bob = next(a for a in authors if a["name"] == "Bob")
        assert bob["paper_count"] == 2
        assert bob["total_citations"] == 150


class TestBuildTrends:
    def test_keywords(self, sample_outputs):
        all_papers = {
            "iclr_2025": load_papers(sample_outputs / "iclr_2025"),
            "acl_2025": load_papers(sample_outputs / "acl_2025"),
        }
        trends = build_trends(all_papers)
        assert trends["keywords_by_year"]["2025"]["nlp"] == 3
        assert trends["keywords_by_year"]["2025"]["transformers"] == 1
        assert trends["venue_counts_by_year"]["2025"]["ICLR"] == 3
        assert trends["venue_counts_by_year"]["2025"]["ACL"] == 1


class TestBuildAll:
    def test_produces_all_files(self, sample_outputs, tmp_path):
        out_dir = tmp_path / "web_data"
        build_all(sample_outputs, out_dir)

        assert (out_dir / "manifest.json").exists()
        assert (out_dir / "iclr_2025.json").exists()
        assert (out_dir / "acl_2025.json").exists()
        assert (out_dir / "authors.json").exists()
        assert (out_dir / "trends.json").exists()

        manifest = json.loads((out_dir / "manifest.json").read_text())
        assert len(manifest) == 2

        iclr_data = json.loads((out_dir / "iclr_2025.json").read_text())
        assert len(iclr_data) == 3
