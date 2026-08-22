"""Unit tests for shared model-selection helpers."""

import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.model_selection import (
    AUTO_VRAM_THRESHOLD_MB,
    apply_mode,
    auto_model_for_vram,
    default_state,
    load_state,
    refresh_auto_state,
    save_state,
)


class TestModelSelectionHelpers(unittest.TestCase):
    def test_load_missing_state_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "model_selection.json")
            state = load_state(path)
            self.assertEqual(state["mode"], "auto")
            self.assertEqual(state["active_model"], "turbo")

    def test_apply_legacy_manual_mode_falls_back_to_auto(self):
        # Retired modes (medium/small/fast) coerce to auto, which resolves by hardware.
        state, _ = apply_mode(default_state(), "medium", 0)
        self.assertEqual(state["mode"], "auto")
        self.assertEqual(state["active_model"], "base")

    def test_apply_turbo_mode_sets_active_model(self):
        state, auto_switched = apply_mode(default_state(), "turbo", 0)
        self.assertEqual(state["mode"], "turbo")
        self.assertEqual(state["manual_model"], "turbo")
        self.assertEqual(state["active_model"], "turbo")
        self.assertFalse(auto_switched)

    def test_apply_base_mode_is_honored(self):
        state, auto_switched = apply_mode(default_state(), "base", 12288)
        self.assertEqual(state["mode"], "base")
        self.assertEqual(state["manual_model"], "base")
        self.assertEqual(state["active_model"], "base")
        self.assertTrue(auto_switched)

    def test_auto_mode_picks_turbo_with_enough_vram(self):
        state, _ = apply_mode(default_state(), "auto", AUTO_VRAM_THRESHOLD_MB)
        self.assertEqual(state["mode"], "auto")
        self.assertEqual(state["active_model"], "turbo")

    def test_auto_mode_picks_base_without_gpu(self):
        state, auto_switched = apply_mode(default_state(), "auto", 0)
        self.assertEqual(state["mode"], "auto")
        self.assertEqual(state["active_model"], "base")
        self.assertTrue(auto_switched)

    def test_auto_model_for_vram_boundary(self):
        self.assertEqual(auto_model_for_vram(AUTO_VRAM_THRESHOLD_MB - 1), "base")
        self.assertEqual(auto_model_for_vram(AUTO_VRAM_THRESHOLD_MB), "turbo")

    def test_refresh_auto_state_switches_with_hardware(self):
        state = default_state()
        state["mode"] = "auto"
        state["active_model"] = "base"
        refreshed, auto_switched = refresh_auto_state(state, 12288)
        self.assertEqual(refreshed["mode"], "auto")
        self.assertEqual(refreshed["active_model"], "turbo")
        self.assertTrue(auto_switched)

    def test_refresh_keeps_manual_pin(self):
        state, _ = apply_mode(default_state(), "base", 12288)
        refreshed, auto_switched = refresh_auto_state(state, 12288)
        self.assertEqual(refreshed["active_model"], "base")
        self.assertFalse(auto_switched)

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "model_selection.json")
            original, _ = apply_mode(default_state(), "base", 0)
            self.assertTrue(save_state(path, original))
            loaded = load_state(path)
            self.assertEqual(loaded["mode"], "base")
            self.assertEqual(loaded["active_model"], "base")


if __name__ == "__main__":
    unittest.main()
