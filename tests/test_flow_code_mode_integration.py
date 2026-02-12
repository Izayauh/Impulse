"""Integration checks for flow-level code dictation formatting."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.flow_local_dictation import detect_code_formatting


class TestFlowCodeModeIntegration(unittest.TestCase):
    def test_detect_code_formatting_applies_code_transforms(self):
        self.assertEqual(
            detect_code_formatting("if value less than or equal to max value colon"),
            "if value <= max value:",
        )

    def test_detect_code_formatting_preserves_prose(self):
        text = "Thanks for your help today"
        self.assertEqual(detect_code_formatting(text), text)


if __name__ == "__main__":
    unittest.main()
