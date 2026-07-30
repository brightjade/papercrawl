"""Write registration entries for sources whose setup is mechanical."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """The registration could not be written safely."""


def _insert_into_dict(path: Path, dict_name: str, conf_id: str, line: str) -> None:
    """Insert `line` just before the closing brace of `dict_name` in `path`.

    Editing the literal in place keeps the surrounding comments and grouping
    intact, which matters because these dicts are organised by venue family and
    a regenerated file would lose that.
    """
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(dict_name)}\s*=\s*\{{", text, re.MULTILINE)
    if not match:
        raise RegistrationError(f"{dict_name} not found in {path}")
    if f'"{conf_id}"' in text:
        raise RegistrationError(f"{conf_id} is already registered in {dict_name}")

    depth = 0
    for i in range(match.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                closing = i
                break
    else:
        raise RegistrationError(f"unbalanced braces in {dict_name} in {path}")

    path.write_text(text[:closing] + f"    {line}\n" + text[closing:], encoding="utf-8")
    logger.info("Registered %s in %s", conf_id, path.name)


def register_dblp(conf_id: str, toc_key: str, path: Path) -> None:
    _insert_into_dict(
        path, "DBLP_CONFERENCES", conf_id, f'"{conf_id}": {{"key": "{toc_key}"}},'
    )


def register_cvf(conf_id: str, url: str, parser: str, path: Path, year: int | None = None) -> None:
    entry = f'"{conf_id}": {{"url": "{url}", "parser": "{parser}"'
    if year is not None:
        entry += f', "year": {year}'
    _insert_into_dict(path, "CVF_CONFERENCES", conf_id, entry + "},")


def register_usenix(conf_id: str, slug: str, path: Path) -> None:
    _insert_into_dict(path, "USENIX_CONFERENCES", conf_id, f'"{conf_id}": "{slug}",')


# Words that appear in OpenReview venue strings and name a track.
_TRACK_WORDS = ("oral", "spotlight", "poster", "findings", "industry")


def openreview_selections(client, venue_id: str) -> dict[str, str]:
    """Read a conference's actual `venue` values and turn them into selections.

    Never generate these from a pattern. `configs/corl_2024.yaml` was written
    to match "CoRL 2024 Oral"/"CoRL 2024 Poster" by analogy with 2023 and 2025,
    but CoRL 2024 tags all 264 papers plain "CoRL 2024". The crawl matched
    nothing, wrote an empty file, and reported success.
    """
    notes = client.get_all_notes(content={"venueid": venue_id})
    if not notes:
        raise RegistrationError(f"{venue_id} returned no papers -- nothing to register")

    values = set()
    for note in notes:
        raw = note.content.get("venue", "")
        values.add(raw.get("value", "") if isinstance(raw, dict) else raw)
    values.discard("")

    if len(values) == 1:
        return {"main": next(iter(values))}

    selections: dict[str, str] = {}
    for value in sorted(values):
        lowered = value.lower().replace(" ", "")
        name = next((w for w in _TRACK_WORDS if w in lowered), None)
        selections[name or value.lower().replace(" ", "_")] = value
    return selections


def render_openreview_config(
    name: str, year: int, venue_id: str, selections: dict[str, str]
) -> str:
    """Render a `configs/<id>.yaml` body."""
    lines = [
        "conference:",
        f'  name: "{name}"',
        f"  year: {year}",
        f'  venue_id: "{venue_id}"',
        "  api_version: 2",
        "  selections:",
    ]
    lines += [f'    {key}: "{value}"' for key, value in selections.items()]
    return "\n".join(lines) + "\n"
