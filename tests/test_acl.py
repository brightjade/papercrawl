from ppr.scrapers.acl import _parse_anthology, _parse_paper_list
from bs4 import BeautifulSoup


ANTHOLOGY_HTML = """<html><body>
<div class="d-sm-flex align-items-stretch mb-3">
<span class="d-block">
<strong><a href="/2024.eacl-long.0/" class="align-middle">Proceedings of the 18th Conference</a></strong><br/>
<a href="/people/a/alice-editor/">Alice Editor</a>
</span></div>
<div class="d-sm-flex align-items-stretch mb-3">
<span class="d-block">
<strong><a href="/2024.eacl-long.1/" class="align-middle">Efficient Fine-tuning of Language Models</a></strong><br/>
<a href="/people/a/alice-smith/">Alice Smith</a> |
<a href="/people/b/bob-jones/">Bob Jones</a>
</span></div>
<div class="d-sm-flex align-items-stretch mb-3">
<span class="d-block">
<strong><a href="/2024.eacl-long.2/" class="align-middle">Multilingual Evaluation Benchmarks</a></strong><br/>
<a href="/people/c/carol-lee/">Carol Lee</a>
</span></div>
</body></html>"""


class TestParseAnthology:
    def test_extracts_papers(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert len(papers) == 2

    def test_paper_title(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].title == "Efficient Fine-tuning of Language Models"

    def test_paper_authors(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].authors == ["Alice Smith", "Bob Jones"]

    def test_paper_link(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].link == "https://aclanthology.org/2024.eacl-long.1/"

    def test_selection(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        assert papers[0].selection == "main"

    def test_skips_proceedings_header(self):
        papers = _parse_anthology(ANTHOLOGY_HTML, "main")
        titles = [p.title for p in papers]
        assert "Proceedings of the 18th Conference" not in titles


class TestParseAuthorDelimiter:
    def test_comma_separated(self):
        html = '<ul><li><strong>Title</strong><em>Alice, Bob, Carol</em></li></ul>'
        soup = BeautifulSoup(html, "html.parser")
        papers = _parse_paper_list(soup, "main")
        assert papers[0].authors == ["Alice", "Bob", "Carol"]

    def test_and_separator(self):
        html = '<ul><li><strong>Title</strong><em>Alice, Bob and Carol</em></li></ul>'
        soup = BeautifulSoup(html, "html.parser")
        papers = _parse_paper_list(soup, "main")
        assert papers[0].authors == ["Alice", "Bob", "Carol"]

    def test_comma_and_mixed(self):
        html = '<ul><li><strong>Title</strong><em>Alice Smith, Bob Jones and Carol Lee</em></li></ul>'
        soup = BeautifulSoup(html, "html.parser")
        papers = _parse_paper_list(soup, "main")
        assert papers[0].authors == ["Alice Smith", "Bob Jones", "Carol Lee"]
