"""Cross-reference scraped paper counts against DBLP proceedings data."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

DBLP_API_URL = "https://dblp.org/search/publ/api"
HITS_PER_PAGE = 1000

# Conference IDs sourced from ppr/scrapers/dblp.py — skip these in validation
# (cross-checking DBLP against itself is circular).
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
    # wacv_2026: not yet indexed
    "eccv_2024": [f"db/conf/eccv/eccv2024-{i}.bht" for i in range(1, 90)],
    # --- RSS (scraped from roboticsconference.org, not DBLP) ---
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
    """Count non-Editorship papers for a single DBLP toc key."""
    offset = 0
    count = 0

    while True:
        params = {
            "q": f"toc:{key}:",
            "h": HITS_PER_PAGE,
            "f": offset,
            "format": "json",
        }
        resp = requests.get(DBLP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
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

    return count
