from ppr.scrapers.dblp import _clean_author


class TestCleanAuthor:
    def test_strips_four_digit_suffix(self):
        assert _clean_author("Hao Zhong 0001") == "Hao Zhong"

    def test_strips_different_suffix(self):
        assert _clean_author("Wei Meng 0003") == "Wei Meng"

    def test_no_suffix_unchanged(self):
        assert _clean_author("John Smith") == "John Smith"

    def test_name_ending_in_digits_not_suffix(self):
        # Only strip if preceded by space and exactly 4 digits at end
        assert _clean_author("Agent 47") == "Agent 47"

    def test_empty_string(self):
        assert _clean_author("") == ""
