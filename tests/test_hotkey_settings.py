"""Unit tests for hotkey settings persistence and normalization."""

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.hotkey_settings import (
    DEFAULT_HOTKEY,
    hotkey_tokens,
    load_hotkey,
    set_hotkey,
    settings_file,
    try_normalize_hotkey,
)


class TestHotkeySettings(unittest.TestCase):
    def test_try_normalize_hotkey_accepts_modifier_combo(self):
        self.assertEqual(try_normalize_hotkey("Win + Space"), "windows+space")
        self.assertEqual(try_normalize_hotkey("alt+space"), "alt+space")

    def test_try_normalize_hotkey_rejects_single_key(self):
        self.assertIsNone(try_normalize_hotkey("a"))
        self.assertIsNone(try_normalize_hotkey("space"))

    def test_set_and_load_hotkey_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = settings_file(tmp_dir)
            value, changed = set_hotkey(path, "ctrl+shift+m")
            self.assertTrue(changed)
            self.assertEqual(value, "ctrl+shift+m")
            self.assertEqual(load_hotkey(path), "ctrl+shift+m")
            self.assertEqual(hotkey_tokens(load_hotkey(path)), ["ctrl", "shift", "m"])

    def test_load_hotkey_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = settings_file(tmp_dir)
            self.assertEqual(load_hotkey(path), DEFAULT_HOTKEY)

    def test_set_hotkey_raises_for_invalid_combo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = settings_file(tmp_dir)
            with self.assertRaises(ValueError):
                set_hotkey(path, "space")


if __name__ == "__main__":
    unittest.main()
