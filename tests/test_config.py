import pytest
from pathlib import Path

from ppr.config import CrawlConfig


class TestCrawlConfig:
    def test_from_yaml_valid(self, tmp_path):
        config_file = tmp_path / "iclr_2025.yaml"
        config_file.write_text("""
conference:
  name: "ICLR"
  year: 2025
  venue_id: "ICLR.cc/2025/Conference"
  selections:
    oral: "ICLR 2025 Oral"
    poster: "ICLR 2025 Poster"
""")
        config = CrawlConfig.from_yaml(config_file)
        assert config.name == "ICLR"
        assert config.year == 2025
        assert config.venue_id == "ICLR.cc/2025/Conference"
        assert config.selections["oral"] == "ICLR 2025 Oral"
        assert config.conference_id == "iclr_2025"
        assert config.get_save_path() == Path("data/iclr_2025/papers.jsonl")

    def test_from_yaml_missing_file(self):
        with pytest.raises(FileNotFoundError):
            CrawlConfig.from_yaml("/nonexistent/path.yaml")

    def test_from_yaml_missing_conference(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("foo: bar\n")
        with pytest.raises(ValueError, match="conference"):
            CrawlConfig.from_yaml(config_file)

    def test_from_yaml_missing_name(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("""
conference:
  year: 2025
  venue_id: "X"
  selections:
    oral: "X"
""")
        with pytest.raises(ValueError, match="name"):
            CrawlConfig.from_yaml(config_file)

    def test_from_yaml_missing_venue_id(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("""
conference:
  name: "X"
  year: 2025
  selections:
    oral: "X"
""")
        with pytest.raises(ValueError, match="venue_id"):
            CrawlConfig.from_yaml(config_file)

    def test_from_yaml_selections_must_be_dict(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("""
conference:
  name: "X"
  year: 2025
  venue_id: "X"
  selections: ["oral", "poster"]
""")
        with pytest.raises(ValueError, match="dict"):
            CrawlConfig.from_yaml(config_file)

    def test_get_save_path(self):
        config = CrawlConfig(
            name="ICLR", year=2025, venue_id="ICLR.cc/2025/Conference",
            selections={"oral": "X"}, conference_id="iclr_2025",
        )
        assert config.get_save_path() == Path("data/iclr_2025/papers.jsonl")

    def test_uses_safe_load(self, tmp_path):
        config_file = tmp_path / "evil.yaml"
        config_file.write_text("""
conference: !!python/object:builtins.dict
  name: "ICLR"
  year: 2025
  venue_id: "X"
  selections:
    oral: "X"
""")
        with pytest.raises(Exception):
            CrawlConfig.from_yaml(config_file)
