"""Cross-reference scraped paper counts against DBLP proceedings data."""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

DBLP_API_URL = "https://dblp.org/search/publ/api"
HITS_PER_PAGE = 1000

# Conferences scraped directly from DBLP (ppr/scrapers/dblp.py).
# Validating these against DBLP would be circular — skip them.
DBLP_SOURCE_IDS: set[str] = {
    "icse_2023", "icse_2024", "icse_2025",
    "fse_2023", "fse_2024", "fse_2025",
    "ase_2023", "ase_2024", "ase_2025",
    "issta_2023", "issta_2024", "issta_2025",
    "icra_2023", "icra_2024", "icra_2025",
    "iros_2023", "iros_2024", "iros_2025",
    "rss_2023", "rss_2024",
    "ijcai_2023", "ijcai_2024", "ijcai_2025",
}

# Maps conference ID -> list of DBLP toc keys to query.
# Multiple keys handle multi-volume proceedings (e.g., ACL long + short + findings).
# Only includes volumes matching the tracks our scraper covers.
DBLP_VALIDATION_KEYS: dict[str, list[str]] = {
    # --- OpenReview conferences ---
    "iclr_2023": ["db/conf/iclr/iclr2023.bht"],
    "iclr_2024": ["db/conf/iclr/iclr2024.bht"],
    "iclr_2025": ["db/conf/iclr/iclr2025.bht"],
    # iclr_2026: not yet indexed
    "icml_2023": ["db/conf/icml/icml2023.bht"],
    "icml_2024": ["db/conf/icml/icml2024.bht"],
    "icml_2025": ["db/conf/icml/icml2025.bht"],
    "neurips_2023": ["db/conf/nips/neurips2023.bht"],
    "neurips_2024": ["db/conf/nips/neurips2024.bht"],
    # neurips_2025: not yet indexed
    # colm_2024, colm_2025: not in DBLP
    "corl_2023": ["db/conf/corl/corl2023.bht"],
    "corl_2024": ["db/conf/corl/corl2024.bht"],
    # --- ACL conferences (multi-volume) ---
    "emnlp_2023": [
        "db/conf/emnlp/emnlp2023.bht",      # main
        "db/conf/emnlp/emnlp2023f.bht",      # findings
        "db/conf/emnlp/emnlp2023i.bht",      # industry
    ],
    "emnlp_2024": [
        "db/conf/emnlp/emnlp2024.bht",
        "db/conf/emnlp/emnlp2024f.bht",
        "db/conf/emnlp/emnlp2024i.bht",
    ],
    "emnlp_2025": [
        "db/conf/emnlp/emnlp2025.bht",
        "db/conf/emnlp/emnlp2025f.bht",
        "db/conf/emnlp/emnlp2025i.bht",
    ],
    "acl_2023": [
        "db/conf/acl/acl2023-1.bht",         # long
        "db/conf/acl/acl2023-2.bht",         # short
        "db/conf/acl/acl2023f.bht",          # findings
        "db/conf/acl/acl2023i.bht",          # industry
    ],
    "acl_2024": [
        "db/conf/acl/acl2024-1.bht",         # long
        "db/conf/acl/acl2024short.bht",      # short
        "db/conf/acl/acl2024f.bht",          # findings
    ],
    "acl_2025": [
        "db/conf/acl/acl2025-1.bht",         # long
        "db/conf/acl/acl2025-2.bht",         # short
        "db/conf/acl/acl2025f.bht",          # findings
        "db/conf/acl/acl2025-6.bht",         # industry
    ],
    "naacl_2024": [
        "db/conf/naacl/naacl2024.bht",       # long
        "db/conf/naacl/naacl2024-2.bht",     # short
        "db/conf/naacl/naacl2024f.bht",      # findings
        "db/conf/naacl/naacl2024-6.bht",     # industry
    ],
    "naacl_2025": [
        "db/conf/naacl/naacl2025-1.bht",     # long
        "db/conf/naacl/naacl2025-2.bht",     # short
        "db/conf/naacl/naacl2025f.bht",      # findings
        "db/conf/naacl/naacl2025-3.bht",     # industry
    ],
    "eacl_2023": [
        "db/conf/eacl/eacl2023.bht",         # main
        "db/conf/eacl/eacl2023f.bht",        # findings
    ],
    "eacl_2024": [
        "db/conf/eacl/eacl2024-1.bht",       # long
        "db/conf/eacl/eacl2024-2.bht",       # short
        "db/conf/eacl/eacl2024f.bht",        # findings
    ],
    "coling_2024": ["db/conf/coling/coling2024.bht"],
    "coling_2025": [
        "db/conf/coling/coling2025.bht",      # main
        "db/conf/coling/coling2025i.bht",     # industry
        "db/conf/coling/coling2025d.bht",     # demo
    ],
    # --- AAAI ---
    "aaai_2023": ["db/conf/aaai/aaai2023.bht"],
    "aaai_2024": ["db/conf/aaai/aaai2024.bht"],
    "aaai_2025": ["db/conf/aaai/aaai2025.bht"],
    # --- USENIX Security ---
    "usenix_security_2023": ["db/conf/uss/uss2023.bht"],
    "usenix_security_2024": ["db/conf/uss/uss2024.bht"],
    "usenix_security_2025": ["db/conf/uss/uss2025.bht"],
    # --- CVF/ECVA ---
    "cvpr_2023": ["db/conf/cvpr/cvpr2023.bht"],
    "cvpr_2024": ["db/conf/cvpr/cvpr2024.bht"],
    "cvpr_2025": ["db/conf/cvpr/cvpr2025.bht"],
    "iccv_2023": ["db/conf/iccv/iccv2023.bht"],
    # iccv_2025: not yet indexed
    "wacv_2023": ["db/conf/wacv/wacv2023.bht"],
    "wacv_2024": ["db/conf/wacv/wacv2024.bht"],
    "wacv_2025": ["db/conf/wacv/wacv2025.bht"],
    # iccv_2025, wacv_2026: not yet indexed (pre-publication)
    # eccv_2024: 89 volumes on DBLP — fetching counts takes ~90s
    "eccv_2024": [f"db/conf/eccv/eccv2024-{i}.bht" for i in range(1, 90)],
    # rss_2025: not yet indexed
}


def fetch_dblp_count(keys: list[str]) -> int:
    """Count non-Editorship papers across one or more DBLP toc keys.

    Makes one paginated API call per key, sums the paper counts.
    Rate-limited to 1 request per second.
    """
    total = 0
    for i, key in enumerate(keys):
        if i > 0:
            time.sleep(1)
        total += _count_one_key(key)
    return total


def _count_one_key(key: str) -> int:
    """Count non-Editorship papers for a single DBLP toc key.

    Returns 0 if the key is not found or the API returns an error.
    """
    offset = 0
    count = 0

    while True:
        params = {
            "q": f"toc:{key}:",
            "h": HITS_PER_PAGE,
            "f": offset,
            "format": "json",
        }
        logger.debug("DBLP API: key=%s offset=%d", key, offset)
        try:
            resp = requests.get(DBLP_API_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning("DBLP API error for %s: %s", key, e)
            return count
        data = resp.json()

        hits_data = data["result"]["hits"]
        api_total = int(hits_data["@total"])

        if api_total == 0:
            break

        for hit in hits_data.get("hit", []):
            if hit["info"].get("type") != "Editorship":
                count += 1

        offset += HITS_PER_PAGE
        if offset >= api_total:
            break

        time.sleep(1)

    logger.debug("DBLP count for %s: %d papers", key, count)
    return count


@dataclass
class ValidationResult:
    conf_id: str
    status: str      # PASS, FAIL, SKIP, NO_DATA
    scraped: int = 0
    dblp: int = 0
    message: str = ""


def validate_conference(
    conf_id: str,
    tolerance: float = 0.1,
) -> ValidationResult:
    """Validate a conference's scraped paper count against DBLP.

    Args:
        conf_id: Conference identifier (e.g., 'iclr_2025').
        tolerance: Maximum allowed relative difference (default 10%).

    Returns:
        ValidationResult with status and counts.
    """
    if conf_id in DBLP_SOURCE_IDS:
        return ValidationResult(conf_id, "SKIP", message="DBLP-sourced conference")

    if conf_id not in DBLP_VALIDATION_KEYS:
        return ValidationResult(conf_id, "NO_DATA", message="No DBLP mapping")

    output_path = OUTPUTS_DIR / conf_id / "papers.jsonl"
    if not output_path.exists():
        return ValidationResult(conf_id, "NO_DATA", message="No output file")

    with open(output_path, encoding="utf-8") as f:
        scraped = sum(1 for line in f if line.strip())

    dblp_count = fetch_dblp_count(DBLP_VALIDATION_KEYS[conf_id])

    if dblp_count == 0:
        return ValidationResult(
            conf_id, "NO_DATA", scraped=scraped, dblp=0,
            message="DBLP returned 0 (not yet indexed?)",
        )

    diff = abs(scraped - dblp_count) / dblp_count
    if diff <= tolerance:
        return ValidationResult(conf_id, "PASS", scraped=scraped, dblp=dblp_count)
    else:
        return ValidationResult(
            conf_id, "FAIL", scraped=scraped, dblp=dblp_count,
            message=f"Difference: {diff:.1%}",
        )
