"""Tests for final regex sanitizer glitch cleanup."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.final_sanitizer import sanitize_final_glitches


class TestFinalSanitizer(unittest.TestCase):
    def test_python_accent_and_init_signature(self):
        src = "Death init self comma args colon"
        out = sanitize_final_glitches(src, context="code_editor")
        self.assertEqual(out, "def __init__(self, args):")

    def test_endpoint_colon_to_symbol(self):
        src = "connect to 127.0.0.1 colon 8080 now"
        out = sanitize_final_glitches(src)
        self.assertEqual(out, "connect to 127.0.0.1:8080 now")

    def test_grandma_vocative_comma(self):
        src = "lets eat grandma."
        out = sanitize_final_glitches(src)
        self.assertEqual(out, "Let's eat, Grandma.")

    def test_death_metal_not_modified(self):
        src = "I love death metal."
        out = sanitize_final_glitches(src)
        self.assertEqual(out, src)

    def test_plain_colon_word_not_forced(self):
        src = "In grammar, colon is a punctuation mark."
        out = sanitize_final_glitches(src)
        self.assertEqual(out, src)

    def test_audio_queue_glitch_to_q_factor(self):
        src = "we are checking THD+N and in the queue 2.7"
        out = sanitize_final_glitches(src)
        self.assertEqual(out, "we are checking THD+N and the Q-factor to 0.7")

    def test_maker_wright_name_patch(self):
        src = "direction right, the action right, and the maker right."
        out = sanitize_final_glitches(src)
        self.assertEqual(out, "direction right, the action right, and the maker Wright.")


if __name__ == "__main__":
    unittest.main()
