from unittest.mock import MagicMock

import pytest

from ppr.register import (
    RegistrationError,
    openreview_selections,
    register_cvf,
    register_dblp,
    register_usenix,
    render_openreview_config,
)


def _module(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body)
    return p


DBLP_SRC = '''DBLP_CONFERENCES = {
    "icse_2025": {"key": "db/conf/icse/icse2025.bht"},
}
'''

CVF_SRC = '''CVF_CONFERENCES = {
    "cvpr_2025": {"url": f"{CVF_BASE_URL}/CVPR2025?day=all", "parser": "openaccess"},
}
'''

USENIX_SRC = '''USENIX_CONFERENCES = {
    "usenix_security_2025": "usenixsecurity25",
}
'''


class TestRegisterDblp:
    def test_inserts_before_the_closing_brace(self, tmp_path):
        p = _module(tmp_path, "dblp.py", DBLP_SRC)
        register_dblp("icse_2026", "db/conf/icse/icse2026.bht", p)
        text = p.read_text()
        assert '"icse_2026": {"key": "db/conf/icse/icse2026.bht"},' in text
        assert text.index("icse_2025") < text.index("icse_2026")
        assert "icse_2025" in text  # existing entries survive

    def test_refuses_a_duplicate(self, tmp_path):
        p = _module(tmp_path, "dblp.py", DBLP_SRC)
        with pytest.raises(RegistrationError, match="already registered"):
            register_dblp("icse_2025", "db/conf/icse/icse2025.bht", p)

    def test_raises_when_the_dict_is_absent(self, tmp_path):
        p = _module(tmp_path, "dblp.py", "SOMETHING_ELSE = {}\n")
        with pytest.raises(RegistrationError, match="DBLP_CONFERENCES"):
            register_dblp("icse_2026", "k", p)


class TestRegisterCvf:
    def test_inserts_entry(self, tmp_path):
        p = _module(tmp_path, "cvf.py", CVF_SRC)
        register_cvf("cvpr_2026", "https://openaccess.thecvf.com/CVPR2026?day=all", "openaccess", p)
        assert '"cvpr_2026": {"url": "https://openaccess.thecvf.com/CVPR2026?day=all", "parser": "openaccess"},' in p.read_text()

    def test_includes_year_for_the_ecva_parser(self, tmp_path):
        p = _module(tmp_path, "cvf.py", CVF_SRC)
        register_cvf("eccv_2026", "https://www.ecva.net/papers.php", "ecva", p, year=2026)
        assert '"year": 2026' in p.read_text()


class TestRegisterUsenix:
    def test_inserts_entry(self, tmp_path):
        p = _module(tmp_path, "usenix.py", USENIX_SRC)
        register_usenix("usenix_security_2026", "usenixsecurity26", p)
        assert '"usenix_security_2026": "usenixsecurity26",' in p.read_text()


class TestOpenreviewSelections:
    def _client(self, venues):
        notes = []
        for v in venues:
            n = MagicMock()
            n.content = {"venue": {"value": v}}
            notes.append(n)
        c = MagicMock()
        c.get_all_notes.return_value = notes
        return c

    def test_single_venue_value_yields_one_main_selection(self):
        """CoRL 2024 tags every paper 'CoRL 2024' -- the bug this prevents."""
        client = self._client(["CoRL 2024"] * 264)
        assert openreview_selections(client, "robot-learning.org/CoRL/2024/Conference") == {
            "main": "CoRL 2024"
        }

    def test_oral_and_poster_are_named_from_the_venue_strings(self):
        client = self._client(["ICLR 2026 Oral"] * 5 + ["ICLR 2026 Poster"] * 50)
        assert openreview_selections(client, "ICLR.cc/2026/Conference") == {
            "oral": "ICLR 2026 Oral",
            "poster": "ICLR 2026 Poster",
        }

    def test_spotlight_is_recognised(self):
        client = self._client(["ICML 2026 Oral", "ICML 2026 Spotlight", "ICML 2026 Poster"])
        assert set(openreview_selections(client, "ICML.cc/2026/Conference")) == {
            "oral", "spotlight", "poster"
        }

    def test_no_notes_raises_rather_than_writing_an_empty_config(self):
        c = MagicMock()
        c.get_all_notes.return_value = []
        with pytest.raises(RegistrationError, match="no papers"):
            openreview_selections(c, "ICLR.cc/2027/Conference")


class TestRenderOpenreviewConfig:
    def test_renders_loadable_yaml(self):
        import yaml

        text = render_openreview_config("CoRL", 2024, "robot-learning.org/CoRL/2024/Conference",
                                        {"main": "CoRL 2024"})
        parsed = yaml.safe_load(text)["conference"]
        assert parsed["name"] == "CoRL"
        assert parsed["year"] == 2024
        assert parsed["venue_id"] == "robot-learning.org/CoRL/2024/Conference"
        assert parsed["selections"] == {"main": "CoRL 2024"}
        assert parsed["api_version"] == 2
