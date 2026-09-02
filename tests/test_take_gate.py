"""The take gate must be honest: silence and fan noise stop before Whisper, speech never does.

From the 2026-09-02 laptop test: the processing bar ran for a long time on
takes with nothing said. The old gate was a fixed RMS (0.002) that sat below
laptop fan noise, so a silent take went to Whisper on CPU and Whisper
invented words for it. The gate is now relative to each take's own noise
floor, scaled by the dashboard sensitivity slider, re-read every take.
"""

import os
import random
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import whisper_local.flow_local_dictation as flow
from whisper_local.settings_manager import SettingsManager


FRAME = flow.AUDIO_BLOCK_DURATION_SEC


def noise(level, seconds, jitter=0.15, seed=1):
    """Stationary noise frames at *level* RMS with a little frame-to-frame jitter."""
    rng = random.Random(seed)
    return [level * (1.0 + rng.uniform(-jitter, jitter)) for _ in range(int(seconds / FRAME))]


def speech(level, seconds, seed=2):
    """Speech-like frames: RMS swings between a third of *level* and *level*."""
    rng = random.Random(seed)
    return [level * rng.uniform(0.33, 1.0) for _ in range(int(seconds / FRAME))]


class NoiseFloorTest(unittest.TestCase):
    def test_floor_is_the_top_of_the_quietest_fifth(self):
        frames = [0.001] * 4 + [0.01] * 16
        self.assertAlmostEqual(flow.estimate_noise_floor(frames), 0.001)

    def test_a_few_zero_frames_do_not_zero_the_floor(self):
        # The first reads after a stream opens can be all zeros.
        frames = [0.0, 0.0] + [0.004] * 18
        self.assertAlmostEqual(flow.estimate_noise_floor(frames), 0.004)

    def test_digital_silence_clamps_to_the_minimum(self):
        self.assertEqual(flow.estimate_noise_floor([1e-6] * 20), flow.NOISE_FLOOR_MIN_RMS)

    def test_no_frames_gives_the_minimum(self):
        self.assertEqual(flow.estimate_noise_floor([]), flow.NOISE_FLOOR_MIN_RMS)


class SensitivityMappingTest(unittest.TestCase):
    def test_ends_of_the_slider(self):
        self.assertAlmostEqual(flow.voiced_ratio_for_sensitivity(1), flow.VOICED_RATIO_LOW_SENSITIVITY)
        self.assertAlmostEqual(flow.voiced_ratio_for_sensitivity(100), flow.VOICED_RATIO_HIGH_SENSITIVITY)

    def test_higher_sensitivity_means_a_lower_bar(self):
        ratios = [flow.voiced_ratio_for_sensitivity(s) for s in range(1, 101)]
        self.assertEqual(ratios, sorted(ratios, reverse=True))
        self.assertGreater(ratios[0], ratios[-1])

    def test_out_of_range_and_junk_values_are_safe(self):
        self.assertAlmostEqual(flow.voiced_ratio_for_sensitivity(0), flow.VOICED_RATIO_LOW_SENSITIVITY)
        self.assertAlmostEqual(flow.voiced_ratio_for_sensitivity(500), flow.VOICED_RATIO_HIGH_SENSITIVITY)
        self.assertAlmostEqual(
            flow.voiced_ratio_for_sensitivity("junk"),
            flow.voiced_ratio_for_sensitivity(flow.DEFAULT_VAD_SENSITIVITY),
        )


class TakeGateTest(unittest.TestCase):
    DEFAULT = flow.DEFAULT_VAD_SENSITIVITY

    def test_fan_noise_take_is_dropped(self):
        frames = noise(0.005, 3.0)
        # The regression: every one of these frames cleared the old fixed gate.
        self.assertTrue(all(f > flow.RMS_THRESHOLD_VOICED for f in frames))
        verdict = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        self.assertFalse(verdict["has_speech"])
        self.assertEqual(verdict["reason"], "silent")

    def test_digital_silence_is_dropped(self):
        verdict = flow.analyze_take_energy([1e-6] * 40, self.DEFAULT, FRAME)
        self.assertFalse(verdict["has_speech"])

    def test_first_zero_frames_do_not_make_fan_noise_speech(self):
        frames = [0.0] * 3 + noise(0.005, 2.85)
        verdict = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        self.assertFalse(verdict["has_speech"], verdict)

    def test_speech_over_fan_noise_passes(self):
        frames = noise(0.005, 1.0) + speech(0.04, 0.6) + noise(0.005, 0.4)
        verdict = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        self.assertTrue(verdict["has_speech"])
        self.assertEqual(verdict["reason"], "voiced")
        self.assertGreaterEqual(verdict["voiced_sec"], flow.MIN_SEC)

    def test_quiet_studio_interface_still_passes(self):
        # Isaiah's Audient iD14: speech at 0.002-0.01 over a 0.0001 floor.
        frames = noise(0.00012, 0.5) + speech(0.006, 0.5) + noise(0.00012, 0.3)
        verdict = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        self.assertTrue(verdict["has_speech"], verdict)

    def test_short_clear_word_passes_by_peak(self):
        # Two frames of speech is under MIN_SEC, but a frame 15x the floor is speech.
        frames = noise(0.004, 1.0) + [0.06, 0.06]
        verdict = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        self.assertLess(verdict["voiced_sec"], flow.MIN_SEC)
        self.assertGreaterEqual(verdict["peak_ratio"], flow.SPEECH_PEAK_RATIO)
        self.assertTrue(verdict["has_speech"])
        self.assertEqual(verdict["reason"], "peak")

    def test_peak_rule_needs_a_real_level_not_just_a_ratio(self):
        # Digital silence with one dither blip: 15x a clamped floor, but far
        # below anything a voice produces.
        frames = [1e-6] * 30 + [0.0015]
        verdict = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        self.assertGreaterEqual(verdict["peak_ratio"], flow.SPEECH_PEAK_RATIO)
        self.assertFalse(verdict["has_speech"])

    def test_sensitivity_slider_moves_the_verdict(self):
        # Speech at twice the floor: below the default bar, above the top-of-slider bar.
        frames = noise(0.005, 0.5) + [0.010] * 20 + noise(0.005, 0.5)
        at_default = flow.analyze_take_energy(frames, self.DEFAULT, FRAME)
        at_max = flow.analyze_take_energy(frames, 100, FRAME)
        self.assertFalse(at_default["has_speech"])
        self.assertTrue(at_max["has_speech"])

    def test_empty_take_is_dropped(self):
        self.assertFalse(flow.analyze_take_energy([], self.DEFAULT, FRAME)["has_speech"])


class TakeSettingsRereadTest(unittest.TestCase):
    """The dashboard writes settings from another process; each take must see the file as it is now."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.user_dir = tmp.name
        engine_mgr = SettingsManager(self.user_dir)
        patcher = patch.object(flow, "_flow_settings_mgr", engine_mgr)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_slider_change_from_another_manager_reaches_the_next_take(self):
        self.assertEqual(flow.current_take_settings()["vad_sensitivity"], 65)
        dashboard_mgr = SettingsManager(self.user_dir)  # the dashboard process
        self.assertTrue(dashboard_mgr.update_setting("vad_sensitivity", 90))
        self.assertEqual(flow.current_take_settings()["vad_sensitivity"], 90)

    def test_microphone_change_reaches_the_next_take(self):
        SettingsManager(self.user_dir).update_setting("input_device", "Audient iD14")
        self.assertEqual(flow.current_take_settings()["input_device"], "Audient iD14")

    def test_defaults_when_the_settings_file_cannot_be_read(self):
        with patch.object(flow, "_get_flow_settings_mgr", side_effect=OSError("locked")):
            settings = flow.current_take_settings()
        self.assertEqual(settings["vad_sensitivity"], flow.DEFAULT_VAD_SENSITIVITY)
        self.assertEqual(settings["input_device"], "default")


class InputDeviceRequestTest(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("FLOW_INPUT_DEVICE", None)
        for name, value in (("INPUT_DEVICE", None), ("_resolved_input_device_request", None)):
            patcher = patch.object(flow, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_default_labels_mean_system_default(self):
        for value in (None, "", "default", "Default", "Default System Microphone"):
            self.assertIsNone(flow._input_device_request_from_settings(value), value)

    def test_device_labels_and_indices_pass_through(self):
        self.assertEqual(flow._input_device_request_from_settings(" Audient "), "Audient")
        self.assertEqual(flow._input_device_request_from_settings("2"), "2")

    def test_env_override_wins_over_settings(self):
        os.environ["FLOW_INPUT_DEVICE"] = "3"
        self.assertEqual(flow._requested_input_device({"input_device": "Audient"}), "3")

    def test_settings_choice_used_when_env_unset(self):
        self.assertEqual(flow._requested_input_device({"input_device": "Audient"}), "Audient")
        self.assertIsNone(flow._requested_input_device({"input_device": "default"}))

    def test_sync_reresolves_only_when_the_choice_changed(self):
        with patch.object(flow, "resolve_input_device") as resolve:
            flow._sync_input_device_from_settings({"input_device": "default"})
            resolve.assert_not_called()
            flow._sync_input_device_from_settings({"input_device": "Audient"})
            resolve.assert_called_once_with()


class StartMenuGuardDecisionTest(unittest.TestCase):
    """Windows opens Start on a bare Win tap; the guard must fire while Win is still down."""

    HOLD = ["ctrl", "windows"]

    def test_press_edge_taps_while_win_is_down(self):
        self.assertTrue(flow.start_menu_guard_needed(self.HOLD, "press", win_down=True))

    def test_release_edge_taps_only_while_win_is_still_down(self):
        self.assertTrue(flow.start_menu_guard_needed(self.HOLD, "release", win_down=True))
        # Win was the first key released: Start is already decided, nothing to do.
        self.assertFalse(flow.start_menu_guard_needed(self.HOLD, "release", win_down=False))

    def test_latch_chord_always_carries_win(self):
        self.assertTrue(flow.start_menu_guard_needed(["ctrl", "shift", "m"], "latch", win_down=True))
        self.assertFalse(flow.start_menu_guard_needed(["ctrl", "shift", "m"], "latch", win_down=False))

    def test_chords_without_win_never_tap(self):
        for edge in ("press", "release"):
            self.assertFalse(flow.start_menu_guard_needed(["ctrl", "shift", "m"], edge, win_down=True))

    def test_win_alias_and_unknown_edges(self):
        self.assertTrue(flow.start_menu_guard_needed(["ctrl", "win"], "press", win_down=True))
        self.assertFalse(flow.start_menu_guard_needed(self.HOLD, "poll", win_down=True))

    def test_win_key_down_reads_both_lwin_and_rwin(self):
        def pressed(vk_set):
            return lambda vk: 0x8000 if vk in vk_set else 0

        fake_user32 = MagicMock()
        with patch.object(flow, "_user32", fake_user32):
            fake_user32.GetAsyncKeyState.side_effect = pressed({0x5B})
            self.assertTrue(flow._win_key_down())
            fake_user32.GetAsyncKeyState.side_effect = pressed({0x5C})
            self.assertTrue(flow._win_key_down())
            fake_user32.GetAsyncKeyState.side_effect = pressed(set())
            self.assertFalse(flow._win_key_down())

    def test_guard_injects_through_the_helper_only_when_needed(self):
        with patch.object(flow, "_tap_neutral_key", return_value=True) as tap:
            with patch.object(flow, "_win_key_down", return_value=True):
                self.assertTrue(flow._guard_start_menu(self.HOLD, "press"))
                tap.assert_called_once_with()
            tap.reset_mock()
            with patch.object(flow, "_win_key_down", return_value=False):
                self.assertFalse(flow._guard_start_menu(self.HOLD, "release"))
                tap.assert_not_called()

    def test_guard_never_raises(self):
        with patch.object(flow, "_win_key_down", side_effect=OSError("no user32")):
            self.assertFalse(flow._guard_start_menu(self.HOLD, "press"))


class WhisperCppGuardArgsTest(unittest.TestCase):
    def test_whisper_cli_gets_no_fallback_and_suppress_nonspeech(self):
        self.assertEqual(flow.whisper_cpp_hallucination_guard_args(True), ["-nf", "-sns"])

    def test_legacy_main_exe_gets_nothing(self):
        self.assertEqual(flow.whisper_cpp_hallucination_guard_args(False), [])


if __name__ == "__main__":
    unittest.main()
