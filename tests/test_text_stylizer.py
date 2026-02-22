"""Unit tests for the text_stylizer module."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.text_stylizer import (
    PROFILE_ORDER,
    PROFILES,
    TextStylizer,
    next_profile,
)


# ---------------------------------------------------------------------------
# next_profile() cycling
# ---------------------------------------------------------------------------

class TestNextProfile:
    def test_cycles_through_all(self):
        current = "off"
        visited = [current]
        for _ in range(len(PROFILE_ORDER) - 1):
            current = next_profile(current)
            visited.append(current)
        assert visited == PROFILE_ORDER

    def test_wraps_around(self):
        assert next_profile("technical") == "off"

    def test_unknown_defaults_to_first(self):
        assert next_profile("nonexistent") == "off"


# ---------------------------------------------------------------------------
# Profile definitions sanity
# ---------------------------------------------------------------------------

class TestProfileDefinitions:
    def test_all_profiles_have_required_keys(self):
        for name, profile in PROFILES.items():
            assert "prompt" in profile, f"Profile '{name}' missing 'prompt'"
            assert "label" in profile, f"Profile '{name}' missing 'label'"
            assert "description" in profile, f"Profile '{name}' missing 'description'"

    def test_profile_order_matches_profiles_dict(self):
        assert set(PROFILE_ORDER) == set(PROFILES.keys())

    def test_off_has_empty_prompt(self):
        assert PROFILES["off"]["prompt"] == ""


# ---------------------------------------------------------------------------
# TextStylizer.stylize()
# ---------------------------------------------------------------------------

class TestStylize:
    def test_off_returns_unchanged(self):
        s = TextStylizer()
        assert s.stylize("hello world", "off") == "hello world"

    def test_empty_text_returns_unchanged(self):
        s = TextStylizer()
        assert s.stylize("", "clean") == ""

    def test_whitespace_only_returns_unchanged(self):
        s = TextStylizer()
        assert s.stylize("   ", "clean") == "   "

    def test_unknown_profile_returns_unchanged(self):
        s = TextStylizer()
        assert s.stylize("hello", "nonexistent") == "hello"

    @patch("whisper_local.processing.text_stylizer.request.urlopen")
    def test_ollama_unavailable_returns_unchanged(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("connection refused")
        s = TextStylizer()
        result = s.stylize("um yeah so it works", "clean")
        assert result == "um yeah so it works"

    @patch("whisper_local.processing.text_stylizer.request.urlopen")
    def test_successful_stylization(self, mock_urlopen):
        # First call: availability check (GET /api/tags)
        tags_resp = MagicMock()
        tags_resp.__enter__ = MagicMock(return_value=tags_resp)
        tags_resp.__exit__ = MagicMock(return_value=False)

        # Second call: generation (POST /api/generate)
        gen_resp = MagicMock()
        gen_resp.__enter__ = MagicMock(return_value=gen_resp)
        gen_resp.__exit__ = MagicMock(return_value=False)
        gen_resp.read.return_value = json.dumps(
            {"response": "It works."}
        ).encode("utf-8")

        mock_urlopen.side_effect = [tags_resp, gen_resp]

        s = TextStylizer()
        result = s.stylize("um yeah so it works", "clean")
        assert result == "It works."

    @patch("whisper_local.processing.text_stylizer.request.urlopen")
    def test_empty_llm_response_returns_original(self, mock_urlopen):
        tags_resp = MagicMock()
        tags_resp.__enter__ = MagicMock(return_value=tags_resp)
        tags_resp.__exit__ = MagicMock(return_value=False)

        gen_resp = MagicMock()
        gen_resp.__enter__ = MagicMock(return_value=gen_resp)
        gen_resp.__exit__ = MagicMock(return_value=False)
        gen_resp.read.return_value = json.dumps({"response": ""}).encode("utf-8")

        mock_urlopen.side_effect = [tags_resp, gen_resp]

        s = TextStylizer()
        result = s.stylize("hello world", "formal")
        assert result == "hello world"


# ---------------------------------------------------------------------------
# reset_availability()
# ---------------------------------------------------------------------------

class TestResetAvailability:
    def test_reset_clears_cache(self):
        s = TextStylizer()
        s._ollama_available_checked = True
        s._ollama_available = False
        s.reset_availability()
        assert s._ollama_available_checked is False
        assert s._ollama_available is False
