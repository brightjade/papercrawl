from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class CrawlConfig:
    name: str
    year: int
    venue_id: str  # e.g., "ICLR.cc/2025/Conference"
    selections: dict[str, str]  # selection_name -> venue string (e.g., "ICLR 2025 Oral")
    conference_id: str  # e.g., "iclr_2025" (derived from filename)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CrawlConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f)

        conference = raw.get("conference")
        if not conference:
            raise ValueError("Config must have a 'conference' section")

        name = conference.get("name")
        year = conference.get("year")
        venue_id = conference.get("venue_id")
        selections = conference.get("selections")

        if not name:
            raise ValueError("Config 'conference.name' is required")
        if not year:
            raise ValueError("Config 'conference.year' is required")
        if not venue_id:
            raise ValueError("Config 'conference.venue_id' is required")
        if not selections or not isinstance(selections, dict):
            raise ValueError(
                "Config 'conference.selections' must be a dict mapping "
                "selection names to venue strings"
            )

        conference_id = path.stem  # e.g., "iclr_2025"

        return cls(
            name=name,
            year=year,
            venue_id=venue_id,
            selections=selections,
            conference_id=conference_id,
        )

    def get_save_path(self) -> Path:
        return Path("outputs") / self.conference_id / "papers.jsonl"
