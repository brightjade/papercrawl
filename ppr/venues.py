"""The registry of conference venues discovery knows how to look for."""

from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "configs" / "venues.yaml"

SOURCES = {"openreview", "dblp", "cvf", "usenix", "acl", "aaai", "bespoke"}
CADENCES = {"annual", "biennial-odd", "biennial-even"}

# Sources whose registration needs a human-written scraper. Discovery reports
# these as `needs-manual` rather than claiming a list is ready to register.
MANUAL_SOURCES = {"acl", "aaai", "bespoke"}

_REQUIRED = ("name", "source", "cadence", "announce_month", "probe")


@dataclass(frozen=True)
class Venue:
    prefix: str
    name: str
    source: str
    cadence: str
    probe: dict
    announce_month: int


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Venue]:
    """Parse the venue registry, rejecting anything discovery could not act on.

    Validation is strict on purpose: a venue with an unrecognized source would
    otherwise be skipped silently, and a silently unprobed venue looks exactly
    like a venue with nothing new.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    venues = raw.get("venues") or {}
    registry: dict[str, Venue] = {}

    for prefix, entry in venues.items():
        for field_name in _REQUIRED:
            if field_name not in entry:
                raise ValueError(f"venue {prefix!r}: missing required field {field_name!r}")
        if entry["source"] not in SOURCES:
            raise ValueError(
                f"venue {prefix!r}: unknown source {entry['source']!r} "
                f"(expected one of {sorted(SOURCES)})"
            )
        if entry["cadence"] not in CADENCES:
            raise ValueError(
                f"venue {prefix!r}: unknown cadence {entry['cadence']!r} "
                f"(expected one of {sorted(CADENCES)})"
            )
        month = entry["announce_month"]
        if not isinstance(month, int) or not 1 <= month <= 12:
            raise ValueError(f"venue {prefix!r}: announce_month must be 1-12, got {month!r}")

        registry[prefix] = Venue(
            prefix=prefix,
            name=entry["name"],
            source=entry["source"],
            cadence=entry["cadence"],
            probe=entry["probe"],
            announce_month=month,
        )

    return registry
