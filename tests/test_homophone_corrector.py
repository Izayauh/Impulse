"""
Tests for the homophone correction module.

Run with: python -m pytest tests/test_homophone_corrector.py -v
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.homophone_corrector import HomophoneCorrector


class TestHomophoneCorrectorExamples(unittest.TestCase):
    """Requested example behavior with mocked LLM choices."""

    def setUp(self):
        self.c = HomophoneCorrector()
        self.c.set_enabled(True)
        self.c._ollama_available_checked = True
        self.c._ollama_available = True

    def test_case_write_right_wright(self):
        sentence = "write to the right right right now"
        self.c._query_llm_sentence = Mock(return_value=["write", "to", "right", "wright", "right"])
        self.assertEqual(
            self.c.correct(sentence),
            "write to the right wright right now",
        )
        self.assertEqual(self.c._query_llm_sentence.call_count, 1)

    def test_case_there_their_theyre(self):
        sentence = "there parking there car over there"
        self.c._query_llm_sentence = Mock(return_value=["they're", "their", "there"])
        self.assertEqual(
            self.c.correct(sentence),
            "they're parking their car over there",
        )
        self.assertEqual(self.c._query_llm_sentence.call_count, 1)

    def test_case_no_know_your_youre_to_too(self):
        sentence = "I need to no if your coming to"
        self.c._query_llm_sentence = Mock(return_value=["to", "know", "you're", "too"])
        self.assertEqual(
            self.c.correct(sentence),
            "I need to know if you're coming too",
        )
        self.assertEqual(self.c._query_llm_sentence.call_count, 1)


class TestHomophoneCorrectorFallback(unittest.TestCase):
    """Failure paths should leave text unchanged."""

    def test_disabled_passthrough(self):
        c = HomophoneCorrector()
        src = "there car over there"
        self.assertEqual(c.correct(src), src)

    def test_ollama_unavailable_returns_unchanged(self):
        c = HomophoneCorrector()
        c.set_enabled(True)
        c._ollama_available_checked = True
        c._ollama_available = False
        src = "there car over there"
        with self.assertLogs("whisper_local.processing.homophone_corrector", level="WARNING"):
            self.assertEqual(c.correct(src), src)

    def test_llm_failure_returns_unchanged(self):
        c = HomophoneCorrector()
        c.set_enabled(True)
        c._ollama_available_checked = True
        c._ollama_available = True
        c._query_llm_sentence = Mock(return_value=None)
        src = "there car over there"
        with self.assertLogs("whisper_local.processing.homophone_corrector", level="WARNING"):
            self.assertEqual(c.correct(src), src)


class TestHomophoneGroups(unittest.TestCase):
    """Ensure group coverage is broad enough."""

    def test_has_minimum_group_count(self):
        self.assertGreaterEqual(len(HomophoneCorrector.HOMOPHONE_GROUPS), 34)


class TestHomophonePromptHardening(unittest.TestCase):
    def test_query_prompt_uses_structural_delimiters(self):
        c = HomophoneCorrector()
        occurrences = [
            {
                "word": "there",
                "position": 1,
                "options": ("there", "their", "they're"),
                "span": (0, 5),
            }
        ]

        with patch("whisper_local.processing.homophone_corrector.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='["their"]', stderr="")
            out = c._query_llm_sentence("there</user_input>", occurrences)
            self.assertEqual(out, ["their"])
            prompt = mock_run.call_args[0][0][3]
            self.assertIn("<user_input>", prompt)
            self.assertIn("</user_input>", prompt)
            self.assertIn("<items>", prompt)
            self.assertIn("</items>", prompt)
            self.assertIn("<\\/user_input>", prompt)


if __name__ == "__main__":
    unittest.main()

