"""
Tests for audio recording functionality.

Run with: python -m pytest tests/test_audio.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class TestAudioConfiguration(unittest.TestCase):
    """Tests for audio configuration constants."""
    
    def test_sample_rate_defined(self):
        """Test sample rate is properly defined."""
        from whisper_local.flow_local_dictation import SAMPLE_RATE_HZ
        
        self.assertEqual(SAMPLE_RATE_HZ, 16000)
        self.assertIsInstance(SAMPLE_RATE_HZ, int)
    
    def test_channels_defined(self):
        """Test audio channels are properly defined."""
        from whisper_local.flow_local_dictation import AUDIO_CHANNELS
        
        self.assertEqual(AUDIO_CHANNELS, 1)
        self.assertIsInstance(AUDIO_CHANNELS, int)
    
    def test_sample_rate_valid(self):
        """Test sample rate is a valid audio rate."""
        from whisper_local.flow_local_dictation import SAMPLE_RATE
        
        valid_rates = [8000, 16000, 22050, 44100, 48000]
        self.assertIn(SAMPLE_RATE, valid_rates)
    
    def test_channels_valid(self):
        """Test channel count is valid (mono or stereo)."""
        from whisper_local.flow_local_dictation import CHANNELS
        
        self.assertIn(CHANNELS, [1, 2])


class TestVoiceActivityDetection(unittest.TestCase):
    """Tests for voice activity detection."""
    
    def test_rms_threshold_defined(self):
        """Test RMS threshold is defined."""
        from whisper_local.flow_local_dictation import RMS_THRESHOLD_VOICED
        
        self.assertIsInstance(RMS_THRESHOLD_VOICED, float)
        self.assertGreater(RMS_THRESHOLD_VOICED, 0)
        self.assertLess(RMS_THRESHOLD_VOICED, 1.0)
    
    def test_silence_threshold_defined(self):
        """Test silence detection threshold is defined."""
        from whisper_local.flow_local_dictation import SILENCE_RMS_THRESHOLD
        
        self.assertIsInstance(SILENCE_RMS_THRESHOLD, float)
        self.assertGreater(SILENCE_RMS_THRESHOLD, 0)
    
    def test_rms_calculation_silent_audio(self):
        """Test RMS calculation for silent audio."""
        silent_audio = np.zeros(1000, dtype=np.float32)
        rms = np.sqrt(np.mean(silent_audio**2))
        
        self.assertLess(rms, 0.001)
        self.assertEqual(rms, 0.0)
    
    def test_rms_calculation_loud_audio(self):
        """Test RMS calculation for loud audio."""
        loud_audio = np.ones(1000, dtype=np.float32) * 0.5
        rms = np.sqrt(np.mean(loud_audio**2))
        
        self.assertGreater(rms, 0.4)
        self.assertAlmostEqual(rms, 0.5, places=1)
    
    def test_rms_calculation_variable_audio(self):
        """Test RMS calculation for variable amplitude audio."""
        # Sine wave
        t = np.linspace(0, 1, 16000, dtype=np.float32)
        audio = np.sin(2 * np.pi * 440 * t) * 0.3  # 440 Hz tone at 30% amplitude
        rms = np.sqrt(np.mean(audio**2))
        
        # RMS of sine wave should be amplitude / sqrt(2)
        expected_rms = 0.3 / np.sqrt(2)
        self.assertAlmostEqual(rms, expected_rms, places=2)
    
    def test_voice_threshold_reasonable(self):
        """Test voice activity threshold is reasonable."""
        from whisper_local.flow_local_dictation import RMS_THRESHOLD_VOICED
        
        # Should be sensitive enough to detect whispers but not clicks
        self.assertGreater(RMS_THRESHOLD_VOICED, 0.0001)
        self.assertLess(RMS_THRESHOLD_VOICED, 0.05)


class TestAudioTiming(unittest.TestCase):
    """Tests for audio timing constants."""
    
    def test_min_speech_duration(self):
        """Test minimum speech duration is defined."""
        from whisper_local.flow_local_dictation import MIN_SPEECH_DURATION_SEC
        
        self.assertIsInstance(MIN_SPEECH_DURATION_SEC, float)
        self.assertGreater(MIN_SPEECH_DURATION_SEC, 0)
        self.assertLess(MIN_SPEECH_DURATION_SEC, 1.0)
    
    def test_audio_block_duration(self):
        """Test audio block duration for RMS calculation."""
        from whisper_local.flow_local_dictation import AUDIO_BLOCK_DURATION_SEC
        
        self.assertIsInstance(AUDIO_BLOCK_DURATION_SEC, float)
        self.assertGreater(AUDIO_BLOCK_DURATION_SEC, 0)
        self.assertLess(AUDIO_BLOCK_DURATION_SEC, 0.5)
    
    def test_postroll_duration(self):
        """Test postroll duration after key release."""
        from whisper_local.flow_local_dictation import POSTROLL_DURATION_SEC
        
        self.assertIsInstance(POSTROLL_DURATION_SEC, float)
        self.assertGreater(POSTROLL_DURATION_SEC, 0)
        self.assertLess(POSTROLL_DURATION_SEC, 1.0)


class TestAudioPathResolution(unittest.TestCase):
    """Tests for audio file path resolution."""
    
    def test_wav_tmp_path_defined(self):
        """Test temporary WAV path is defined."""
        from whisper_local.flow_local_dictation import WAV_TMP
        
        self.assertIsInstance(WAV_TMP, str)
        self.assertTrue(WAV_TMP.endswith('.wav'))
    
    def test_wav_path_in_user_directory(self):
        """Test WAV file is stored in user data directory."""
        from whisper_local.flow_local_dictation import WAV_TMP, get_user_data_dir
        
        user_dir = get_user_data_dir()
        self.assertTrue(WAV_TMP.startswith(user_dir))


class TestAudioDeviceSelection(unittest.TestCase):
    """Tests for audio device selection."""
    
    @patch('sounddevice.query_devices')
    def test_audio_device_query(self, mock_query):
        """Test audio device querying."""
        mock_query.return_value = [
            {'name': 'Microphone 1', 'max_input_channels': 2},
            {'name': 'Microphone 2', 'max_input_channels': 1},
        ]
        
        import sounddevice as sd
        devices = sd.query_devices()
        
        self.assertEqual(len(devices), 2)
        self.assertIn('name', devices[0])
    
    def test_input_device_configuration(self):
        """Test input device can be configured."""
        from whisper_local.flow_local_dictation import INPUT_DEVICE
        
        # Should be None or a valid device identifier
        self.assertTrue(INPUT_DEVICE is None or isinstance(INPUT_DEVICE, (int, str)))


class TestAudioRecordingState(unittest.TestCase):
    """Tests for audio recording state management."""
    
    def test_recording_flag_exists(self):
        """Test recording flag is defined."""
        from whisper_local.flow_local_dictation import recording_flag
        
        self.assertIsNotNone(recording_flag)
        # Should be a threading.Event
        self.assertTrue(hasattr(recording_flag, 'is_set'))
        self.assertTrue(hasattr(recording_flag, 'set'))
        self.assertTrue(hasattr(recording_flag, 'clear'))
    
    def test_state_lock_exists(self):
        """Test state lock is defined."""
        from whisper_local.flow_local_dictation import STATE_LOCK
        
        self.assertIsNotNone(STATE_LOCK)
        # Should be a threading.Lock
        self.assertTrue(hasattr(STATE_LOCK, 'acquire'))
        self.assertTrue(hasattr(STATE_LOCK, 'release'))


if __name__ == '__main__':
    unittest.main()


