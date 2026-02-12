"""
Tests for the post-processing pipeline module.

Run with: python -m pytest tests/test_post_processor.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.post_processor import PipelineConfig, PostProcessingPipeline


class TestPostProcessorBasics(unittest.TestCase):
    def test_empty_input(self):
        p = PostProcessingPipeline(PipelineConfig(enable_homophone=False))
        out, diff = p.process("")
        self.assertEqual(out, "")
        self.assertEqual(diff, "")

    def test_unknown_domain_does_not_crash(self):
        p = PostProcessingPipeline(
            PipelineConfig(
                enable_numeric=False,
                enable_punctuation=False,
                enable_domain=True,
                enable_code_mode=False,
                enable_homophone=False,
                domains=["audio_engineering", "networking"],
            )
        )
        out, _ = p.process("48 v phantom power")
        self.assertIn("48V", out)

    def test_chunking_for_long_input(self):
        p = PostProcessingPipeline(
            PipelineConfig(
                enable_numeric=True,
                enable_punctuation=False,
                enable_domain=False,
                enable_code_mode=False,
                enable_homophone=False,
                enable_final_sanitizer=True,
                max_chunk_chars=120,
            )
        )
        src = ("the value is 0. 7 and the ip is 127. 0. 0. 1: 8080. " * 20).strip()
        chunks = p._chunk_text(src, 120)
        self.assertGreater(len(chunks), 1)
        out, _ = p.process(src)
        self.assertIn("0.7", out)
        self.assertIn("127.0.0.1:8080", out)

    def test_final_sanitizer_glitch_cleanup(self):
        p = PostProcessingPipeline(
            PipelineConfig(
                enable_numeric=False,
                enable_punctuation=False,
                enable_domain=False,
                enable_code_mode=False,
                enable_homophone=False,
                enable_final_sanitizer=True,
            )
        )
        out, _ = p.process("lets eat grandma and connect to localhost colon 3000")
        self.assertIn("Let's eat, Grandma", out)
        self.assertIn("localhost:3000", out)


class TestPostProcessorResilience(unittest.TestCase):
    @patch("whisper_local.processing.post_processor.format_numbers")
    def test_step_failure_does_not_kill_pipeline(self, mock_format):
        mock_format.side_effect = RuntimeError("boom")
        p = PostProcessingPipeline(
            PipelineConfig(
                enable_numeric=True,
                enable_punctuation=False,
                enable_domain=False,
                enable_code_mode=True,
                enable_homophone=False,
            )
        )
        src = "death foo colon"
        out, _ = p.process(src)
        # numeric formatter failure should not prevent downstream code mode correction
        self.assertEqual(out, "def foo:")


class TestPostProcessorIntegration(unittest.TestCase):
    @patch("whisper_local.processing.post_processor.restore_punctuation")
    def test_real_whisper_sample_pipeline(self, mock_restore_punctuation):
        # Deterministic punctuation fallback for test stability.
        def _simple_punct(text: str) -> str:
            text = text.strip()
            if not text:
                return text
            text = text[0].upper() + text[1:]
            if text[-1] not in ".!?":
                text += "."
            return text

        mock_restore_punctuation.side_effect = _simple_punct

        src = (
            "switching to the audio domain i need to know if the xlr cable is providing "
            "48 v of Phantom Power to the shure sm7b we are checking for the THD+N ratings "
            "to 0. 7 i am rendering this project as a wave file at 24-Bit-depth 48 kilohertz "
            "sample rate did it write khz or spell it out"
        )

        p = PostProcessingPipeline(
            PipelineConfig(
                enable_numeric=True,
                enable_punctuation=True,
                enable_domain=True,
                enable_code_mode=False,
                enable_homophone=False,
                domains=["audio_engineering"],
            )
        )

        out, diff = p.process(src)

        self.assertTrue(out[0].isupper())
        self.assertIn(".", out)
        self.assertIn("48V", out)
        self.assertIn("Shure SM7B", out)
        self.assertIn("XLR", out)
        self.assertIn("THD+N", out)
        self.assertIn("0.7", out)
        self.assertIn("WAV", out)
        self.assertIn("24-bit depth", out)
        self.assertIn("48kHz", out)
        self.assertIn("kHz", out)
        self.assertTrue(len(diff) > 0)


if __name__ == "__main__":
    unittest.main()

