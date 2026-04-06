from unittest.mock import MagicMock, patch

from ppr.scrapers.rss import RSS_CONFERENCES, SCRAPERS, _parse_rss, _scrape_rss

# Minimal HTML fixture matching the real RSS page structure:
# <table id="myTable"> with a header row (<th>) and data rows (<td>).
# Each data row has: [number, session, title (<a href>), authors (comma-separated)].
# The author cell contains a hidden <div class="content"> that duplicates the text.
FIXTURE_HTML = """
<!DOCTYPE html>
<html>
<body>
<table id="myTable">
  <tr class="toprowHeader">
    <th>ID</th>
    <th>Session</th>
    <th>Title</th>
    <th>Authors</th>
  </tr>
  <tr session="1. Perception and Navigation">
    <td height="100px" width="5%">1</td>
    <td height="100px" width="15%"><span style="font-size: smaller;">Perception and Navigation</span></td>
    <td height="100px" width="40%">
      <a href="/program/papers/1/">
        <b>Learned Perceptive Forward Dynamics Model for Safe and Platform-aware Robotic Navigation</b>
      </a>
    </td>
    <td height="100px" width="40%">
      Pascal Roth, Jonas Frey, Cesar Cadena, Marco Hutter
      <div class="content" style="display:none; padding-top:20px;">
        Pascal Roth, Jonas Frey, Cesar Cadena, Marco Hutter
      </div>
    </td>
  </tr>
  <tr session="1. Perception and Navigation">
    <td height="100px" width="5%">2</td>
    <td height="100px" width="15%"><span style="font-size: smaller;">Perception and Navigation</span></td>
    <td height="100px" width="40%">
      <a href="/program/papers/2/">
        <b>Demonstrating ViSafe: Vision-enabled Safety for High-speed Detect and Avoid</b>
      </a>
    </td>
    <td height="100px" width="40%">
      Parv Kapoor, Ian Higgins, Nikhil Varma Keetha, Jay Patrikar, Brady Moon
      <div class="content" style="display:none; padding-top:20px;">
        Parv Kapoor, Ian Higgins, Nikhil Varma Keetha, Jay Patrikar, Brady Moon
      </div>
    </td>
  </tr>
  <tr session="2. Manipulation">
    <td height="100px" width="5%">3</td>
    <td height="100px" width="15%"><span style="font-size: smaller;">Manipulation</span></td>
    <td height="100px" width="40%">
      <a href="/program/papers/3/">
        <b>Dexterous Manipulation with Policy Adaptation</b>
      </a>
    </td>
    <td height="100px" width="40%">
      Alice Smith, Bob Jones
      <div class="content" style="display:none; padding-top:20px;">
        Alice Smith, Bob Jones
      </div>
    </td>
  </tr>
</table>
</body>
</html>
"""

NO_TABLE_HTML = "<html><body><p>No table here.</p></body></html>"


class TestParseRss:
    def test_paper_count(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert len(papers) == 3

    def test_first_paper_title(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert papers[0].title == (
            "Learned Perceptive Forward Dynamics Model for Safe and Platform-aware Robotic Navigation"
        )

    def test_second_paper_title(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert papers[1].title == (
            "Demonstrating ViSafe: Vision-enabled Safety for High-speed Detect and Avoid"
        )

    def test_authors_comma_separated(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert papers[0].authors == ["Pascal Roth", "Jonas Frey", "Cesar Cadena", "Marco Hutter"]

    def test_authors_multi_author_row(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert papers[1].authors == [
            "Parv Kapoor", "Ian Higgins", "Nikhil Varma Keetha", "Jay Patrikar", "Brady Moon"
        ]

    def test_authors_two_authors(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert papers[2].authors == ["Alice Smith", "Bob Jones"]

    def test_link_is_absolute_url(self):
        papers = _parse_rss(FIXTURE_HTML)
        assert papers[0].link == "https://roboticsconference.org/program/papers/1/"

    def test_link_uses_base_url(self):
        papers = _parse_rss(FIXTURE_HTML)
        for paper in papers:
            assert paper.link.startswith("https://roboticsconference.org")

    def test_selection_is_main(self):
        papers = _parse_rss(FIXTURE_HTML)
        for paper in papers:
            assert paper.selection == "main"

    def test_hidden_div_not_duplicated_in_authors(self):
        # Authors should not contain duplicated names from the hidden <div class="content">
        papers = _parse_rss(FIXTURE_HTML)
        # First paper has 4 unique authors; if the hidden div were included, we'd get 8
        assert len(papers[0].authors) == 4

    def test_no_table_returns_empty(self):
        papers = _parse_rss(NO_TABLE_HTML)
        assert papers == []

    def test_header_row_skipped(self):
        # The <tr class="toprowHeader"> with <th> cells must not produce a paper
        papers = _parse_rss(FIXTURE_HTML)
        titles = [p.title for p in papers]
        assert "ID" not in titles
        assert "Title" not in titles


class TestScrapeRss:
    @patch("ppr.scrapers.rss.requests.get")
    def test_fetches_correct_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = FIXTURE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _scrape_rss("rss_2025")

        mock_get.assert_called_once_with(
            "https://roboticsconference.org/program/papers/", timeout=60
        )

    @patch("ppr.scrapers.rss.requests.get")
    def test_returns_parsed_papers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = FIXTURE_HTML
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        papers = _scrape_rss("rss_2025")
        assert len(papers) == 3

    @patch("ppr.scrapers.rss.requests.get")
    def test_raises_on_http_error(self, mock_get):
        import requests as req

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("404")
        mock_get.return_value = mock_resp

        try:
            _scrape_rss("rss_2025")
            assert False, "Expected HTTPError"
        except req.HTTPError:
            pass


class TestScrapersDict:
    def test_expected_conference_ids(self):
        assert "rss_2025" in SCRAPERS

    def test_all_conferences_registered(self):
        for conf_id in RSS_CONFERENCES:
            assert conf_id in SCRAPERS, f"{conf_id} not in SCRAPERS"

    def test_scrapers_are_callable(self):
        for conf_id, scraper in SCRAPERS.items():
            assert callable(scraper), f"{conf_id} scraper is not callable"
