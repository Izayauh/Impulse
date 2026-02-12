"""
Tests for the LLM-powered markdown formatter module.

Run with: python -m pytest tests/test_markdown_formatter.py -v
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.markdown_formatter import (
    MARKDOWN_SYSTEM_PROMPT,
    MarkdownFormatter,
)


class TestMarkdownFormatterDisabled(unittest.TestCase):
    """Formatter should be a no-op when disabled."""

    def test_disabled_returns_text_unchanged(self):
        fmt = MarkdownFormatter()
        text = "some raw transcript text"
        self.assertEqual(fmt.format(text), text)

    def test_empty_input_returns_empty(self):
        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        self.assertEqual(fmt.format(""), "")

    def test_whitespace_only_returns_unchanged(self):
        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        self.assertEqual(fmt.format("   "), "   ")


class TestMarkdownFormatterPrompt(unittest.TestCase):
    """Verify the system prompt contains all expected examples and rules."""

    def test_prompt_contains_all_nine_examples(self):
        for label in [
            "Example 1: Feature List",
            "Example 2: Sequential Workflow",
            "Example 3: Technical Debugging",
            "Example 4: Multi-Topic Brain Dump",
            "Example 5: Philosophical Reflection",
            "Example 6: Long Unstructured Ramble",
            "Example 7: Subtle Topic Drift",
            "Example 8: Hybrid Mode",
            "Example 9: Extended Rant",
        ]:
            with self.subTest(label=label):
                self.assertIn(label, MARKDOWN_SYSTEM_PROMPT)

    def test_prompt_contains_catch_all_rule(self):
        self.assertIn("Catch-All (Unstructured/Long-form)", MARKDOWN_SYSTEM_PROMPT)

    def test_prompt_contains_core_rules(self):
        for rule in [
            "Topic Segmentation",
            "Technical Precision",
            "Lists & Steps",
            "Philosophical/Abstract Mode",
            "Clean Up",
        ]:
            with self.subTest(rule=rule):
                self.assertIn(rule, MARKDOWN_SYSTEM_PROMPT)


class TestCodeFenceStripping(unittest.TestCase):
    """Verify wrapping code fences are removed from LLM output."""

    def test_strip_markdown_fence(self):
        raw = "```markdown\n## Hello\nWorld\n```"
        result = MarkdownFormatter._strip_code_fence(raw)
        self.assertEqual(result, "## Hello\nWorld")

    def test_strip_plain_fence(self):
        raw = "```\n## Hello\nWorld\n```"
        result = MarkdownFormatter._strip_code_fence(raw)
        self.assertEqual(result, "## Hello\nWorld")

    def test_no_fence_unchanged(self):
        raw = "## Hello\nWorld"
        result = MarkdownFormatter._strip_code_fence(raw)
        self.assertEqual(result, "## Hello\nWorld")

    def test_fence_with_trailing_whitespace(self):
        raw = "```md\n## Title\n```  "
        result = MarkdownFormatter._strip_code_fence(raw)
        self.assertEqual(result, "## Title")


class TestOllamaUnavailable(unittest.TestCase):
    """Formatter falls back gracefully when Ollama is unreachable."""

    def test_ollama_unavailable_returns_original(self):
        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        # Force the availability check to fail.
        fmt._ollama_available_checked = True
        fmt._ollama_available = False

        text = "raw transcript text"
        self.assertEqual(fmt.format(text), text)


class TestSuccessfulFormatting(unittest.TestCase):
    """Verify end-to-end formatting with a mocked Ollama response."""

    @patch("whisper_local.processing.markdown_formatter.request.urlopen")
    def test_formats_text_via_ollama(self, mock_urlopen):
        formatted_md = "## Backend Issues\n* **Latency** is too high."
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": formatted_md}
        ).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        fmt._ollama_available_checked = True
        fmt._ollama_available = True

        result = fmt.format("latency is too high on the backend")
        self.assertEqual(result, formatted_md)

    @patch("whisper_local.processing.markdown_formatter.request.urlopen")
    def test_strips_code_fence_from_response(self, mock_urlopen):
        formatted_md = "```markdown\n## Title\nBody text\n```"
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": formatted_md}
        ).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        fmt._ollama_available_checked = True
        fmt._ollama_available = True

        result = fmt.format("some transcript")
        self.assertEqual(result, "## Title\nBody text")


class TestErrorFallback(unittest.TestCase):
    """Verify formatter returns original text on LLM errors."""

    @patch("whisper_local.processing.markdown_formatter.request.urlopen")
    def test_timeout_returns_original(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("request timed out")

        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        fmt._ollama_available_checked = True
        fmt._ollama_available = True

        text = "original transcript"
        self.assertEqual(fmt.format(text), text)

    @patch("whisper_local.processing.markdown_formatter.request.urlopen")
    def test_empty_response_returns_original(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"response": ""}
        ).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        fmt = MarkdownFormatter()
        fmt.set_enabled(True)
        fmt._ollama_available_checked = True
        fmt._ollama_available = True

        text = "original transcript"
        self.assertEqual(fmt.format(text), text)


class TestPipelineIntegration(unittest.TestCase):
    """Verify markdown formatter integrates with PostProcessingPipeline."""

    def test_pipeline_config_has_markdown_fields(self):
        from whisper_local.processing.post_processor import PipelineConfig

        cfg = PipelineConfig()
        self.assertFalse(cfg.enable_markdown)
        self.assertEqual(cfg.markdown_model, "llama3.2:3b")

    def test_pipeline_disabled_markdown_passthrough(self):
        from whisper_local.processing.post_processor import (
            PipelineConfig,
            PostProcessingPipeline,
        )

        cfg = PipelineConfig(
            enable_numeric=False,
            enable_punctuation=False,
            enable_domain=False,
            enable_code_mode=False,
            enable_homophone=False,
            enable_final_sanitizer=False,
            enable_markdown=False,
        )
        pipeline = PostProcessingPipeline(cfg)
        text = "simple text"
        out, diff = pipeline.process(text)
        self.assertEqual(out, text)
        self.assertEqual(diff, "")

    def test_pipeline_step_times_include_markdown(self):
        from whisper_local.processing.post_processor import (
            PipelineConfig,
            PostProcessingPipeline,
        )

        cfg = PipelineConfig(
            enable_numeric=False,
            enable_punctuation=False,
            enable_domain=False,
            enable_code_mode=False,
            enable_homophone=False,
            enable_final_sanitizer=False,
            enable_markdown=False,
        )
        pipeline = PostProcessingPipeline(cfg)
        result = pipeline.process_with_details("hello")
        self.assertIn("markdown_formatter", result.step_times_ms)


if __name__ == "__main__":
    unittest.main()
