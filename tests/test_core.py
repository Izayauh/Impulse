"""
Unit tests for WhisperLocal core functionality.

Run with: python -m pytest tests/test_core.py -v
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class TestSanitizeTranscript(unittest.TestCase):
    """Tests for sanitize_transcript function."""
    
    def setUp(self):
        """Import the function under test."""
        # Import here to avoid module-level side effects
        from whisper_local.flow_local_dictation import sanitize_transcript
        self.sanitize = sanitize_transcript
    
    def test_empty_input(self):
        """Empty input returns empty string."""
        self.assertEqual(self.sanitize(""), "")
        self.assertEqual(self.sanitize(None), "")
    
    def test_basic_text(self):
        """Basic text passes through unchanged."""
        text = "Hello, this is a test transcription."
        self.assertEqual(self.sanitize(text), text)
    
    def test_removes_blank_audio(self):
        """BLANK_AUDIO tokens are removed."""
        text = "[BLANK_AUDIO] Hello world [BLANK_AUDIO]"
        result = self.sanitize(text)
        self.assertNotIn("[BLANK_AUDIO]", result)
        self.assertIn("Hello world", result)
    
    def test_removes_warning_lines(self):
        """Lines starting with 'warning:' are removed."""
        text = "Warning: something went wrong\nActual transcript text"
        result = self.sanitize(text)
        self.assertNotIn("Warning:", result)
        self.assertIn("Actual transcript text", result)
    
    def test_removes_deprecation_notices(self):
        """Deprecation notices are removed."""
        text = "This is deprecated\nActual content"
        result = self.sanitize(text)
        self.assertNotIn("deprecated", result.lower())
        self.assertIn("Actual content", result)
    
    def test_removes_github_notices(self):
        """GitHub deprecation links are removed."""
        text = "See https://github.com/ggerganov/whisper.cpp for deprecation\nHello world"
        result = self.sanitize(text)
        self.assertNotIn("github.com", result)
        self.assertIn("Hello world", result)
    
    def test_removes_please_use_notices(self):
        """'Please use X instead' notices are removed."""
        text = "Please use whisper-cli.exe instead of main.exe\nTranscript here"
        result = self.sanitize(text)
        self.assertNotIn("Please use", result)
        self.assertIn("Transcript here", result)
    
    def test_preserves_multiline_content(self):
        """Multiple lines of actual content are preserved."""
        text = "Line one\nLine two\nLine three"
        result = self.sanitize(text)
        self.assertIn("Line one", result)
        self.assertIn("Line two", result)
        self.assertIn("Line three", result)
    
    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        text = "   Hello world   "
        result = self.sanitize(text)
        self.assertEqual(result, "Hello world")
    
    def test_handles_large_input(self):
        """Large inputs are truncated safely."""
        from whisper_local.flow_local_dictation import MAX_TRANSCRIPT_BYTES
        large_text = "A" * (MAX_TRANSCRIPT_BYTES + 1000)
        result = self.sanitize(large_text)
        self.assertLessEqual(len(result), MAX_TRANSCRIPT_BYTES)
    
    def test_handles_many_lines(self):
        """Many lines are handled safely."""
        from whisper_local.flow_local_dictation import MAX_TRANSCRIPT_LINES
        many_lines = "\n".join([f"Line {i}" for i in range(MAX_TRANSCRIPT_LINES + 100)])
        result = self.sanitize(many_lines)
        # Should complete without hanging
        self.assertIsInstance(result, str)

    def test_collapse_repetition_artifacts_removes_duplicate_sentences(self):
        """Consecutive duplicate long sentences are collapsed to one."""
        from whisper_local.flow_local_dictation import collapse_repetition_artifacts

        repeated = (
            "And I've heard about it in context to somebody who's studying for mechanical engineering, "
            "all the way to people who are just semi-professional soccer players and beyond. "
            "And I've heard about it in context to somebody who's studying for mechanical engineering, "
            "all the way to people who are just semi-professional soccer players and beyond. "
            "And I've heard about it in context to somebody who's studying for mechanical engineering, "
            "all the way to people who are just semi-professional soccer players and beyond."
        )

        result = collapse_repetition_artifacts(repeated)
        self.assertEqual(result.count("And I've heard about it in context"), 1)

    def test_collapse_repetition_artifacts_preserves_short_repeats(self):
        """Short intentional repeats are preserved to avoid over-cleaning."""
        from whisper_local.flow_local_dictation import collapse_repetition_artifacts

        text = "Okay. Okay."
        result = collapse_repetition_artifacts(text)
        self.assertEqual(result, text)


class TestStatsTracker(unittest.TestCase):
    """Tests for StatsTracker class."""
    
    def setUp(self):
        """Create a temporary stats file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, "test_stats.json")

        # Create fresh tracker with explicit stats file
        from whisper_local.stats import StatsTracker
        self.tracker = StatsTracker(self.stats_file)
    
    def tearDown(self):
        """Cleanup temp files."""
        if os.path.exists(self.stats_file):
            os.remove(self.stats_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_initial_stats(self):
        """New tracker has default stats."""
        self.assertEqual(self.tracker.data["total_words"], 0)
        self.assertEqual(self.tracker.data["total_sessions"], 0)
        self.assertEqual(self.tracker.data["streak"], 0)
    
    def test_record_transcription(self):
        """Recording transcription updates stats correctly."""
        self.tracker.record_transcription("Hello world test", "base.en")

        self.assertEqual(self.tracker.data["total_words"], 3)
        self.assertEqual(self.tracker.data["total_sessions"], 1)
        self.assertEqual(self.tracker.data["model_usage"]["base.en"], 1)

    def test_record_transcription_with_wpm(self):
        """Recording transcription with duration calculates WPM correctly."""
        # 10 words in 12 seconds = 50 WPM
        self.tracker.record_transcription("This is a test with ten words in the sentence", "base.en", 12.0)

        self.assertEqual(self.tracker.data["total_words"], 10)
        self.assertEqual(self.tracker.data["total_sessions"], 1)
        self.assertEqual(self.tracker.data["best_wpm"], 50)
        self.assertEqual(len(self.tracker.data["wpm_history"]), 1)
        self.assertEqual(self.tracker.data["wpm_history"][0], 50)

        # Check summary includes WPM data
        summary = self.tracker.get_summary()
        self.assertEqual(summary["avg_wpm"], 50)
        self.assertEqual(summary["best_wpm"], 50)
    
    def test_record_empty_transcription(self):
        """Empty transcription is ignored."""
        self.tracker.record_transcription("", "base.en")
        
        self.assertEqual(self.tracker.data["total_words"], 0)
        self.assertEqual(self.tracker.data["total_sessions"], 0)
    
    def test_get_today_words(self):
        """Today's word count is tracked correctly."""
        self.tracker.record_transcription("One two three", "base.en")
        self.assertEqual(self.tracker.get_today_words(), 3)
    
    def test_get_week_words(self):
        """Week word count is calculated correctly."""
        self.tracker.record_transcription("One two three four five", "base.en")
        week_words = self.tracker.get_week_words()
        self.assertGreaterEqual(week_words, 5)
    
    def test_streak_calculation(self):
        """Streak is calculated correctly for consecutive days."""
        # First use starts streak at 1
        self.tracker.record_transcription("Hello", "base.en")
        self.assertEqual(self.tracker.data["streak"], 1)
    
    def test_milestones(self):
        """Milestones are awarded at correct thresholds."""
        # Generate enough words to hit 1K milestone
        for _ in range(100):
            self.tracker.record_transcription("word " * 11, "base.en")  # 11 words per iteration
        
        self.assertIn("1K Words", self.tracker.data["milestones"])
    
    def test_recent_transcripts(self):
        """Recent transcripts are stored correctly."""
        self.tracker.record_transcription("First transcript", "base.en")
        self.tracker.record_transcription("Second transcript", "base.en")
        
        self.assertEqual(len(self.tracker.data["recent_transcripts"]), 2)
        # Most recent is first
        self.assertIn("Second", self.tracker.data["recent_transcripts"][0]["text"])
    
    def test_recent_transcripts_limit(self):
        """Only last 5 transcripts are kept."""
        for i in range(10):
            self.tracker.record_transcription(f"Transcript number {i}", "base.en")
        
        self.assertEqual(len(self.tracker.data["recent_transcripts"]), 5)
    
    def test_model_usage_tracking(self):
        """Model usage is tracked per model type."""
        self.tracker.record_transcription("Test one", "base.en")
        self.tracker.record_transcription("Test two", "medium.en")
        self.tracker.record_transcription("Test three", "large-v3")
        
        self.assertEqual(self.tracker.data["model_usage"]["base.en"], 1)
        self.assertEqual(self.tracker.data["model_usage"]["medium.en"], 1)
        self.assertEqual(self.tracker.data["model_usage"]["large-v3"], 1)
    
    def test_persistence(self):
        """Stats are persisted to file."""
        self.tracker.record_transcription("Persistent test", "base.en")
        
        # Check file exists
        self.assertTrue(os.path.exists(self.stats_file))
        
        # Reload and verify
        with open(self.stats_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data["total_words"], 2)

    def test_load_sanitizes_implausible_wpm_history(self):
        """Legacy outlier WPM values are removed on load."""
        bad_payload = {
            "total_words": 50,
            "total_sessions": 3,
            "daily_words": {},
            "model_usage": {},
            "recent_transcripts": [],
            "milestones": [],
            "streak": 0,
            "last_use_date": None,
            "wpm_history": [45, 700, 120, 999],
            "best_wpm": 999,
        }
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(bad_payload, f)

        from whisper_local.stats import StatsTracker
        tracker = StatsTracker(self.stats_file)
        self.assertEqual(tracker.data["wpm_history"], [45, 120])
        self.assertEqual(tracker.data["best_wpm"], 120)


class TestModelSelection(unittest.TestCase):
    """Tests for model selection logic."""
    
    def test_word_thresholds_defined(self):
        """Word thresholds are properly defined."""
        from whisper_local.flow_local_dictation import WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM
        
        self.assertIsInstance(WORD_THRESHOLD_BASE, int)
        self.assertIsInstance(WORD_THRESHOLD_MEDIUM, int)
        self.assertLess(WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM)
    
    def test_model_paths_defined(self):
        """Model paths are properly defined."""
        from whisper_local.flow_local_dictation import MODEL_BASE, MODEL_MEDIUM, MODEL_LARGE
        
        self.assertIn("base", MODEL_BASE)
        self.assertIn("medium", MODEL_MEDIUM)
        self.assertIn("large", MODEL_LARGE)


class TestPathResolution(unittest.TestCase):
    """Tests for path resolution functions."""
    
    def test_get_bundle_dir(self):
        """Bundle directory is a valid path."""
        from whisper_local.flow_local_dictation import get_bundle_dir
        bundle_dir = get_bundle_dir()
        
        self.assertIsInstance(bundle_dir, str)
        self.assertTrue(os.path.isabs(bundle_dir))
    
    def test_get_app_dir(self):
        """App directory is a valid path."""
        from whisper_local.flow_local_dictation import get_app_dir
        app_dir = get_app_dir()
        
        self.assertIsInstance(app_dir, str)
        self.assertTrue(os.path.isabs(app_dir))
    
    def test_get_user_data_dir(self):
        """User data directory is a valid path."""
        from whisper_local.flow_local_dictation import get_user_data_dir
        user_dir = get_user_data_dir()
        
        self.assertIsInstance(user_dir, str)
        self.assertTrue(os.path.isabs(user_dir))
    
    def test_is_frozen(self):
        """is_frozen returns correct value in dev mode."""
        from whisper_local.flow_local_dictation import is_frozen
        # In test environment, should not be frozen
        self.assertFalse(is_frozen())


class TestTextPostProcessing(unittest.TestCase):
    """Tests for text post-processing functions."""
    
    def test_scrub_fillers(self):
        """Filler words are removed correctly."""
        from whisper_local.flow_local_dictation import scrub_fillers
        
        text = "um I think uh you know that's kind of like interesting"
        result = scrub_fillers(text)
        
        self.assertNotIn("um", result.lower())
        self.assertNotIn("uh", result.lower())
        self.assertIn("interesting", result)
    
    def test_apply_commands(self):
        """Voice commands are applied correctly."""
        from whisper_local.flow_local_dictation import apply_commands
        
        text = "Hello new line world"
        result = apply_commands(text)
        
        self.assertIn("\n", result)
    
    def test_to_bullets(self):
        """Text with a bullet trigger is converted to bullet list."""
        from whisper_local.flow_local_dictation import to_bullets

        # to_bullets only activates when a trigger word is present
        text = "make a list apples and oranges and bananas"
        result = to_bullets(text)

        self.assertIn("\u2022", result)
        self.assertIn("apples", result.lower())

    def test_to_bullets_no_trigger(self):
        """Text WITHOUT a trigger keyword is returned unchanged."""
        from whisper_local.flow_local_dictation import to_bullets

        text = "apples and oranges and bananas"
        result = to_bullets(text)

        self.assertEqual(result, text)


class TestVocabularyPostProcessing(unittest.TestCase):
    """Tests for vocabulary-backed deterministic replacements."""

    def test_apply_vocabulary_corrections_handles_punctuation_terms(self):
        from whisper_local.flow_local_dictation import apply_vocabulary_corrections

        with patch("whisper_local.flow_local_dictation.load_vocabulary", return_value=["C++"]):
            result = apply_vocabulary_corrections("c + + C + + C++17")

        self.assertEqual(result, "c++ C++ C++17")

    def test_apply_vocabulary_corrections_preserves_case_style(self):
        from whisper_local.flow_local_dictation import apply_vocabulary_corrections

        with patch("whisper_local.flow_local_dictation.load_vocabulary", return_value=["Ableton Live"]):
            result = apply_vocabulary_corrections("ABLETON   LIVE ableton   live Ableton   Live")

        self.assertEqual(result, "ABLETON LIVE ableton live Ableton Live")

    def test_postprocess_runs_vocabulary_stage_before_domain_passes(self):
        from whisper_local.flow_local_dictation import postprocess

        class PreserveCaseContext:
            app_type = "unit-test"

            def should_preserve_casing(self):
                return True

            def is_casual_context(self):
                return False

        observed = {"fix_ip_input": None}

        def _capture_fix_ip_input(text):
            observed["fix_ip_input"] = text
            return text

        with patch("whisper_local.flow_local_dictation.load_vocabulary", return_value=["C++"]):
            with patch("whisper_local.flow_local_dictation.fix_ip_addresses", side_effect=_capture_fix_ip_input):
                postprocess("c + +", context=PreserveCaseContext())

        self.assertEqual(observed["fix_ip_input"], "c++")


class TestFuzzyVocabularyMatching(unittest.TestCase):
    """Tests for fuzzy vocabulary matching (pass 2)."""

    def test_fuzzy_catches_word_splitting(self):
        """Whisper splitting 'Ableton' into 'able ton' is corrected."""
        from whisper_local.flow_local_dictation import _fuzzy_vocabulary_pass

        result = _fuzzy_vocabulary_pass("open able ton live", ["Ableton Live"])
        # "able ton live" concatenated = "abletonlive" matches "abletonlive"
        self.assertIn("ableton live", result.lower())

    def test_fuzzy_catches_minor_misspelling(self):
        """Near-miss single word spelling is corrected."""
        from whisper_local.flow_local_dictation import _fuzzy_vocabulary_pass

        # "Isaih" is close enough to "Isaiah" (1 char swap)
        result = _fuzzy_vocabulary_pass("hello Isaih", ["Isaiah"])
        self.assertIn("Isaiah", result)

    def test_fuzzy_catches_split_compound(self):
        """Whisper splitting a compound word is corrected via expanded window."""
        from whisper_local.flow_local_dictation import _fuzzy_vocabulary_pass

        # "bid fta" split from "BidFTA" - concat "bidfta" matches
        # Case style: input is lowercase so output preserves lowercase.
        result = _fuzzy_vocabulary_pass("open bid fta now", ["BidFTA"])
        self.assertIn("bidfta", result.lower())

    def test_fuzzy_skips_exact_matches(self):
        """Words already matching exactly are not double-processed."""
        from whisper_local.flow_local_dictation import _fuzzy_vocabulary_pass

        result = _fuzzy_vocabulary_pass("hello Isaiah", ["Isaiah"])
        self.assertEqual(result, "hello Isaiah")

    def test_fuzzy_does_not_false_positive(self):
        """Dissimilar words are not replaced."""
        from whisper_local.flow_local_dictation import _fuzzy_vocabulary_pass

        result = _fuzzy_vocabulary_pass("the weather is nice today", ["Isaiah"])
        self.assertNotIn("Isaiah", result)
        self.assertIn("weather", result)

    def test_fuzzy_multiword_priority(self):
        """Longer multi-word vocab terms get priority over shorter ones."""
        from whisper_local.flow_local_dictation import _fuzzy_vocabulary_pass

        # "whisper locale directory" is close to "Whisper Local Directory"
        # Case style: input is all lowercase, so output preserves lowercase.
        result = _fuzzy_vocabulary_pass(
            "check the whisper locale directory",
            ["Whisper Local", "Whisper Local Directory"],
        )
        self.assertIn("whisper local directory", result.lower())

    def test_full_pipeline_with_fuzzy(self):
        """End-to-end: apply_vocabulary_corrections uses both passes."""
        from whisper_local.flow_local_dictation import apply_vocabulary_corrections

        with patch(
            "whisper_local.flow_local_dictation.load_vocabulary",
            return_value=["Ableton Live"],
        ):
            # Whisper splits "Ableton" into "able ton"
            result = apply_vocabulary_corrections("open able ton live")
        self.assertIn("ableton live", result.lower())


class TestFuzzySnippetMatching(unittest.TestCase):
    """Tests for fuzzy snippet trigger matching."""

    def test_fuzzy_catches_near_miss_trigger(self):
        from whisper_local.snippets import _fuzzy_snippet_pass

        items = [{"trigger": "BidFTA Directory", "replacement": "C:\\path\\to\\bidfta"}]
        result = _fuzzy_snippet_pass("check the bid FTA directory", items)
        self.assertIn("C:\\path\\to\\bidfta", result)

    def test_fuzzy_does_not_false_positive(self):
        from whisper_local.snippets import _fuzzy_snippet_pass

        items = [{"trigger": "BidFTA Directory", "replacement": "C:\\path\\to\\bidfta"}]
        result = _fuzzy_snippet_pass("the weather is nice today", items)
        self.assertNotIn("C:\\path\\to\\bidfta", result)

    def test_fuzzy_skips_exact_match(self):
        from whisper_local.snippets import _fuzzy_snippet_pass

        items = [{"trigger": "hello world", "replacement": "replaced"}]
        # Exact match should be skipped (handled by pass 1).
        result = _fuzzy_snippet_pass("hello world", items)
        self.assertEqual(result, "hello world")

    def test_full_apply_snippets_with_fuzzy(self):
        """End-to-end: apply_snippets uses both exact and fuzzy passes."""
        from whisper_local.snippets import apply_snippets

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(
                {"snippets": [{"id": 1, "trigger": "Jarvis Ableton", "replacement": "C:\\JarvisAbleton"}]},
                f,
            )
            path = f.name
        try:
            # Exact match
            result = apply_snippets("open Jarvis Ableton", path)
            self.assertIn("C:\\JarvisAbleton", result)

            # Fuzzy match (Whisper mishearing)
            result = apply_snippets("open jarvis able ton", path)
            self.assertIn("C:\\JarvisAbleton", result)
        finally:
            os.remove(path)


class TestConfigValidation(unittest.TestCase):
    """Tests for configuration validation."""

    def test_sample_rate_valid(self):
        """Sample rate is a valid audio rate."""
        from whisper_local.flow_local_dictation import SAMPLE_RATE
        
        self.assertIn(SAMPLE_RATE, [8000, 16000, 22050, 44100, 48000])
    
    def test_channels_valid(self):
        """Channel count is valid."""
        from whisper_local.flow_local_dictation import CHANNELS
        
        self.assertIn(CHANNELS, [1, 2])
    
    def test_timeout_reasonable(self):
        """Timeout is a reasonable value."""
        from whisper_local.flow_local_dictation import WHISPER_TIMEOUT_SEC
        
        self.assertGreater(WHISPER_TIMEOUT_SEC, 10)
        self.assertLess(WHISPER_TIMEOUT_SEC, 600)


class TestInputValidationConstants(unittest.TestCase):
    """Tests for input validation constants."""
    
    def test_max_transcript_bytes(self):
        """Max transcript bytes is reasonable."""
        from whisper_local.flow_local_dictation import MAX_TRANSCRIPT_BYTES
        
        self.assertGreater(MAX_TRANSCRIPT_BYTES, 0)
        self.assertLessEqual(MAX_TRANSCRIPT_BYTES, 10 * 1024 * 1024)  # Max 10MB
    
    def test_max_transcript_lines(self):
        """Max transcript lines is reasonable."""
        from whisper_local.flow_local_dictation import MAX_TRANSCRIPT_LINES
        
        self.assertGreater(MAX_TRANSCRIPT_LINES, 0)
        self.assertLessEqual(MAX_TRANSCRIPT_LINES, 100000)
    
    def test_max_line_length(self):
        """Max line length is reasonable."""
        from whisper_local.flow_local_dictation import MAX_LINE_LENGTH
        
        self.assertGreater(MAX_LINE_LENGTH, 0)
        self.assertLessEqual(MAX_LINE_LENGTH, 100000)


if __name__ == "__main__":
    unittest.main()
