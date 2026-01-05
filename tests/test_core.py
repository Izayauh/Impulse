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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSanitizeTranscript(unittest.TestCase):
    """Tests for sanitize_transcript function."""
    
    def setUp(self):
        """Import the function under test."""
        # Import here to avoid module-level side effects
        from flow_local_dictation import sanitize_transcript
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
        from flow_local_dictation import MAX_TRANSCRIPT_BYTES
        large_text = "A" * (MAX_TRANSCRIPT_BYTES + 1000)
        result = self.sanitize(large_text)
        self.assertLessEqual(len(result), MAX_TRANSCRIPT_BYTES)
    
    def test_handles_many_lines(self):
        """Many lines are handled safely."""
        from flow_local_dictation import MAX_TRANSCRIPT_LINES
        many_lines = "\n".join([f"Line {i}" for i in range(MAX_TRANSCRIPT_LINES + 100)])
        result = self.sanitize(many_lines)
        # Should complete without hanging
        self.assertIsInstance(result, str)


class TestStatsTracker(unittest.TestCase):
    """Tests for StatsTracker class."""
    
    def setUp(self):
        """Create a temporary stats file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.temp_dir, "test_stats.json")
        
        # Patch the STATS_FILE constant
        import flow_local_dictation
        self.original_stats_file = flow_local_dictation.STATS_FILE
        flow_local_dictation.STATS_FILE = self.stats_file
        
        # Create fresh tracker
        from flow_local_dictation import StatsTracker
        self.tracker = StatsTracker()
    
    def tearDown(self):
        """Restore original STATS_FILE and cleanup."""
        import flow_local_dictation
        flow_local_dictation.STATS_FILE = self.original_stats_file
        
        # Cleanup temp files
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
        
        self.assertIn("1K", self.tracker.data["milestones"])
    
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


class TestModelSelection(unittest.TestCase):
    """Tests for model selection logic."""
    
    def test_word_thresholds_defined(self):
        """Word thresholds are properly defined."""
        from flow_local_dictation import WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM
        
        self.assertIsInstance(WORD_THRESHOLD_BASE, int)
        self.assertIsInstance(WORD_THRESHOLD_MEDIUM, int)
        self.assertLess(WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM)
    
    def test_model_paths_defined(self):
        """Model paths are properly defined."""
        from flow_local_dictation import MODEL_BASE, MODEL_MEDIUM, MODEL_LARGE
        
        self.assertIn("base", MODEL_BASE)
        self.assertIn("medium", MODEL_MEDIUM)
        self.assertIn("large", MODEL_LARGE)


class TestPathResolution(unittest.TestCase):
    """Tests for path resolution functions."""
    
    def test_get_bundle_dir(self):
        """Bundle directory is a valid path."""
        from flow_local_dictation import get_bundle_dir
        bundle_dir = get_bundle_dir()
        
        self.assertIsInstance(bundle_dir, str)
        self.assertTrue(os.path.isabs(bundle_dir))
    
    def test_get_app_dir(self):
        """App directory is a valid path."""
        from flow_local_dictation import get_app_dir
        app_dir = get_app_dir()
        
        self.assertIsInstance(app_dir, str)
        self.assertTrue(os.path.isabs(app_dir))
    
    def test_get_user_data_dir(self):
        """User data directory is a valid path."""
        from flow_local_dictation import get_user_data_dir
        user_dir = get_user_data_dir()
        
        self.assertIsInstance(user_dir, str)
        self.assertTrue(os.path.isabs(user_dir))
    
    def test_is_frozen(self):
        """is_frozen returns correct value in dev mode."""
        from flow_local_dictation import is_frozen
        # In test environment, should not be frozen
        self.assertFalse(is_frozen())


class TestTextPostProcessing(unittest.TestCase):
    """Tests for text post-processing functions."""
    
    def test_scrub_fillers(self):
        """Filler words are removed correctly."""
        from flow_local_dictation import scrub_fillers
        
        text = "um I think uh you know that's kind of like interesting"
        result = scrub_fillers(text)
        
        self.assertNotIn("um", result.lower())
        self.assertNotIn("uh", result.lower())
        self.assertIn("interesting", result)
    
    def test_apply_commands(self):
        """Voice commands are applied correctly."""
        from flow_local_dictation import apply_commands
        
        text = "Hello new line world"
        result = apply_commands(text)
        
        self.assertIn("\n", result)
    
    def test_to_bullets(self):
        """Text is converted to bullet list."""
        from flow_local_dictation import to_bullets
        
        text = "apples and oranges and bananas"
        result = to_bullets(text)
        
        self.assertIn("-", result)


class TestConfigValidation(unittest.TestCase):
    """Tests for configuration validation."""
    
    def test_sample_rate_valid(self):
        """Sample rate is a valid audio rate."""
        from flow_local_dictation import SAMPLE_RATE
        
        self.assertIn(SAMPLE_RATE, [8000, 16000, 22050, 44100, 48000])
    
    def test_channels_valid(self):
        """Channel count is valid."""
        from flow_local_dictation import CHANNELS
        
        self.assertIn(CHANNELS, [1, 2])
    
    def test_timeout_reasonable(self):
        """Timeout is a reasonable value."""
        from flow_local_dictation import WHISPER_TIMEOUT_SEC
        
        self.assertGreater(WHISPER_TIMEOUT_SEC, 10)
        self.assertLess(WHISPER_TIMEOUT_SEC, 600)


class TestInputValidationConstants(unittest.TestCase):
    """Tests for input validation constants."""
    
    def test_max_transcript_bytes(self):
        """Max transcript bytes is reasonable."""
        from flow_local_dictation import MAX_TRANSCRIPT_BYTES
        
        self.assertGreater(MAX_TRANSCRIPT_BYTES, 0)
        self.assertLessEqual(MAX_TRANSCRIPT_BYTES, 10 * 1024 * 1024)  # Max 10MB
    
    def test_max_transcript_lines(self):
        """Max transcript lines is reasonable."""
        from flow_local_dictation import MAX_TRANSCRIPT_LINES
        
        self.assertGreater(MAX_TRANSCRIPT_LINES, 0)
        self.assertLessEqual(MAX_TRANSCRIPT_LINES, 100000)
    
    def test_max_line_length(self):
        """Max line length is reasonable."""
        from flow_local_dictation import MAX_LINE_LENGTH
        
        self.assertGreater(MAX_LINE_LENGTH, 0)
        self.assertLessEqual(MAX_LINE_LENGTH, 100000)


if __name__ == "__main__":
    unittest.main()

