"""Single point of contact with DBLP's search API.

Two subsystems query this endpoint: the discovery sweep (`ppr/discover.py`) and
count validation (`ppr/validate.py`). They run from the same machine against
one host that throttles on total request volume, so pacing only one of them
honors is not pacing -- and a retry policy only one of them has means the other
turns ordinary throttling into a wrong answer. Both live here instead.

Owns pacing, retries, and the refusal to hand back anything but a real answer:
`query` returns a parsed payload or raises. There is deliberately no "return 0
on failure" path, because a throttled query silently read as a count is how
`ppr validate` came to report count mismatches that were not real.
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

API_URL = "https://dblp.org/search/publ/api"

# DBLP throttles hard: a sweep at 0.4s intervals drew a 429 on the fourth
# request and refused connections thereafter. 1.0s was not enough either --
# two real sweeps on 2026-07-30 still lost 7-8 venue-years per run (the lost
# set *shifted* between runs) to a mix of 429, 500, and 503 that cleared up
# within seconds of a manual retry -- transient throttling, not an outage.
# Bumping to 3.0s made it worse (every DBLP venue came back a hard
# ConnectionError), which is the tell that this isn't a per-request interval
# problem alone -- it's total request volume in a short window. dblp.org's own
# robots.txt (checked 2026-07-30) specifies `Crawl-delay: 4`, which is the
# number actually used here: a server-stated figure beats another guess.
MIN_INTERVAL = 4.0
MAX_RETRIES = 5
# DBLP's overload signal isn't just 429 -- under sustained load it also
# returns bare 500s and 503s that clear up on their own within seconds.
# Treating those as terminal failures turns ordinary throttling into
# permanent-looking ones.
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}

# When the last request went out, on the monotonic clock. Module state because
# the interval is a property of the host, not of any one caller.
_last_request = 0.0


class DblpUnavailable(Exception):
    """DBLP never answered a query: throttled, erroring, or unparseable.

    Distinct from "DBLP answered with zero hits", which is a real answer a
    caller may act on. This exception means the caller knows nothing, and must
    not report a count.
    """


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a `Retry-After` header's delay-seconds form; `None` if absent or a
    HTTP-date (rare for this API, and 2**attempt covers it well enough)."""
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _wait_for_turn() -> None:
    """Sleep until `MIN_INTERVAL` has passed since the last request went out."""
    global _last_request
    elapsed = time.monotonic() - _last_request
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_request = time.monotonic()


def query(params: dict) -> dict:
    """Run one paced, retried DBLP search-API query; return its parsed JSON.

    Raises `DblpUnavailable` when DBLP could not be made to answer, so that a
    failed query can never be mistaken for a result.
    """
    last_failure = ""
    for attempt in range(MAX_RETRIES):
        _wait_for_turn()

        try:
            response = requests.get(
                API_URL, params=params, headers=HEADERS, timeout=TIMEOUT
            )
        except requests.RequestException as exc:
            last_failure = type(exc).__name__
            logger.debug("DBLP request failed (%s); retrying", last_failure)
            time.sleep(2**attempt)
            continue

        if response.status_code in RETRYABLE_STATUSES:
            last_failure = f"HTTP {response.status_code}"
            # DBLP's own Retry-After beats a guessed exponential backoff when
            # it bothers to send one; fall back to 2**attempt when it doesn't.
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            time.sleep(retry_after if retry_after is not None else 2**attempt)
            continue

        if response.status_code != 200:
            raise DblpUnavailable(f"HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError as exc:
            raise DblpUnavailable("unparseable response") from exc

    raise DblpUnavailable(f"{last_failure} after {MAX_RETRIES} attempts")
