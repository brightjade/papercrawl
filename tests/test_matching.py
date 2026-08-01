import pytest

from ppr.matching import title_key


class TestTitleKey:
    @pytest.mark.parametrize(
        "ours,theirs",
        [
            # Curly quotes (neurips_2023)
            (
                "Calibrating “Cheap Signals” in Peer Review without a Prior",
                'Calibrating "Cheap Signals" in Peer Review without a Prior',
            ),
            # Inline LaTeX math (icml_2024)
            (
                "The Non-linear $F$-Design and Applications to Interactive Learning",
                "The Non-linear F-Design and Applications to Interactive Learning",
            ),
            # LaTeX command vs unicode Greek (icml_2023)
            (
                r"Fast $(1+\varepsilon)$-Approximation Algorithms for Binary Matrix Factorization",
                "Fast (1+ε)-Approximation Algorithms for Binary Matrix Factorization",
            ),
            # LaTeX Greek leading a title (corl_2023)
            (
                r"$\alpha$-MDF: An Attention-based Multimodal Differentiable Filter",
                "α-MDF: An Attention-based Multimodal Differentiable Filter",
            ),
            # Stray space before a colon (cvpr_2023)
            (
                "DARE-GRAM: Unsupervised Domain Adaptation Regression",
                "DARE-GRAM : Unsupervised Domain Adaptation Regression",
            ),
            # Trailing period (icml_2026)
            ("What Language is This? Ask Your Tokenizer.", "What Language is This? Ask Your Tokenizer"),
            # Trailing asterisk (iros_2024)
            ("Development of a Bilateral Control Teleoperation System",
             "Development of a Bilateral Control Teleoperation System *"),
            # Double vs single dash (iclr_2026)
            ("GenCtrl -- A Formal Controllability Toolkit",
             "GenCtrl - A Formal Controllability Toolkit"),
            # Case and whitespace, the old normalize_title's whole job
            ("  A   Paper\nTitle ", "a paper title"),
        ],
    )
    def test_cosmetic_differences_collapse(self, ours, theirs):
        assert title_key(ours) == title_key(theirs)

    def test_epsilon_spellings_agree(self):
        assert title_key(r"\varepsilon") == title_key(r"\epsilon") == title_key("ε")
        assert title_key("ϵ") == title_key("ε")

    def test_distinct_titles_stay_distinct(self):
        assert title_key("Beta Diffusion") != title_key(
            "Floorplan Generation with Graph Beta Diffusion"
        )

    def test_unknown_latex_command_is_dropped_not_inlined(self):
        # \mathcal must not leave the letters "mathcal" glued into the key,
        # or two titles differing only in markup stop comparing equal.
        assert title_key(r"A \mathcal{X} Study") == title_key("A X Study")

    def test_is_at_least_as_aggressive_as_normalize_title(self):
        # The safety property the refresh path depends on: anything the old
        # comparison called equal must still be equal, so re-verification can
        # never demote a paper already recorded as matched.
        from ppr.enrich import normalize_title

        pairs = [("A  Paper", "a paper"), ("X\tY", "x y")]
        for a, b in pairs:
            assert normalize_title(a) == normalize_title(b)
            assert title_key(a) == title_key(b)

    def test_empty_and_punctuation_only(self):
        assert title_key("") == ""
        assert title_key("!!! ---") == ""
