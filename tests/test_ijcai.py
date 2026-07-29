from unittest.mock import MagicMock, patch

from ppr.scrapers.ijcai import IJCAI_CONFERENCES, SCRAPERS, _parse_ijcai, _scrape_ijcai

# Minimal HTML fixture matching the real IJCAI 2026 accepted-papers page.
# Each paper is an <li class="ij-paper"> with:
#   <div class="ij-pid">#NN</div>
#   <h3 class="ij-ptitle"> title
#   <div class="ij-authors"> with <span class="ij-author"> names (ij-sep separators between)
#   <details class="ij-abs"><div class="ij-abstract"> abstract
#   <div class="ij-keywords"> with <span class="ij-kw" title="Area → Topic">
# Some papers carry an author-supplied <div class="ij-oslink"><a href> code link,
# which is NOT the paper itself and must be ignored.
FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<body>
<ol class="ij-list">
  <li class="ij-paper" data-search="frequency-aware ...">
    <div class="ij-pid">#29</div>
    <h3 class="ij-ptitle">Frequency-Aware Augmentation for Time Series Contrastive Learning</h3>
    <div class="ij-authors"><span class="ij-author">Yusen Liu</span><span class="ij-sep">, </span><span class="ij-author">Hua Lu</span></div>
    <details class="ij-abs">
      <summary aria-label="Toggle abstract"></summary>
      <div class="ij-abstract">Contrastive learning for time series representations.</div>
    </details>
    <div class="ij-keywords"><span class="ij-kw" title="Data Mining → Mining spatial and/or temporal data"><span class="ij-kw-area">Data Mining</span>Mining spatial and/or temporal data</span><span class="ij-kw" title="Machine Learning → Self-supervised Learning"><span class="ij-kw-area">Machine Learning</span>Self-supervised Learning</span></div>
  </li>
  <li class="ij-paper" data-search="beyond made with ai ...">
    <div class="ij-pid">#HC13</div>
    <h3 class="ij-ptitle">Beyond Made with AI</h3>
    <div class="ij-authors"><span class="ij-author">Qing Zhang</span></div>
    <details class="ij-abs">
      <summary aria-label="Toggle abstract"></summary>
      <div class="ij-abstract">Visualizing provenance density.</div>
    </details>
    <div class="ij-oslink"><a href="https://github.com/x/y" target="_blank" rel="noopener">Code</a></div>
  </li>
  <li class="ij-paper" data-search="no abstract ...">
    <div class="ij-pid">#100</div>
    <h3 class="ij-ptitle">Paper Without Abstract Or Keywords</h3>
    <div class="ij-authors"><span class="ij-author">Alice Smith</span><span class="ij-sep">, </span><span class="ij-author">Bob Jones</span></div>
  </li>
</ol>
</body>
</html>
"""

NO_PAPERS_HTML = "<html><body><p>No papers here.</p></body></html>"


class TestParseIjcai:
    def test_paper_count(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert len(papers) == 3

    def test_first_paper_title(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[0].title == (
            "Frequency-Aware Augmentation for Time Series Contrastive Learning"
        )

    def test_authors_exclude_separators(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[0].authors == ["Yusen Liu", "Hua Lu"]

    def test_single_author(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[1].authors == ["Qing Zhang"]

    def test_abstract_captured(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[0].abstract == "Contrastive learning for time series representations."

    def test_keywords_use_title_attribute(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[0].keywords == [
            "Data Mining → Mining spatial and/or temporal data",
            "Machine Learning → Self-supervised Learning",
        ]

    def test_selection_is_main(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        for paper in papers:
            assert paper.selection == "main"

    def test_link_is_empty(self):
        # No canonical paper URL exists yet; the ij-oslink code repo must be ignored.
        papers = _parse_ijcai(FIXTURE_HTML)
        for paper in papers:
            assert paper.link == ""

    def test_missing_abstract_is_empty(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[2].abstract == ""

    def test_missing_keywords_is_empty(self):
        papers = _parse_ijcai(FIXTURE_HTML)
        assert papers[1].keywords == []
        assert papers[2].keywords == []

    def test_no_papers_returns_empty(self):
        papers = _parse_ijcai(NO_PAPERS_HTML)
        assert papers == []


class TestScrapeIjcai:
    @patch("ppr.scrapers.ijcai.requests.get")
    def test_fetches_correct_url_with_browser_ua(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = FIXTURE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _scrape_ijcai("ijcai_2026")

        args, kwargs = mock_get.call_args
        assert args[0] == "https://2026.ijcai.org/accepted-papers/"
        assert "User-Agent" in kwargs["headers"]

    @patch("ppr.scrapers.ijcai.requests.get")
    def test_returns_parsed_papers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = FIXTURE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        papers = _scrape_ijcai("ijcai_2026")
        assert len(papers) == 3

    @patch("ppr.scrapers.ijcai.requests.get")
    def test_raises_on_http_error(self, mock_get):
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("404")
        mock_get.return_value = mock_resp

        try:
            _scrape_ijcai("ijcai_2026")
            assert False, "Expected HTTPError"
        except req.HTTPError:
            pass


class TestScrapersDict:
    def test_expected_conference_ids(self):
        assert "ijcai_2026" in SCRAPERS

    def test_all_conferences_registered(self):
        for conf_id in IJCAI_CONFERENCES:
            assert conf_id in SCRAPERS, f"{conf_id} not in SCRAPERS"

    def test_scrapers_are_callable(self):
        for conf_id, scraper in SCRAPERS.items():
            assert callable(scraper), f"{conf_id} scraper is not callable"
