"""
Tests for the code-mode correction module.

Run with: python -m pytest tests/test_code_mode.py -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.code_mode import CodeModeCorrector


class TestCodeModeExamples(unittest.TestCase):
    """Requested behavior examples."""

    @classmethod
    def setUpClass(cls):
        cls.c = CodeModeCorrector(enabled=True)

    def test_def_init_signature(self):
        self.assertEqual(
            self.c.correct("Death init underscore underscore self comma args colon"),
            "def __init__(self, args):",
        )

    def test_library_alias_normalization(self):
        self.assertEqual(
            self.c.correct("importing pandas as PD and numpy as NP"),
            "importing pandas as pd and numpy as np",
        )

    def test_camel_and_snake(self):
        self.assertEqual(
            self.c.correct(
                "camel case variable versus snake underscore case underscore variable"
            ),
            "camelCaseVariable versus snake_case_variable",
        )


class TestCodeModeToggle(unittest.TestCase):
    """Code mode should be opt-in via toggle."""

    def test_disabled_passthrough(self):
        c = CodeModeCorrector(enabled=False)
        src = "Death init underscore underscore self comma args colon"
        self.assertEqual(c.correct(src), src)

    def test_enable_after_init(self):
        c = CodeModeCorrector(enabled=False)
        c.set_enabled(True)
        self.assertEqual(c.correct("death foo colon"), "def foo:")


class TestCodeModeIntelligence(unittest.TestCase):
    """Hybrid deterministic + confidence-gated behavior."""

    def test_operator_mapping_for_code_blocks(self):
        c = CodeModeCorrector(enabled=True)
        self.assertEqual(
            c.correct("if value less than or equal to max value colon"),
            "if value <= max value:",
        )

    def test_auto_detect_skips_prose(self):
        c = CodeModeCorrector(enabled=True, auto_detect=True)
        text = "thanks for your help today"
        self.assertEqual(c.correct(text), text)

    def test_auto_detect_handles_code_context(self):
        c = CodeModeCorrector(enabled=True, auto_detect=True)
        self.assertEqual(
            c.correct("if score greater than threshold colon"),
            "if score > threshold:",
        )

    def test_intent_scoring_prefers_code(self):
        c = CodeModeCorrector(enabled=True, auto_detect=True)
        code_intent = c.analyze_intent("def fetch data from api colon")
        prose_intent = c.analyze_intent("thanks for taking the time to review this")
        self.assertGreater(code_intent.score, prose_intent.score)
        self.assertTrue(code_intent.looks_code_like)
        self.assertFalse(prose_intent.looks_code_like)


if __name__ == "__main__":
    unittest.main()

