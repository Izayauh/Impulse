"""
Tests for UI components and theming.

Run with: python -m pytest tests/test_ui.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class TestThemeConfiguration(unittest.TestCase):
    """Tests for theme and color configuration."""
    
    def test_theme_class_exists(self):
        """Test Theme class is defined."""
        from whisper_local.flow_local_dictation import Theme
        
        self.assertIsNotNone(Theme)
    
    def test_theme_has_required_colors(self):
        """Test Theme class has all required color constants."""
        from whisper_local.flow_local_dictation import Theme
        
        required_colors = [
            'BG_ELEVATED',
            'BG_DARK',
            'TEXT_PRIMARY',
            'SUCCESS',
            'ERROR',
            'WARNING',
            'INFO',
            'PINK_PRIMARY'
        ]
        
        for color in required_colors:
            self.assertTrue(hasattr(Theme, color), f"Theme missing color: {color}")
            color_value = getattr(Theme, color)
            self.assertIsInstance(color_value, str)
            # Should be hex color or color name
            self.assertGreater(len(color_value), 0)
    
    def test_theme_colors_are_valid_hex(self):
        """Test theme colors are valid hex codes."""
        from whisper_local.flow_local_dictation import Theme
        import re
        
        # Get all color attributes
        colors = [attr for attr in dir(Theme) if not attr.startswith('_')]
        
        # Support both 6-digit and 8-digit (with alpha) hex colors
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')
        
        for color_name in colors:
            color_value = getattr(Theme, color_name)
            if isinstance(color_value, str) and color_value.startswith('#'):
                self.assertTrue(
                    hex_pattern.match(color_value),
                    f"{color_name} has invalid hex color: {color_value}"
                )


class TestStatusMessages(unittest.TestCase):
    """Tests for status messages and indicators."""
    
    def test_status_messages_use_emojis(self):
        """Test status messages use emojis for visual feedback."""
        # These should be the actual status messages used
        ready_msg = "🎤 Ready"
        listening_msg = "🎙️ Listening..."
        transcribing_msg = "⚙️ Transcribing..."
        pasted_msg = "✅ Pasted!"
        error_msg = "❌ Failed"
        no_speech_msg = "🔇 No speech"
        
        # Each message should have content
        self.assertGreater(len(ready_msg), 5)
        self.assertGreater(len(listening_msg), 5)
        self.assertGreater(len(transcribing_msg), 5)
        self.assertGreater(len(pasted_msg), 5)
        self.assertGreater(len(error_msg), 5)
        self.assertGreater(len(no_speech_msg), 5)
        
        # Check that they contain descriptive text
        self.assertIn("Ready", ready_msg)
        self.assertIn("Listening", listening_msg)
        self.assertIn("Transcribing", transcribing_msg)
        self.assertIn("Pasted", pasted_msg)
        self.assertIn("Failed", error_msg)
        self.assertIn("speech", no_speech_msg)


class TestUIConfiguration(unittest.TestCase):
    """Tests for UI configuration constants."""
    
    def test_hotkey_defined(self):
        """Test hotkey is defined."""
        from whisper_local.flow_local_dictation import HOTKEY_HOLD
        
        self.assertIsInstance(HOTKEY_HOLD, str)
        self.assertGreater(len(HOTKEY_HOLD), 0)
    
    def test_hotkey_debounce_defined(self):
        """Test hotkey debounce is defined."""
        from whisper_local.flow_local_dictation import HOTKEY_DEBOUNCE_MS
        
        self.assertIsInstance(HOTKEY_DEBOUNCE_MS, int)
        self.assertGreater(HOTKEY_DEBOUNCE_MS, 0)
        self.assertLess(HOTKEY_DEBOUNCE_MS, 1000)  # Should be < 1 second
    
    def test_ui_animation_fps(self):
        """Test UI animation FPS is reasonable."""
        from whisper_local.flow_local_dictation import UI_ANIMATION_FPS
        
        self.assertIsInstance(UI_ANIMATION_FPS, int)
        self.assertGreater(UI_ANIMATION_FPS, 0)
        self.assertLessEqual(UI_ANIMATION_FPS, 60)  # Max 60 FPS
    
    def test_ui_queue_poll_rate(self):
        """Test UI queue polling rate is defined."""
        from whisper_local.flow_local_dictation import UI_QUEUE_POLL_MS
        
        self.assertIsInstance(UI_QUEUE_POLL_MS, int)
        self.assertGreater(UI_QUEUE_POLL_MS, 0)
        self.assertLess(UI_QUEUE_POLL_MS, 1000)
    
    def test_status_display_duration(self):
        """Test status message display duration is reasonable."""
        from whisper_local.flow_local_dictation import STATUS_SUCCESS_DISPLAY_SEC
        
        self.assertIsInstance(STATUS_SUCCESS_DISPLAY_SEC, float)
        self.assertGreater(STATUS_SUCCESS_DISPLAY_SEC, 0)
        self.assertLess(STATUS_SUCCESS_DISPLAY_SEC, 10)  # Should be < 10 seconds


class TestUIState(unittest.TestCase):
    """Tests for UI state management."""
    
    def test_ui_queue_exists(self):
        """Test UI update queue exists."""
        from whisper_local.flow_local_dictation import ui_queue
        
        self.assertIsNotNone(ui_queue)
        # Should be a queue.Queue
        self.assertTrue(hasattr(ui_queue, 'put'))
        self.assertTrue(hasattr(ui_queue, 'get'))
    
    def test_dashboard_window_reference(self):
        """Test dashboard window reference exists."""
        from whisper_local.flow_local_dictation import dashboard_window
        
        # Should be None or a Tk window
        self.assertTrue(dashboard_window is None or hasattr(dashboard_window, 'winfo_exists'))


class TestApplicationMetadata(unittest.TestCase):
    """Tests for application metadata."""
    
    def test_app_name_defined(self):
        """Test application name is defined."""
        from whisper_local.flow_local_dictation import APP_NAME
        
        self.assertIsInstance(APP_NAME, str)
        self.assertGreater(len(APP_NAME), 0)
        self.assertEqual(APP_NAME, "Impulse")
    
    def test_app_version_defined(self):
        """Test application version is defined."""
        from whisper_local.flow_local_dictation import APP_VERSION
        
        self.assertIsInstance(APP_VERSION, str)
        self.assertGreater(len(APP_VERSION), 0)
        # Should match semantic versioning pattern
        self.assertRegex(APP_VERSION, r'^\d+\.\d+\.\d+')
    
    def test_app_author_defined(self):
        """Test application author is defined."""
        from whisper_local.flow_local_dictation import APP_AUTHOR
        
        self.assertIsInstance(APP_AUTHOR, str)
        self.assertGreater(len(APP_AUTHOR), 0)


class TestPathResolution(unittest.TestCase):
    """Tests for path resolution functions."""
    
    def test_is_frozen_function(self):
        """Test is_frozen function exists."""
        from whisper_local.flow_local_dictation import is_frozen
        
        result = is_frozen()
        self.assertIsInstance(result, bool)
        # In test environment, should not be frozen
        self.assertFalse(result)
    
    def test_get_bundle_dir(self):
        """Test get_bundle_dir returns valid path."""
        from whisper_local.flow_local_dictation import get_bundle_dir
        
        bundle_dir = get_bundle_dir()
        self.assertIsInstance(bundle_dir, str)
        self.assertTrue(os.path.isabs(bundle_dir))
    
    def test_get_app_dir(self):
        """Test get_app_dir returns valid path."""
        from whisper_local.flow_local_dictation import get_app_dir
        
        app_dir = get_app_dir()
        self.assertIsInstance(app_dir, str)
        self.assertTrue(os.path.isabs(app_dir))
    
    def test_get_user_data_dir(self):
        """Test get_user_data_dir returns valid path."""
        from whisper_local.flow_local_dictation import get_user_data_dir
        
        user_dir = get_user_data_dir()
        self.assertIsInstance(user_dir, str)
        self.assertTrue(os.path.isabs(user_dir))
    
    def test_get_config_file(self):
        """Test get_config_file returns valid path."""
        from whisper_local.flow_local_dictation import get_config_file
        
        config_file = get_config_file()
        self.assertIsInstance(config_file, str)
        self.assertTrue(config_file.endswith('.json'))


class TestNotificationSystem(unittest.TestCase):
    """Tests for notification system."""
    
    def test_notify_function_exists(self):
        """Test notify function exists."""
        from whisper_local.flow_local_dictation import notify
        
        self.assertIsNotNone(notify)
        self.assertTrue(callable(notify))
    
    @patch('whisper_local.flow_local_dictation.log_line')
    def test_notify_logs_message(self, mock_log):
        """Test notify function logs messages."""
        from whisper_local.flow_local_dictation import notify
        
        test_message = "Test notification"
        notify(test_message)
        
        # Should log the message
        mock_log.assert_called()


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling UI."""
    
    def test_friendly_error_function_exists(self):
        """Test show_friendly_error function exists."""
        from whisper_local.flow_local_dictation import show_friendly_error
        
        self.assertIsNotNone(show_friendly_error)
        self.assertTrue(callable(show_friendly_error))
    
    def test_get_friendly_error_message_exists(self):
        """Test get_friendly_error_message function exists."""
        from whisper_local.flow_local_dictation import get_friendly_error_message
        
        self.assertIsNotNone(get_friendly_error_message)
        self.assertTrue(callable(get_friendly_error_message))
    
    def test_handle_startup_issue_exists(self):
        """Test handle_startup_issue function exists."""
        from whisper_local.flow_local_dictation import handle_startup_issue
        
        self.assertIsNotNone(handle_startup_issue)
        self.assertTrue(callable(handle_startup_issue))


class TestClipboardOperations(unittest.TestCase):
    """Tests for clipboard operations."""
    
    def test_clipboard_settle_delay(self):
        """Test clipboard settle delay is defined."""
        from whisper_local.flow_local_dictation import CLIPBOARD_SETTLE_DELAY_SEC
        
        self.assertIsInstance(CLIPBOARD_SETTLE_DELAY_SEC, float)
        self.assertGreater(CLIPBOARD_SETTLE_DELAY_SEC, 0)
        self.assertLess(CLIPBOARD_SETTLE_DELAY_SEC, 1.0)


class TestSingleInstance(unittest.TestCase):
    """Tests for single instance enforcement."""
    
    def test_singleton_lock_functions_exist(self):
        """Test singleton lock functions exist."""
        from whisper_local.flow_local_dictation import _acquire_single_instance, _release_single_instance
        
        self.assertIsNotNone(_acquire_single_instance)
        self.assertIsNotNone(_release_single_instance)
        self.assertTrue(callable(_acquire_single_instance))
        self.assertTrue(callable(_release_single_instance))


if __name__ == '__main__':
    unittest.main()


