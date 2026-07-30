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
