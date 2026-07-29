from ppr.enrich import (
    apply_enrichment,
    carry_over,
    match_status_for,
    normalize_title,
)
from ppr.models import Paper


def _paper(**kw) -> Paper:
    base = dict(title="A Paper", link="L", authors=["X"], selection="oral")
    base.update(kw)
    return Paper(**base)


FULL_ENTRY = {
    "title": "A Paper",
    "citationCount": 42,
    "abstract": "S2 abstract.",
    "influentialCitationCount": 5,
    "referenceCount": 30,
    "tldr": {"model": "tldr@v2", "text": "A summary."},
    "publicationDate": "2025-01-15",
    "fieldsOfStudy": ["Computer Science"],
    "openAccessPdf": {"url": "https://example.com/p.pdf"},
    "externalIds": {"CorpusId": 123, "ArXiv": "2501.00001"},
}


class TestNormalizeTitle:
    def test_lowercases_and_collapses_whitespace(self):
        assert normalize_title("  A   Paper\nTitle ") == "a paper title"


class TestApplyEnrichment:
    def test_populates_all_enrichment_fields(self):
        p = apply_enrichment(_paper(), FULL_ENTRY)
        assert p.citation_count == 42
        assert p.influential_citation_count == 5
        assert p.reference_count == 30
        assert p.tldr == "A summary."
        assert p.publication_date == "2025-01-15"
        assert p.fields_of_study == ["Computer Science"]
        assert p.open_access_pdf == "https://example.com/p.pdf"
        assert p.external_ids == {"CorpusId": 123, "ArXiv": "2501.00001"}

    def test_fills_abstract_when_empty(self):
        assert apply_enrichment(_paper(), FULL_ENTRY).abstract == "S2 abstract."

    def test_preserves_existing_abstract(self):
        p = apply_enrichment(_paper(abstract="OpenReview abstract"), FULL_ENTRY)
        assert p.abstract == "OpenReview abstract"

    def test_never_touches_crawl_fields(self):
        p = _paper(keywords=["k"], forum_id="fid")
        entry = dict(FULL_ENTRY, title="Totally Different", authors=[{"name": "Z"}])
        apply_enrichment(p, entry)
        assert p.title == "A Paper"
        assert p.authors == ["X"]
        assert p.link == "L"
        assert p.selection == "oral"
        assert p.keywords == ["k"]
        assert p.forum_id == "fid"

    def test_none_entry_leaves_paper_unchanged(self):
        p = _paper(citation_count=99, external_ids={"CorpusId": 7})
        apply_enrichment(p, None)
        assert p.citation_count == 99
        assert p.external_ids == {"CorpusId": 7}

    def test_entry_without_citation_count_leaves_paper_unchanged(self):
        p = _paper(citation_count=99)
        apply_enrichment(p, {"title": "A Paper", "citationCount": None})
        assert p.citation_count == 99

    def test_zero_citations_is_written(self):
        p = apply_enrichment(_paper(citation_count=5), dict(FULL_ENTRY, citationCount=0))
        assert p.citation_count == 0

    def test_empty_tldr_does_not_clear_existing(self):
        p = _paper(tldr="Existing summary")
        apply_enrichment(p, dict(FULL_ENTRY, tldr=None))
        assert p.tldr == "Existing summary"

    def test_tldr_is_overwritten_when_api_has_one(self):
        p = _paper(tldr="Old summary")
        apply_enrichment(p, dict(FULL_ENTRY, tldr={"text": "New summary"}))
        assert p.tldr == "New summary"

    def test_null_nested_objects_are_safe(self):
        p = apply_enrichment(
            _paper(),
            dict(FULL_ENTRY, openAccessPdf=None, fieldsOfStudy=None, externalIds=None,
                 publicationDate=None),
        )
        assert p.open_access_pdf == ""
        assert p.fields_of_study == []
        assert p.external_ids == {}
        assert p.publication_date == ""


class TestMatchStatusFor:
    def test_matched_ignores_case_and_spacing(self):
        assert match_status_for("A  Paper", {"title": "a paper"}) == "matched"

    def test_mismatch(self):
        assert match_status_for("A Paper", {"title": "Other"}) == "mismatch"

    def test_not_found(self):
        assert match_status_for("A Paper", None) == "not_found"


class TestCarryOver:
    def test_copies_enrichment_but_not_identity(self):
        raw = _paper(title="A Paper", link="NEW", authors=["New"])
        prior = _paper(
            title="A Paper",
            link="OLD",
            authors=["Old"],
            citation_count=10,
            influential_citation_count=2,
            reference_count=20,
            tldr="Prior summary",
            publication_date="2024-01-01",
            fields_of_study=["CS"],
            open_access_pdf="https://old.pdf",
            external_ids={"CorpusId": 55},
            match_status="matched",
        )
        carry_over(raw, prior)
        assert raw.citation_count == 10
        assert raw.influential_citation_count == 2
        assert raw.reference_count == 20
        assert raw.tldr == "Prior summary"
        assert raw.publication_date == "2024-01-01"
        assert raw.fields_of_study == ["CS"]
        assert raw.open_access_pdf == "https://old.pdf"
        assert raw.external_ids == {"CorpusId": 55}
        assert raw.match_status == "matched"
        assert raw.link == "NEW"
        assert raw.authors == ["New"]

    def test_prior_abstract_fills_only_when_raw_is_empty(self):
        raw = _paper(abstract="")
        carry_over(raw, _paper(abstract="Prior abstract"))
        assert raw.abstract == "Prior abstract"

        raw2 = _paper(abstract="Fresh abstract")
        carry_over(raw2, _paper(abstract="Prior abstract"))
        assert raw2.abstract == "Fresh abstract"
