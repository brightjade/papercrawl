from scripts.ngrams import tokenize, extract_ngrams, build_ngram_data


class TestTokenize:
    def test_basic(self):
        tokens = tokenize("Reinforcement Learning for Robot Control")
        assert "reinforcement" in tokens
        assert "learning" in tokens
        assert "robot" in tokens
        assert "control" in tokens

    def test_removes_stopwords(self):
        tokens = tokenize("A Novel Approach to the Problem")
        assert "novel" not in tokens
        assert "approach" not in tokens
        assert "the" not in tokens
        assert "problem" in tokens

    def test_strips_punctuation(self):
        tokens = tokenize("multi-modal, vision-language (models).")
        assert "multi" in tokens
        assert "modal" in tokens
        assert "vision" in tokens
        assert "language" in tokens
        assert "models" in tokens

    def test_filters_short_tokens(self):
        tokens = tokenize("On AI in NLP and ML")
        # "on", "ai", "in", "ml" are all too short (< 3 chars) or stopwords
        assert "nlp" in tokens
        assert "ai" not in tokens

    def test_empty_string(self):
        assert tokenize("") == []


class TestExtractNgrams:
    def test_bigrams(self):
        tokens = ["reinforcement", "learning", "robot"]
        ngrams = extract_ngrams(tokens, ns=(2,))
        assert "reinforcement learning" in ngrams
        assert "learning robot" in ngrams
        assert len(ngrams) == 2

    def test_trigrams(self):
        tokens = ["large", "language", "model", "training"]
        ngrams = extract_ngrams(tokens, ns=(3,))
        assert "large language model" in ngrams
        assert "language model training" in ngrams
        assert len(ngrams) == 2

    def test_bigrams_and_trigrams(self):
        tokens = ["deep", "reinforcement", "learning"]
        ngrams = extract_ngrams(tokens, ns=(2, 3))
        assert "deep reinforcement" in ngrams
        assert "reinforcement learning" in ngrams
        assert "deep reinforcement learning" in ngrams
        assert len(ngrams) == 3

    def test_too_few_tokens(self):
        assert extract_ngrams(["single"], ns=(2,)) == []
        assert extract_ngrams([], ns=(2, 3)) == []


class TestBuildNgramData:
    def _parse_conf(self, conf_id):
        parts = conf_id.rsplit("_", 1)
        return parts[0].upper(), int(parts[1])

    def test_structure(self):
        papers = {
            "iclr_2024": [
                {"title": "Deep Reinforcement Learning for Games", "abstract": "We study deep reinforcement learning"},
                {"title": "Vision Transformers Revisited", "abstract": ""},
            ],
            "iclr_2025": [
                {"title": "Deep Reinforcement Learning Advances", "abstract": "Deep reinforcement learning has improved"},
                {"title": "Large Language Models Scale", "abstract": "Large language models continue to scale"},
            ],
        }
        result = build_ngram_data(papers, self._parse_conf)

        assert "top_ngrams_by_year" in result
        assert "rising_falling_by_year" in result
        assert "ngram_trends" in result
        assert "venue_ngram_matrix_by_year" in result

        assert "2024" in result["top_ngrams_by_year"]
        assert "2025" in result["top_ngrams_by_year"]

    def test_top_ngrams_format(self):
        papers = {
            "iclr_2025": [
                {"title": "Deep Reinforcement Learning", "abstract": "Deep reinforcement learning approach"},
            ],
        }
        result = build_ngram_data(papers, self._parse_conf)
        entries = result["top_ngrams_by_year"]["2025"]
        assert len(entries) > 0
        assert "ngram" in entries[0]
        assert "count" in entries[0]
        # "deep reinforcement" should appear as top bigram (appears twice: title + abstract)
        ngrams = [e["ngram"] for e in entries]
        assert "deep reinforcement" in ngrams

    def test_rising_falling(self):
        papers = {
            "iclr_2024": [
                {"title": f"Deep Reinforcement Learning Paper {i}", "abstract": "Deep reinforcement learning"}
                for i in range(10)
            ],
            "iclr_2025": [
                {"title": f"Large Language Model Paper {i}", "abstract": "Large language models"}
                for i in range(10)
            ],
        }
        result = build_ngram_data(papers, self._parse_conf)
        # 2025 should have rising/falling
        assert "2025" in result["rising_falling_by_year"]
        rf = result["rising_falling_by_year"]["2025"]
        assert "rising" in rf
        assert "falling" in rf

    def test_ngram_trends_tracks_across_years(self):
        papers = {
            "iclr_2024": [
                {"title": f"Deep Learning Paper {i}", "abstract": ""} for i in range(10)
            ],
            "iclr_2025": [
                {"title": f"Deep Learning Paper {i}", "abstract": ""} for i in range(20)
            ],
        }
        result = build_ngram_data(papers, self._parse_conf)
        assert "deep learning" in result["ngram_trends"]
        trend = result["ngram_trends"]["deep learning"]
        assert trend["2024"] == 10
        assert trend["2025"] == 20

    def test_venue_matrix(self):
        papers = {
            "iclr_2025": [
                {"title": "Deep Learning Research", "abstract": ""} for _ in range(5)
            ],
            "acl_2025": [
                {"title": "Deep Learning for NLP", "abstract": ""} for _ in range(3)
            ],
        }
        result = build_ngram_data(papers, self._parse_conf)
        matrix = result["venue_ngram_matrix_by_year"]["2025"]
        assert "ICLR" in matrix
        assert "ACL" in matrix
