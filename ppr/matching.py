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
