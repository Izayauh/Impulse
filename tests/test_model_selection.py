"""Unit tests for shared model-selection helpers."""

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.model_selection import apply_mode, default_state, load_state, refresh_auto_state, save_state


class TestModelSelectionHelpers(unittest.TestCase):
    def test_load_missing_state_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "model_selection.json")
            state = load_state(path)
            self.assertEqual(state["mode"], "auto")
            self.assertEqual(state["active_model"], "base")

    def test_apply_manual_mode_sets_active_model(self):
        state, auto_switched = apply_mode(default_state(), "medium", 0)
        self.assertEqual(state["mode"], "medium")
        self.assertEqual(state["active_model"], "medium")
        self.assertFalse(auto_switched)

    def test_apply_auto_mode_switches_to_large_when_vram_above_8gb(self):
        base = default_state()
        base["active_model"] = "base"
        state, auto_switched = apply_mode(base, "auto", 12288)
        self.assertEqual(state["mode"], "auto")
        self.assertEqual(state["active_model"], "large")
        self.assertTrue(auto_switched)

    def test_refresh_auto_state_updates_active_model(self):
        state = default_state()
        state["mode"] = "auto"
        state["active_model"] = "base"
        refreshed, auto_switched = refresh_auto_state(state, 12288)
        self.assertEqual(refreshed["active_model"], "large")
        self.assertTrue(auto_switched)

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "model_selection.json")
            original, _ = apply_mode(default_state(), "small", 0)
            self.assertTrue(save_state(path, original))
            loaded = load_state(path)
            self.assertEqual(loaded["mode"], "small")
            self.assertEqual(loaded["active_model"], "small")


if __name__ == "__main__":
    unittest.main()
