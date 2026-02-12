"""Tests for user vocabulary storage and prompt composition."""

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.vocabulary import add_vocabulary_word, compose_prompt, load_vocabulary, save_vocabulary


class TestVocabulary(unittest.TestCase):
    def test_save_and_load_words(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "vocabulary.json")
            self.assertTrue(save_vocabulary(path, ["Alice", "GPU Kernel", "Alice"]))
            words = load_vocabulary(path)
            self.assertEqual(words, ["Alice", "GPU Kernel"])

    def test_add_word_is_case_insensitive_unique(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "vocabulary.json")
            words, added = add_vocabulary_word(path, "Ableton")
            self.assertTrue(added)
            self.assertEqual(words, ["Ableton"])

            words, added = add_vocabulary_word(path, "ableton")
            self.assertFalse(added)
            self.assertEqual(words, ["Ableton"])

    def test_compose_prompt_includes_custom_vocabulary(self):
        prompt = compose_prompt("base prompt", ["Ari", "WhisperLocal"])
        self.assertIn("base prompt", prompt)
        self.assertIn("Custom vocabulary:", prompt)
        self.assertIn("Ari", prompt)
        self.assertIn("WhisperLocal", prompt)


if __name__ == "__main__":
    unittest.main()
