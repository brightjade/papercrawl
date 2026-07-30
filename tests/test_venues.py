from unittest.mock import MagicMock

import pytest
import yaml

from ppr.cli import _available_conferences, cmd_crawl
from ppr.venues import (
    CADENCES,
    MANUAL_SOURCES,
    REGISTRY_PATH,
    SOURCES,
    Venue,
    load_registry,
)


def _write(tmp_path, data):
    p = tmp_path / "venues.yaml"
    p.write_text(yaml.safe_dump(data))
    return p


VALID = {
    "venues": {
        "icse": {
            "name": "ICSE",
            "source": "dblp",
            "cadence": "annual",
            "announce_month": 12,
            "probe": {"toc": "db/conf/icse/icse{year}.bht"},
        }
    }
}


class TestLoadRegistry:
    def test_loads_a_venue(self, tmp_path):
        reg = load_registry(_write(tmp_path, VALID))
        v = reg["icse"]
        assert isinstance(v, Venue)
        assert v.prefix == "icse"
        assert v.name == "ICSE"
        assert v.source == "dblp"
        assert v.cadence == "annual"
        assert v.announce_month == 12
        assert v.probe == {"toc": "db/conf/icse/icse{year}.bht"}

    def test_rejects_unknown_source(self, tmp_path):
        bad = {"venues": {"x": dict(VALID["venues"]["icse"], source="carrier-pigeon")}}
        with pytest.raises(ValueError, match="carrier-pigeon"):
            load_registry(_write(tmp_path, bad))

    def test_rejects_unknown_cadence(self, tmp_path):
        bad = {"venues": {"x": dict(VALID["venues"]["icse"], cadence="fortnightly")}}
        with pytest.raises(ValueError, match="fortnightly"):
            load_registry(_write(tmp_path, bad))

    def test_rejects_out_of_range_announce_month(self, tmp_path):
        bad = {"venues": {"x": dict(VALID["venues"]["icse"], announce_month=13)}}
        with pytest.raises(ValueError, match="announce_month"):
            load_registry(_write(tmp_path, bad))

    def test_rejects_missing_required_field(self, tmp_path):
        incomplete = dict(VALID["venues"]["icse"])
        del incomplete["source"]
        with pytest.raises(ValueError, match="source"):
            load_registry(_write(tmp_path, {"venues": {"x": incomplete}}))


class TestShippedRegistry:
    def test_shipped_registry_parses(self):
        reg = load_registry(REGISTRY_PATH)
        assert len(reg) == 24
        for prefix, v in reg.items():
            assert v.source in SOURCES
            assert v.cadence in CADENCES
            assert 1 <= v.announce_month <= 12

    def test_biennial_venues_declared(self):
        reg = load_registry(REGISTRY_PATH)
        assert reg["iccv"].cadence == "biennial-odd"
        assert reg["eccv"].cadence == "biennial-even"

    def test_manual_sources_marked(self):
        reg = load_registry(REGISTRY_PATH)
        for prefix in ("acl", "emnlp", "naacl", "eacl", "coling", "aaai"):
            assert reg[prefix].source in MANUAL_SOURCES

    def test_every_tracked_prefix_is_registered(self):
        """A venue absent from the registry is never probed -- a silent blind spot."""
        from pathlib import Path

        from ppr.scrapers import SCRAPERS

        configs = Path(__file__).resolve().parent.parent / "configs"
        ids = {p.stem for p in configs.glob("*.yaml") if p.stem != "venues"}
        ids |= set(SCRAPERS.keys())
        prefixes = {cid.rsplit("_", 1)[0] for cid in ids}
        assert prefixes <= set(load_registry(REGISTRY_PATH)), (
            f"unregistered: {sorted(prefixes - set(load_registry(REGISTRY_PATH)))}"
        )


class TestConfigsDirExcludesRegistry:
    """configs/venues.yaml shares a directory with per-year conference configs.
    Anything deriving conference IDs by globbing configs/*.yaml must exclude it,
    or the registry itself gets treated as a bogus conference."""

    def test_venues_not_in_available_conferences(self):
        assert "venues" not in _available_conferences()

    def test_crawl_venues_reports_unknown_conference(self):
        """Without the exclusion, `ppr crawl venues` takes the OpenReview branch
        (configs/venues.yaml exists, "venues" isn't in SCRAPERS) and dies inside
        CrawlConfig.from_yaml instead of reporting a clean unknown-conference error."""
        args = MagicMock(conferences=["venues"])
        with pytest.raises(FileNotFoundError, match="venues"):
            cmd_crawl(args)
