"""Deciding whether a Semantic Scholar record is the paper we crawled.

Pure functions, no I/O. `ppr/enrich.py` calls these from every path that can
bind a paper to an S2 record, so the rule for what counts as the same paper
lives in exactly one place.
"""

import difflib
import re
import unicodedata

# LaTeX Greek commands. Both spellings of a letter collapse onto one token so
# that \varepsilon, \epsilon and ε all compare equal.
_GREEK_COMMANDS = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta",
    "eta", "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu",
    "xi", "pi", "rho", "sigma", "tau", "upsilon", "phi", "varphi",
    "chi", "psi", "omega",
}
_CANONICAL = {"varepsilon": "epsilon", "vartheta": "theta", "varphi": "phi"}

_UNICODE_GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ϵ": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota",
    "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi",
    "π": "pi", "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau",
    "υ": "upsilon", "φ": "phi", "ϕ": "phi", "χ": "chi", "ψ": "psi",
    "ω": "omega",
}


def _latex_token(match: re.Match) -> str:
    """A LaTeX command becomes its Greek token, or vanishes.

    Padded with spaces so a dropped command cannot fuse the words on either
    side of it into one token.
    """
    name = match.group(1)
    if name in _GREEK_COMMANDS:
        return f" {_CANONICAL.get(name, name)} "
    return " "


def title_key(title: str) -> str:
    """Canonical form for comparing titles across sources.

    Crawled titles and Semantic Scholar titles disagree constantly over things
    that are not disagreements: curly quotes, inline LaTeX, a stray space
    before a colon, a trailing period. Reducing both sides to lowercase
    alphanumerics settles all of those at once. Greek needs its own step,
    because `$(1+\\varepsilon)$` and `(1+ε)` share no characters at all.

    Strictly more aggressive than `ppr.enrich.normalize_title`: any two titles
    equal under that are equal under this. The refresh path's re-verification
    depends on it, so a paper already recorded as matched can never be demoted.
    """
    s = unicodedata.normalize("NFKC", title).lower()
    s = re.sub(r"\\([a-z]+)", _latex_token, s)
    s = "".join(_UNICODE_GREEK.get(c, c) for c in s)
    return re.sub(r"[^a-z0-9]+", "", s)


MATCHED = "matched"
MATCHED_FUZZY = "matched_fuzzy"
REJECT = "reject"

# Thresholds. Calibrated on a 400-paper sample of the recorded `mismatch`
# population (2026-08-01): 69.5% matched, 28.2% fuzzy, 2.2% rejected, with
# every reject confirmed by hand as a genuinely different paper.
_SIM_STRONG = 0.90          # with corroborating authors
_SIM_WEAK = 0.70            # with strongly corroborating authors
_SIM_NO_AUTHORS = 0.95      # title is the only evidence there is
_OVERLAP_SOME = 0.5
_OVERLAP_STRONG = 0.7


def _last_names(names: list[str]) -> set[str]:
    """Accent-stripped lowercase surnames.

    Only the last token is kept: sources disagree about initials, middle
    names and given-name order far more than they disagree about surnames.
    """
    out: set[str] = set()
    for name in names or []:
        folded = unicodedata.normalize("NFKD", name)
        folded = "".join(c for c in folded if not unicodedata.combining(c))
        parts = re.sub(r"[^A-Za-z\s\-]", " ", folded).split()
        if parts:
            out.add(parts[-1].lower())
    return out


def author_overlap(ours: list[str], theirs: list[str]) -> float | None:
    """Shared surnames as a fraction of the shorter list, or None.

    None means at least one side has no author data, which is a different
    thing from no overlap and must not be read as evidence against a match.
    Dividing by the shorter list keeps a truncated conference listing from
    reading as a disagreement with a complete one.
    """
    a, b = _last_names(ours), _last_names(theirs)
    if not a or not b:
        return None
    return len(a & b) / min(len(a), len(b))


def match_verdict(our_title: str, our_authors: list[str], entry: dict) -> str:
    """Is `entry` the paper we crawled?

    `entry` must be a real Semantic Scholar record — callers filter None
    first, because "the API had nothing to say" is not a failed match.

    An exact `title_key` match settles it before authors are consulted, which
    is what keeps the 1,337 papers with no author data (naacl_2025, almost all
    of them) working normally whenever the title agrees.
    """
    ours = title_key(our_title)
    theirs = title_key(entry.get("title") or "")
    if ours and ours == theirs:
        return MATCHED

    sim = difflib.SequenceMatcher(None, ours, theirs).ratio()
    overlap = author_overlap(
        our_authors, [a.get("name", "") for a in entry.get("authors") or []]
    )

    if overlap is None:
        # Containment stays off here on purpose. "Beta Diffusion" sits inside
        # "Floorplan Generation with Graph Beta Diffusion", and without authors
        # nothing distinguishes that from a subtitle being added to a real
        # match. Requiring near-identity is the only safe rule left.
        return MATCHED_FUZZY if sim >= _SIM_NO_AUTHORS else REJECT

    # Guard both sides: "" is a substring of every string, so an empty title
    # would otherwise be "contained" in ours and pass on authors alone.
    contained = bool(ours) and bool(theirs) and (ours in theirs or theirs in ours)

    if sim >= _SIM_STRONG and overlap >= _OVERLAP_SOME:
        return MATCHED_FUZZY
    if (sim >= _SIM_WEAK or contained) and overlap >= _OVERLAP_STRONG:
        return MATCHED_FUZZY
    return REJECT
