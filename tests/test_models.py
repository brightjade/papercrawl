import json

from models import Paper


class TestPaper:
    def test_to_dict_full(self):
        paper = Paper(
            title="Test Paper",
            link="https://openreview.net/pdf?id=abc123",
            authors=["Alice", "Bob"],
            keywords=["ML", "NLP"],
            abstract="A test abstract.",
            forum_id="abc123",
        )
        d = paper.to_dict()
        assert d["title"] == "Test Paper"
        assert d["authors"] == ["Alice", "Bob"]
        assert d["keywords"] == ["ML", "NLP"]
        assert d["abstract"] == "A test abstract."
        assert d["forum_id"] == "abc123"
        assert "citation_count" not in d  # None is excluded

    def test_to_dict_minimal(self):
        paper = Paper(title="Min", link="http://x", authors=["A"])
        d = paper.to_dict()
        assert d["title"] == "Min"
        assert d["authors"] == ["A"]
        assert "abstract" not in d  # empty string excluded
        assert "forum_id" not in d
        assert "citation_count" not in d

    def test_to_dict_includes_citation_when_set(self):
        paper = Paper(
            title="T", link="L", authors=[], citation_count=42
        )
        d = paper.to_dict()
        assert d["citation_count"] == 42

    def test_to_dict_includes_zero_citation(self):
        paper = Paper(title="T", link="L", authors=[], citation_count=0)
        d = paper.to_dict()
        assert d["citation_count"] == 0

    def test_to_json(self):
        paper = Paper(title="Test", link="http://x", authors=["A"])
        j = paper.to_json()
        parsed = json.loads(j)
        assert parsed["title"] == "Test"

    def test_from_dict(self):
        data = {
            "title": "Test",
            "link": "http://x",
            "authors": ["A", "B"],
            "keywords": ["k1"],
            "abstract": "abs",
            "citation_count": 10,
            "forum_id": "xyz",
        }
        paper = Paper.from_dict(data)
        assert paper.title == "Test"
        assert paper.authors == ["A", "B"]
        assert paper.citation_count == 10

    def test_from_dict_minimal(self):
        data = {"title": "T", "link": "L"}
        paper = Paper.from_dict(data)
        assert paper.title == "T"
        assert paper.authors == []
        assert paper.keywords == []
        assert paper.abstract == ""
        assert paper.citation_count is None

    def test_keywords_as_list(self):
        paper = Paper(
            title="T", link="L", authors=[], keywords=["deep learning", "NLP"]
        )
        assert isinstance(paper.keywords, list)
        assert len(paper.keywords) == 2
