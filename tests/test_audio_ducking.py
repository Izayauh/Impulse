"""Tests for push-to-talk playback ducking manager."""

import json
import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class _FakeVolumeBackend:
    def __init__(self, initial_raw: int):
        self.is_available = True
        self.current_raw = int(initial_raw)
        self.set_calls = []

    def get_volume_raw(self) -> int:
        return int(self.current_raw)

    def set_volume_raw(self, raw_value: int) -> None:
        self.current_raw = int(raw_value)
        self.set_calls.append(int(raw_value))


class TestAudioDuckingSessionManager(unittest.TestCase):
    def test_activate_release_restores_original_volume(self):
        from whisper_local.audio_ducking import AudioDuckingSessionManager

        with tempfile.TemporaryDirectory() as td:
            state_file = os.path.join(td, "duck_state.json")
            backend = _FakeVolumeBackend(initial_raw=0x5A5A5A5A)
            manager = AudioDuckingSessionManager(
                state_file=state_file,
                backend=backend,
                duck_level=0.0,
                restore_delay_ms=0,
            )

            self.assertTrue(manager.activate(reason="test"))
            self.assertEqual(backend.current_raw, 0)
            self.assertTrue(os.path.exists(state_file))

            self.assertTrue(manager.release(reason="test"))
            self.assertEqual(backend.current_raw, 0x5A5A5A5A)
            self.assertFalse(os.path.exists(state_file))

    def test_nested_holds_do_not_restore_early(self):
        from whisper_local.audio_ducking import AudioDuckingSessionManager

        backend = _FakeVolumeBackend(initial_raw=0x3FFF3FFF)
        manager = AudioDuckingSessionManager(
            backend=backend,
            duck_level=0.0,
            restore_delay_ms=0,
        )

        self.assertTrue(manager.activate())
        self.assertTrue(manager.activate())
        self.assertEqual(backend.current_raw, 0)

        self.assertFalse(manager.release())
        self.assertEqual(backend.current_raw, 0)

        self.assertTrue(manager.release())
        self.assertEqual(backend.current_raw, 0x3FFF3FFF)

    def test_repeated_cycles_do_not_drift_volume(self):
        from whisper_local.audio_ducking import AudioDuckingSessionManager

        original = 0x24682468
        backend = _FakeVolumeBackend(initial_raw=original)
        manager = AudioDuckingSessionManager(
            backend=backend,
            duck_level=0.0,
            restore_delay_ms=0,
        )

        for _ in range(40):
            self.assertTrue(manager.activate())
            self.assertTrue(manager.release())

        self.assertEqual(backend.current_raw, original)

    def test_force_restore_clears_duck_state(self):
        from whisper_local.audio_ducking import AudioDuckingSessionManager

        backend = _FakeVolumeBackend(initial_raw=0x7AAA7AAA)
        manager = AudioDuckingSessionManager(
            backend=backend,
            duck_level=0.0,
            restore_delay_ms=500,
        )

        self.assertTrue(manager.activate())
        self.assertEqual(backend.current_raw, 0)
        self.assertTrue(manager.force_restore(reason="unit_test"))
        self.assertEqual(backend.current_raw, 0x7AAA7AAA)

    def test_restore_stale_state_from_previous_run(self):
        from whisper_local.audio_ducking import AudioDuckingSessionManager

        with tempfile.TemporaryDirectory() as td:
            state_file = os.path.join(td, "duck_state.json")
            payload = {
                "version": 1,
                "active": True,
                "saved_raw_volume": 0x34563456,
                "duck_raw_volume": 0,
                "pid": 12345,
                "timestamp_unix": 1.0,
            }
            with open(state_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)

            backend = _FakeVolumeBackend(initial_raw=0)
            manager = AudioDuckingSessionManager(
                state_file=state_file,
                backend=backend,
                duck_level=0.0,
                restore_delay_ms=0,
            )

            self.assertTrue(manager.restore_stale_state())
            self.assertEqual(backend.current_raw, 0x34563456)
            self.assertFalse(os.path.exists(state_file))


if __name__ == "__main__":
    unittest.main()
