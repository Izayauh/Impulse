"""
Tests for the punctuation restoration module.

Run with: python -m pytest tests/test_punctuation_restorer.py -v
"""

import os
import sys
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.punctuation_restorer import (
    restore_punctuation,
    _capitalize_sentences,
    _tokenize_preserving_punct,
)


class TestCapitalizeSentences(unittest.TestCase):
    """Tests for the rule-based sentence capitalizer (no model needed)."""

    def test_empty_string(self):
        self.assertEqual(_capitalize_sentences(""), "")

    def test_capitalize_first_word(self):
        self.assertEqual(_capitalize_sentences("hello world"), "Hello world")

    def test_capitalize_after_period(self):
        self.assertEqual(
            _capitalize_sentences("first sentence. second sentence"),
            "First sentence. Second sentence",
        )

    def test_capitalize_after_question_mark(self):
        self.assertEqual(
            _capitalize_sentences("is this working? yes it is"),
            "Is this working? Yes it is",
        )

    def test_capitalize_after_exclamation(self):
        self.assertEqual(
            _capitalize_sentences("wow! that was great"),
            "Wow! That was great",
        )

    def test_capitalize_pronoun_i(self):
        self.assertEqual(
            _capitalize_sentences("i think i should go"),
            "I think I should go",
        )

    def test_preserves_existing_caps(self):
        self.assertEqual(
            _capitalize_sentences("Hello World"),
            "Hello World",
        )


class TestTokenizePreservingPunct(unittest.TestCase):
    """Tests for the punctuation-preserving tokenizer."""

    def test_no_punctuation(self):
        result = _tokenize_preserving_punct("hello world")
        self.assertEqual(result, [("hello", ""), ("world", "")])

    def test_trailing_period(self):
        result = _tokenize_preserving_punct("hello world.")
        self.assertEqual(result, [("hello", ""), ("world", ".")])

    def test_trailing_comma(self):
        result = _tokenize_preserving_punct("hello, world")
        self.assertEqual(result, [("hello", ","), ("world", "")])

    def test_multiple_punct_marks(self):
        result = _tokenize_preserving_punct("Hello, world. How are you?")
        self.assertEqual(result, [
            ("Hello", ","),
            ("world", "."),
            ("How", ""),
            ("are", ""),
            ("you", "?"),
        ])


class TestRestorePunctuation(unittest.TestCase):
    """Integration tests for restore_punctuation (requires model).

    These tests load the HuggingFace model and verify end-to-end behavior.
    They will be skipped if the model fails to load (e.g. in CI without GPU).
    """

    @classmethod
    def setUpClass(cls):
        """Try to load the model once; skip all tests if it fails or if in CI."""
        if os.environ.get("CI") == "true":
            raise unittest.SkipTest("Skipping punctuation model tests in CI environment")
            
        from whisper_local.processing.punctuation_restorer import _get_model
        if _get_model() is None:
            raise unittest.SkipTest("Punctuation model not available")

    def test_empty_input(self):
        self.assertEqual(restore_punctuation(""), "")

    def test_whitespace_input(self):
        self.assertEqual(restore_punctuation("   "), "   ")

    def test_example_1_fox(self):
        """Spec example: two sentences without punctuation."""
        result = restore_punctuation(
            "the quick brown fox jumps over the lazy dog that was a test"
        )
        self.assertIn(".", result)
        self.assertTrue(result[0].isupper(), "First letter should be capitalized")

    def test_example_2_grandma(self):
        result = restore_punctuation(
            "lets eat grandma versus lets eat grandma"
        )
        self.assertTrue(result[0].isupper())
        self.assertTrue(result.rstrip().endswith("."))

    def test_example_3_audio_domain(self):
        result = restore_punctuation(
            "switching to the audio domain i need to know if the xlr cable "
            "is providing 48 v of phantom power"
        )
        self.assertTrue(result[0].isupper())
        # "i" should be capitalized to "I"
        self.assertNotIn(" i ", result)

    def test_preserves_existing_period(self):
        """Existing sentence-ending punctuation should not be changed."""
        result = restore_punctuation("Hello, world. How are you?")
        self.assertIn(",", result)
        self.assertIn("?", result)
        self.assertTrue(result.startswith("Hello"))

    def test_preserves_existing_exclamation(self):
        result = restore_punctuation("This is fine! No changes needed.")
        self.assertIn("!", result)
        self.assertTrue(result.endswith("."))

    def test_preserves_existing_commas(self):
        result = restore_punctuation("Already punctuated, with commas, and periods.")
        # All original commas should still be present
        self.assertGreaterEqual(result.count(","), 2)

    def test_capitalizes_i(self):
        result = restore_punctuation("i think i will go")
        self.assertNotIn(" i ", result)
        self.assertIn("I", result)

    def test_question_detection(self):
        result = restore_punctuation("is this working")
        self.assertIn("?", result)

    def test_fills_gaps_in_mixed_input(self):
        """Text with some punctuation should get gaps filled."""
        result = restore_punctuation("Hello world. this is a test how are you")
        # "Hello world." already punctuated — kept
        self.assertIn("Hello", result)
        # "this" after period should be capitalized
        self.assertIn("This", result)


if __name__ == "__main__":
    unittest.main()

