from ppr.discover import known_conference_ids, missing_years


class TestMissingYears:
    def test_proposes_the_next_year(self):
        assert missing_years("icse", "annual", {"icse_2023", "icse_2024", "icse_2025"}, 2026) == [2026, 2027]

    def test_fills_a_gap_in_the_middle(self):
        assert missing_years("acl", "annual", {"acl_2023", "acl_2025"}, 2025) == [2024, 2026]

    def test_up_to_date_venue_still_looks_ahead(self):
        assert missing_years("wacv", "annual", {"wacv_2025", "wacv_2026"}, 2026) == [2027]

    def test_biennial_odd_never_proposes_an_even_year(self):
        out = missing_years("iccv", "biennial-odd", {"iccv_2023", "iccv_2025"}, 2026)
        assert out == [2027]
        assert all(y % 2 == 1 for y in out)

    def test_biennial_even_never_proposes_an_odd_year(self):
        out = missing_years("eccv", "biennial-even", {"eccv_2024"}, 2026)
        assert out == [2026]
        assert all(y % 2 == 0 for y in out)

    def test_ignores_other_venues(self):
        assert missing_years("icse", "annual", {"acl_2023", "acl_2024"}, 2024) == []

    def test_no_known_years_yields_nothing(self):
        assert missing_years("icse", "annual", set(), 2026) == []

    def test_result_is_sorted_ascending(self):
        out = missing_years("acl", "annual", {"acl_2020", "acl_2023"}, 2024)
        assert out == sorted(out)


class TestKnownConferenceIds:
    def test_derives_from_committed_sources_not_data(self):
        """CI has no data/ directory, so this must not depend on one."""
        ids = known_conference_ids()
        assert "iclr_2026" in ids       # from configs/
        assert "usenix_security_2025" in ids  # from SCRAPERS
        assert "venues" not in ids      # the registry file is not a conference

    def test_covers_every_committed_source(self):
        """A lower bound, not an exact count -- later tasks register more."""
        from pathlib import Path

        from ppr.scrapers import SCRAPERS

        configs = Path(__file__).resolve().parent.parent / "configs"
        expected = {p.stem for p in configs.glob("*.yaml") if p.stem != "venues"}
        expected |= set(SCRAPERS.keys())
        assert known_conference_ids() == expected
        assert len(expected) >= 69


from unittest.mock import MagicMock, patch

import pytest
import requests

from ppr.discover import (
    DBLP_MIN_INTERVAL,
    MIN_LIVE_PAPERS,
    ProbeResult,
    probe,
)
from ppr.venues import Venue


def _venue(**kw) -> Venue:
    base = dict(
        prefix="cvpr", name="CVPR", source="cvf", cadence="annual",
        announce_month=2, probe={"url": "https://x.test/CVPR{year}"},
    )
    base.update(kw)
    return Venue(**base)


def _response(status=200, text=""):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.content = text.encode()
    return r


CVF_PAPER = '<dt class="ptitle"><a href="/p.html">A Paper</a></dt>'
USENIX_PAPER = '<article class="node-paper"><h2>A Paper</h2></article>'


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr("ppr.discover.time.sleep", lambda *_: None)


class TestCvfProbe:
    def test_populated_page_is_live(self):
        with patch("ppr.discover.requests.get", return_value=_response(200, CVF_PAPER * 60)):
            r = probe(_venue(), 2025)
        assert r.status == "live"
        assert r.count == 60
        assert r.conf_id == "cvpr_2025"

    def test_stub_page_is_empty_not_live(self):
        """CVPR 2026 really returns 200 with a 3KB stub and zero papers."""
        with patch("ppr.discover.requests.get", return_value=_response(200, "<html>CVPR 2026 open access</html>")):
            r = probe(_venue(), 2026)
        assert r.status == "empty"
        assert r.count == 0

    def test_just_below_the_floor_is_empty(self):
        html = CVF_PAPER * (MIN_LIVE_PAPERS - 1)
        with patch("ppr.discover.requests.get", return_value=_response(200, html)):
            assert probe(_venue(), 2026).status == "empty"

    def test_exactly_at_the_floor_is_live(self):
        html = CVF_PAPER * MIN_LIVE_PAPERS
        with patch("ppr.discover.requests.get", return_value=_response(200, html)):
            assert probe(_venue(), 2026).status == "live"

    def test_404_with_a_large_body_is_not_yet(self):
        """WACV 2027 really returns 404 with a 29KB custom error page."""
        with patch("ppr.discover.requests.get", return_value=_response(404, "x" * 29000)):
            r = probe(_venue(), 2027)
        assert r.status == "not-yet"
        assert r.count == 0

    def test_network_failure_is_unreachable(self):
        with patch("ppr.discover.requests.get", side_effect=requests.RequestException("boom")):
            assert probe(_venue(), 2026).status == "unreachable"

    def test_ecva_marker_absent_is_not_yet(self):
        v = _venue(prefix="eccv", name="ECCV", cadence="biennial-even",
                   probe={"url": "https://ecva.test/papers.php", "marker": "ECCV {year}"})
        with patch("ppr.discover.requests.get", return_value=_response(200, "ECCV 2024 papers")):
            assert probe(v, 2026).status == "not-yet"


class TestUsenixProbe:
    def test_populated_page_is_live(self):
        v = _venue(prefix="usenix_security", name="USENIX Security", source="usenix",
                   probe={"slug": "usenixsecurity{yy}"})
        with patch("ppr.discover.requests.get", return_value=_response(200, USENIX_PAPER * 381)) as g:
            r = probe(v, 2026)
        assert (r.status, r.count) == ("live", 381)
        assert "usenixsecurity26" in g.call_args[0][0]


class TestDblpProbe:
    def _venue(self):
        return _venue(prefix="icse", name="ICSE", source="dblp",
                      probe={"toc": "db/conf/icse/icse{year}.bht"})

    def test_falls_through_toc_candidates_until_one_has_hits(self):
        """FSE moved to shared PACMSE volumes; the old conf key is dead for 2024+."""
        v = _venue(prefix="fse", name="FSE", source="dblp", probe={"toc": [
            "db/conf/sigsoft/fse{year}.bht",
            "db/journals/pacmse/pacmse{pacmse_vol}.bht",
        ]})
        miss = _response(200); miss.json = lambda: {"result": {"hits": {"@total": "0"}}}
        hit = _response(200); hit.json = lambda: {"result": {"hits": {"@total": "132"}}}
        with patch("ppr.discover.requests.get", side_effect=[miss, hit]) as g:
            out = probe(v, 2026)
        assert (out.status, out.count) == ("live", 132)
        # pacmse1 is 2024, so 2026 must resolve to volume 3 -- not the year.
        assert "pacmse3" in g.call_args_list[1].kwargs["params"]["q"]

    def test_stops_at_the_first_candidate_with_hits(self):
        v = _venue(prefix="fse", name="FSE", source="dblp", probe={"toc": [
            "db/conf/sigsoft/fse{year}.bht",
            "db/journals/pacmse/pacmse{pacmse_vol}.bht",
        ]})
        hit = _response(200); hit.json = lambda: {"result": {"hits": {"@total": "206"}}}
        with patch("ppr.discover.requests.get", return_value=hit) as g:
            out = probe(v, 2023)
        assert out.count == 206
        assert g.call_count == 1

    def test_all_candidates_empty_is_not_yet(self):
        v = _venue(prefix="fse", name="FSE", source="dblp", probe={"toc": [
            "db/conf/sigsoft/fse{year}.bht",
            "db/journals/pacmse/pacmse{pacmse_vol}.bht",
        ]})
        miss = _response(200); miss.json = lambda: {"result": {"hits": {"@total": "0"}}}
        with patch("ppr.discover.requests.get", return_value=miss):
            assert probe(v, 2027).status == "not-yet"

    def test_a_plain_string_toc_still_works(self):
        ok = _response(200); ok.json = lambda: {"result": {"hits": {"@total": "245"}}}
        with patch("ppr.discover.requests.get", return_value=ok) as g:
            assert probe(self._venue(), 2026).count == 245
        assert g.call_count == 1

    def test_hits_means_live(self):
        payload = {"result": {"hits": {"@total": "245"}}}
        r = _response(200); r.json = lambda: payload
        with patch("ppr.discover.requests.get", return_value=r):
            out = probe(self._venue(), 2026)
        assert (out.status, out.count) == ("live", 245)

    def test_zero_hits_is_not_yet(self):
        payload = {"result": {"hits": {"@total": "0"}}}
        r = _response(200); r.json = lambda: payload
        with patch("ppr.discover.requests.get", return_value=r):
            assert probe(self._venue(), 2026).status == "not-yet"

    def test_429_is_retried_then_succeeds(self, no_sleep):
        ok = _response(200); ok.json = lambda: {"result": {"hits": {"@total": "7"}}}
        with patch("ppr.discover.requests.get", side_effect=[_response(429), ok]):
            out = probe(self._venue(), 2026)
        assert (out.status, out.count) == ("live", 7)

    def test_persistent_429_is_unreachable_not_absent(self, no_sleep):
        """A throttled sweep must never read as 'nothing new'."""
        with patch("ppr.discover.requests.get", return_value=_response(429)):
            out = probe(self._venue(), 2026)
        assert out.status == "unreachable"
        assert "429" in out.note

    def test_paces_at_one_second(self, monkeypatch):
        slept = []
        monkeypatch.setattr("ppr.discover.time.sleep", lambda s: slept.append(s))
        ok = _response(200); ok.json = lambda: {"result": {"hits": {"@total": "1"}}}
        with patch("ppr.discover.requests.get", return_value=ok):
            probe(self._venue(), 2026)
            probe(self._venue(), 2027)
        assert slept and max(slept) <= DBLP_MIN_INTERVAL


class TestOpenreviewProbe:
    def _venue(self):
        return _venue(prefix="iclr", name="ICLR", source="openreview",
                      probe={"venue_id": "ICLR.cc/{year}/Conference"})

    def test_notes_means_live(self):
        client = MagicMock()
        client.get_all_notes.return_value = [MagicMock()] * 5340
        out = probe(self._venue(), 2026, openreview_client=client)
        assert (out.status, out.count) == ("live", 5340)
        client.get_all_notes.assert_called_once_with(
            content={"venueid": "ICLR.cc/2026/Conference"}
        )

    def test_no_notes_is_not_yet(self):
        client = MagicMock()
        client.get_all_notes.return_value = []
        assert probe(self._venue(), 2027, openreview_client=client).status == "not-yet"

    def test_missing_client_is_unreachable_with_a_credentials_note(self):
        """No secret in CI must degrade coverage, not read as 'nothing new'."""
        out = probe(self._venue(), 2026, openreview_client=None)
        assert out.status == "unreachable"
        assert "credential" in out.note.lower()

    def test_api_error_is_unreachable(self):
        client = MagicMock()
        client.get_all_notes.side_effect = Exception("ChallengeRequiredError")
        assert probe(self._venue(), 2026, openreview_client=client).status == "unreachable"


class TestManualSources:
    @pytest.mark.parametrize("source", ["acl", "aaai", "bespoke"])
    def test_always_needs_manual_never_live(self, source):
        v = _venue(prefix="acl", name="ACL", source=source,
                   probe={"url": "https://{year}.aclweb.org/"})
        with patch("ppr.discover.requests.get", return_value=_response(200, CVF_PAPER * 500)):
            out = probe(v, 2026)
        assert out.status == "needs-manual"
        assert out.url == "https://2026.aclweb.org/"

    def test_makes_no_request_at_all(self):
        v = _venue(prefix="aaai", name="AAAI", source="aaai", probe={"url": "https://x.test/"})
        with patch("ppr.discover.requests.get") as g:
            probe(v, 2027)
        assert g.call_count == 0
