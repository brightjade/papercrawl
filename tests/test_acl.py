from ppr.scrapers.acl import _parse_paper_list
from bs4 import BeautifulSoup


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
