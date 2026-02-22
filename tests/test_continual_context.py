"""Unit tests for continual_context auto-learning."""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local import continual_context as cc


def _make_ollama_response(terms: list) -> MagicMock:
    """Build a mock HTTP response that returns a JSON array of terms."""
    body = json.dumps({"response": json.dumps(terms)}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestExtractAndLearnEmptyInput(unittest.TestCase):
    def test_empty_string_returns_empty(self):
        result = cc.extract_and_learn("", "any-model", "http://localhost:11434")
        self.assertEqual(result, [])

    def test_whitespace_only_returns_empty(self):
        result = cc.extract_and_learn("   ", "any-model", "http://localhost:11434")
        self.assertEqual(result, [])


class TestExtractAndLearnOllamaUnavailable(unittest.TestCase):
    def test_url_error_returns_empty(self):
        with patch("whisper_local.continual_context.url_request.urlopen",
                   side_effect=URLError("connection refused")):
            result = cc.extract_and_learn(
                "This talks about PyTorch and CUDA.", "llama3.2:3b",
                "http://localhost:11434"
            )
        self.assertEqual(result, [])


class TestExtractAndLearnSuccess(unittest.TestCase):
    def setUp(self):
        # Redirect continual_context storage to a temp directory for each test.
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_context_file = cc.context_file

        tmp_path = os.path.join(self._tmp.name, "state", "continual_context.json")
        cc.context_file = lambda: tmp_path  # type: ignore[assignment]

    def tearDown(self):
        cc.context_file = self._orig_context_file  # type: ignore[assignment]
        self._tmp.cleanup()

    def _patch_urlopen(self, terms: list):
        """Context manager that patches urlopen: first call (tags) succeeds, second returns terms."""
        mock_tags = MagicMock()
        mock_tags.__enter__ = lambda s: s
        mock_tags.__exit__ = MagicMock(return_value=False)

        mock_generate = _make_ollama_response(terms)

        return patch(
            "whisper_local.continual_context.url_request.urlopen",
            side_effect=[mock_tags, mock_generate],
        )

    def test_new_words_added_and_returned(self):
        # Use terms not present in DEFAULT_CONTEXT
        terms = ["Anthropic", "Whisper", "LlamaCpp"]
        with self._patch_urlopen(terms):
            added = cc.extract_and_learn(
                "We use Anthropic's Whisper with LlamaCpp.", "llama3.2:3b",
                "http://localhost:11434"
            )
        self.assertEqual(sorted(added), sorted(terms))
        words = cc.load_context()
        for term in terms:
            self.assertIn(term, words)

    def test_duplicate_words_not_re_added(self):
        terms = ["Anthropic", "LlamaCpp"]
        # First call — adds the words.
        with self._patch_urlopen(terms):
            first = cc.extract_and_learn(
                "Anthropic and LlamaCpp.", "llama3.2:3b", "http://localhost:11434"
            )
        self.assertEqual(sorted(first), sorted(terms))

        # Second call with same terms — none should be re-added.
        with self._patch_urlopen(terms):
            second = cc.extract_and_learn(
                "Anthropic and LlamaCpp again.", "llama3.2:3b", "http://localhost:11434"
            )
        self.assertEqual(second, [])

    def test_cap_of_10_words_enforced(self):
        fifteen_terms = [f"Term{i}" for i in range(15)]
        with self._patch_urlopen(fifteen_terms):
            added = cc.extract_and_learn(
                "Many technical terms here.", "llama3.2:3b", "http://localhost:11434"
            )
        self.assertLessEqual(len(added), 10)


class TestSaveContextDeduplication(unittest.TestCase):
    def test_duplicate_words_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig = cc.context_file
            path = os.path.join(tmp, "state", "continual_context.json")
            cc.context_file = lambda: path  # type: ignore[assignment]
            try:
                cc.save_context(["Alpha", "Beta", "alpha", "BETA", "Gamma"])
                words = cc.load_context()
                lower_words = [w.casefold() for w in words]
                self.assertEqual(len(lower_words), len(set(lower_words)),
                                 "Duplicates found after save_context deduplication")
                self.assertIn("Alpha", words)
                self.assertIn("Beta", words)
                self.assertIn("Gamma", words)
            finally:
                cc.context_file = orig  # type: ignore[assignment]


class TestVocabularyRegressionNoNameError(unittest.TestCase):
    def test_add_vocabulary_word_does_not_raise(self):
        from whisper_local.vocabulary import add_vocabulary_word
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state", "vocabulary.json")
            # Should not raise NameError for 'candidate' or any other error.
            words, added = add_vocabulary_word(path, "Ableton")
            self.assertTrue(added)
            self.assertIn("Ableton", words)


if __name__ == "__main__":
    unittest.main()
