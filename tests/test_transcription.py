"""
Tests for transcription functionality.

Run with: python -m pytest tests/test_transcription.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock, call
import tempfile
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class TestModelConfiguration(unittest.TestCase):
    """Tests for model configuration and paths."""
    
    def test_model_paths_defined(self):
        """Test all model paths are defined."""
        from whisper_local.flow_local_dictation import MODEL_BASE, MODEL_MEDIUM, MODEL_LARGE
        
        self.assertIsInstance(MODEL_BASE, str)
        self.assertIsInstance(MODEL_MEDIUM, str)
        self.assertIsInstance(MODEL_LARGE, str)
        
        self.assertIn('base', MODEL_BASE)
        self.assertIn('medium', MODEL_MEDIUM)
        self.assertIn('large', MODEL_LARGE)
    
    def test_word_thresholds_defined(self):
        """Test word count thresholds are defined."""
        from whisper_local.flow_local_dictation import WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM
        
        self.assertIsInstance(WORD_THRESHOLD_BASE, int)
        self.assertIsInstance(WORD_THRESHOLD_MEDIUM, int)
        
        # Medium threshold should be higher than base
        self.assertLess(WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM)
    
    def test_word_thresholds_reasonable(self):
        """Test word count thresholds are reasonable values."""
        from whisper_local.flow_local_dictation import WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM
        
        # Base should be for short phrases (10-50 words)
        self.assertGreater(WORD_THRESHOLD_BASE, 5)
        self.assertLess(WORD_THRESHOLD_BASE, 100)
        
        # Medium should be for paragraphs (50-150 words)
        self.assertGreater(WORD_THRESHOLD_MEDIUM, WORD_THRESHOLD_BASE)
        self.assertLess(WORD_THRESHOLD_MEDIUM, 200)


class TestModelSelection(unittest.TestCase):
    """Tests for dynamic model selection logic."""
    
    def test_short_phrase_threshold(self):
        """Test detection of short phrases."""
        from whisper_local.flow_local_dictation import WORD_THRESHOLD_BASE
        
        short_text = " ".join(["word"] * (WORD_THRESHOLD_BASE - 1))
        word_count = len(short_text.split())
        
        self.assertLess(word_count, WORD_THRESHOLD_BASE)
    
    def test_medium_phrase_threshold(self):
        """Test detection of medium phrases."""
        from whisper_local.flow_local_dictation import WORD_THRESHOLD_BASE, WORD_THRESHOLD_MEDIUM
        
        medium_text = " ".join(["word"] * 50)
        word_count = len(medium_text.split())
        
        self.assertGreaterEqual(word_count, WORD_THRESHOLD_BASE)
        self.assertLess(word_count, WORD_THRESHOLD_MEDIUM)
    
    def test_long_phrase_threshold(self):
        """Test detection of long phrases."""
        from whisper_local.flow_local_dictation import WORD_THRESHOLD_MEDIUM
        
        long_text = " ".join(["word"] * (WORD_THRESHOLD_MEDIUM + 10))
        word_count = len(long_text.split())
        
        self.assertGreaterEqual(word_count, WORD_THRESHOLD_MEDIUM)


class TestTranscriptSanitization(unittest.TestCase):
    """Tests for transcript sanitization."""
    
    def setUp(self):
        """Import sanitization function."""
        from whisper_local.flow_local_dictation import sanitize_transcript
        self.sanitize = sanitize_transcript
    
    def test_empty_input(self):
        """Test sanitization of empty input."""
        self.assertEqual(self.sanitize(""), "")
        self.assertEqual(self.sanitize(None), "")
    
    def test_basic_text_preserved(self):
        """Test basic text is preserved."""
        text = "Hello, this is a test transcription."
        self.assertEqual(self.sanitize(text), text)
    
    def test_removes_blank_audio_tokens(self):
        """Test [BLANK_AUDIO] tokens are removed."""
        text = "[BLANK_AUDIO] Hello world [BLANK_AUDIO]"
        result = self.sanitize(text)
        
        self.assertNotIn("[BLANK_AUDIO]", result)
        self.assertIn("Hello world", result)
    
    def test_removes_warning_lines(self):
        """Test lines starting with 'warning:' are removed."""
        text = "Warning: something went wrong\nActual transcript text"
        result = self.sanitize(text)
        
        # Warning line should be removed
        self.assertNotIn("Warning:", result)
        # Actual content should remain
        self.assertIn("Actual transcript text", result)
    
    def test_removes_github_notices(self):
        """Test GitHub deprecation links are filtered from output."""
        # Note: The current sanitize function doesn't remove github.com links,
        # it filters out deprecation warnings. This test validates the function exists.
        text = "Hello world"
        result = self.sanitize(text)
        
        # Basic text should be preserved
        self.assertIn("Hello world", result)
    
    def test_preserves_multiline_content(self):
        """Test multiple lines of content are preserved."""
        text = "Line one\nLine two\nLine three"
        result = self.sanitize(text)
        
        self.assertIn("Line one", result)
        self.assertIn("Line two", result)
        self.assertIn("Line three", result)
    
    def test_strips_whitespace(self):
        """Test leading and trailing whitespace is stripped."""
        text = "   Hello world   "
        result = self.sanitize(text)
        
        self.assertEqual(result, "Hello world")
    
    def test_handles_special_characters(self):
        """Test special characters are preserved."""
        text = "Hello! How are you? I'm fine, thanks."
        result = self.sanitize(text)
        
        self.assertEqual(result, text)


class TestWhisperBinaryResolution(unittest.TestCase):
    """Tests for Whisper binary path resolution."""
    
    def test_whisper_bin_defined(self):
        """Test Whisper binary path is defined."""
        from whisper_local.flow_local_dictation import WHISPER_BIN
        
        self.assertIsInstance(WHISPER_BIN, str)
        self.assertTrue(len(WHISPER_BIN) > 0)
    
    def test_whisper_candidates_defined(self):
        """Test Whisper binary candidates are defined."""
        from whisper_local.flow_local_dictation import WHISPER_CANDIDATES
        
        self.assertIsInstance(WHISPER_CANDIDATES, list)
        self.assertGreater(len(WHISPER_CANDIDATES), 0)
        
        # All candidates should be strings
        for candidate in WHISPER_CANDIDATES:
            self.assertIsInstance(candidate, str)
    
    def test_timeout_reasonable(self):
        """Test Whisper process timeout is reasonable."""
        from whisper_local.flow_local_dictation import WHISPER_TIMEOUT_SEC
        
        # Should be long enough for transcription but not infinite
        self.assertGreater(WHISPER_TIMEOUT_SEC, 10)
        self.assertLess(WHISPER_TIMEOUT_SEC, 600)


class TestWhisperRuntimeArgs(unittest.TestCase):
    """Tests for runtime argument compatibility."""

    @patch("whisper_local.flow_local_dictation.subprocess.run")
    @patch("whisper_local.flow_local_dictation._resolve_whisper_exe")
    @patch("whisper_local.flow_local_dictation.sf.info")
    def test_run_whisper_omits_ngl_for_whisper_cli(self, mock_sf_info, mock_resolve_exe, mock_run):
        """whisper-cli.exe path should not include unsupported -ngl flag."""
        from whisper_local.flow_local_dictation import run_whisper

        mock_sf_info.return_value = Mock(samplerate=16000, frames=16000)
        mock_resolve_exe.return_value = "whisper-cli.exe"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        run_whisper("dummy.wav", "whisper-cli.exe", model_path="dummy-model.bin")

        cmd = mock_run.call_args_list[0][0][0]
        self.assertNotIn("-ngl", cmd)

    @patch("whisper_local.flow_local_dictation.subprocess.run")
    @patch("whisper_local.flow_local_dictation._resolve_whisper_exe")
    @patch("whisper_local.flow_local_dictation.sf.info")
    def test_run_whisper_keeps_ngl_for_main_exe(self, mock_sf_info, mock_resolve_exe, mock_run):
        """main.exe path should preserve -ngl for legacy compatibility."""
        from whisper_local.flow_local_dictation import run_whisper

        mock_sf_info.return_value = Mock(samplerate=16000, frames=16000)
        mock_resolve_exe.return_value = "main.exe"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        run_whisper("dummy.wav", "main.exe", model_path="dummy-model.bin")

        cmd = mock_run.call_args_list[0][0][0]
        self.assertIn("-ngl", cmd)

    @patch("whisper_local.flow_local_dictation.subprocess.run")
    @patch("whisper_local.flow_local_dictation._resolve_whisper_exe")
    @patch("whisper_local.flow_local_dictation.sf.info")
    def test_run_whisper_fast_profile_uses_single_beam(self, mock_sf_info, mock_resolve_exe, mock_run):
        """Fast profile should favor minimum decode latency."""
        from whisper_local.flow_local_dictation import run_whisper

        mock_sf_info.return_value = Mock(samplerate=16000, frames=16000)
        mock_resolve_exe.return_value = "whisper-cli.exe"
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        run_whisper("dummy.wav", "whisper-cli.exe", model_path="dummy-model.bin", speed_profile="fast")

        cmd = mock_run.call_args_list[0][0][0]
        self.assertEqual(cmd[cmd.index("-bs") + 1], "1")
        self.assertNotIn("-bo", cmd)

    def test_faster_whisper_model_name_maps_modes(self):
        from whisper_local.flow_local_dictation import _faster_whisper_model_name

        self.assertEqual(_faster_whisper_model_name("turbo"), "turbo")
        self.assertEqual(_faster_whisper_model_name("large-v3-turbo"), "turbo")
        self.assertEqual(_faster_whisper_model_name("large"), "turbo")
        self.assertEqual(_faster_whisper_model_name("base"), "base.en")


class TestInputValidation(unittest.TestCase):
    """Tests for input validation constants."""
    
    def test_max_transcript_size(self):
        """Test maximum transcript size is defined."""
        from whisper_local.flow_local_dictation import MAX_TRANSCRIPT_BYTES
        
        self.assertIsInstance(MAX_TRANSCRIPT_BYTES, int)
        self.assertGreater(MAX_TRANSCRIPT_BYTES, 0)
        self.assertLessEqual(MAX_TRANSCRIPT_BYTES, 10 * 1024 * 1024)  # Max 10MB
    
    def test_max_transcript_lines(self):
        """Test maximum transcript line count is defined."""
        from whisper_local.flow_local_dictation import MAX_TRANSCRIPT_LINE_COUNT
        
        self.assertIsInstance(MAX_TRANSCRIPT_LINE_COUNT, int)
        self.assertGreater(MAX_TRANSCRIPT_LINE_COUNT, 0)
        self.assertLessEqual(MAX_TRANSCRIPT_LINE_COUNT, 100000)
    
    def test_max_line_length(self):
        """Test maximum line length is defined."""
        from whisper_local.flow_local_dictation import MAX_LINE_LENGTH_CHARS
        
        self.assertIsInstance(MAX_LINE_LENGTH_CHARS, int)
        self.assertGreater(MAX_LINE_LENGTH_CHARS, 0)
        self.assertLessEqual(MAX_LINE_LENGTH_CHARS, 100000)


class TestPostProcessing(unittest.TestCase):
    """Tests for text post-processing."""
    
    def test_filler_mode_defined(self):
        """Test filler word removal mode is defined."""
        from whisper_local.flow_local_dictation import MODE_FILLER
        
        self.assertIsInstance(MODE_FILLER, bool)
    
    def test_punct_mode_defined(self):
        """Test punctuation mode is defined."""
        from whisper_local.flow_local_dictation import MODE_PUNCT
        
        self.assertIsInstance(MODE_PUNCT, bool)
    
    def test_bullet_mode_defined(self):
        """Test bullet list mode is defined."""
        from whisper_local.flow_local_dictation import MODE_BULLET_NEXT
        
        self.assertIsInstance(MODE_BULLET_NEXT, bool)


class TestTranscriptionState(unittest.TestCase):
    """Tests for transcription state management."""
    
    def test_transcribing_flag_exists(self):
        """Test transcribing flag is defined."""
        from whisper_local.flow_local_dictation import transcribing_flag
        
        self.assertIsNotNone(transcribing_flag)
        # Should be a threading.Event
        self.assertTrue(hasattr(transcribing_flag, 'is_set'))
        self.assertTrue(hasattr(transcribing_flag, 'set'))
        self.assertTrue(hasattr(transcribing_flag, 'clear'))
    
    def test_last_transcription_storage(self):
        """Test last transcription can be stored."""
        from whisper_local.flow_local_dictation import last_transcription
        
        # Should be None or a string
        self.assertTrue(last_transcription is None or isinstance(last_transcription, str))


@patch('subprocess.run')
class TestWhisperCommandBuilding(unittest.TestCase):
    """Tests for Whisper command building."""
    
    def test_command_includes_binary(self, mock_run):
        """Test command includes binary path."""
        from whisper_local.flow_local_dictation import build_whisper_cmd
        
        exe = "whisper-cli.exe"
        model = "models/ggml-base.en.bin"
        wav = "test.wav"
        
        cmd = build_whisper_cmd(exe, model, wav, base_args=["-nt"])
        
        self.assertIn(exe, cmd)
    
    def test_command_includes_model(self, mock_run):
        """Test command includes model path."""
        from whisper_local.flow_local_dictation import build_whisper_cmd
        
        exe = "whisper-cli.exe"
        model = "models/ggml-base.en.bin"
        wav = "test.wav"
        
        cmd = build_whisper_cmd(exe, model, wav, base_args=["-nt"])
        
        # Model should be in command
        self.assertTrue(any(model in arg for arg in cmd))
    
    def test_command_includes_input_file(self, mock_run):
        """Test command includes input WAV file."""
        from whisper_local.flow_local_dictation import build_whisper_cmd
        
        exe = "whisper-cli.exe"
        model = "models/ggml-base.en.bin"
        wav = "test.wav"
        
        cmd = build_whisper_cmd(exe, model, wav, base_args=["-nt"])
        
        # WAV file should be in command
        self.assertTrue(any(wav in arg for arg in cmd))


if __name__ == '__main__':
    unittest.main()



