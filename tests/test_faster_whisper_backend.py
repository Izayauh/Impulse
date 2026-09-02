"""Tests for GPU capability detection.

The rule these protect: only a GPU that can actually run inference may
attract the heavy model. Selecting turbo on a card whose CUDA path is
unusable produces the slowest configuration the app can reach (turbo on
CPU), which is worse than simply choosing the small model.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import whisper_local.faster_whisper_backend as backend


class TestCudaCapabilityProbe(unittest.TestCase):
    def setUp(self):
        backend._CUDA_VERIFIED = None
        self.addCleanup(setattr, backend, "_CUDA_VERIFIED", None)
        # Redirect the persisted verdict into a temp dir. Without this the
        # tests write to the real user data dir and leak into each other.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.capability_path = os.path.join(tmp.name, "state", "gpu_capability.json")
        patcher = patch.object(backend, "_capability_file", return_value=self.capability_path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_cuda_device_means_unusable(self):
        with patch.object(backend, "_cudnn_present", return_value=True), patch(
            "ctranslate2.get_cuda_device_count", return_value=0
        ):
            self.assertFalse(backend.gpu_is_usable())

    def test_device_without_cudnn_is_unusable(self):
        # Visible device but no cuDNN: inference would fail at model load and
        # silently demote to CPU, so this must not read as GPU-capable.
        with patch.object(backend, "_cudnn_present", return_value=False), patch(
            "ctranslate2.get_cuda_device_count", return_value=1
        ):
            self.assertFalse(backend.gpu_is_usable())

    def test_device_with_cudnn_is_usable(self):
        with patch.object(backend, "_cudnn_present", return_value=True), patch(
            "ctranslate2.get_cuda_device_count", return_value=1
        ):
            self.assertTrue(backend.gpu_is_usable())

    def test_observed_failure_overrides_optimistic_probe(self):
        backend._record_cuda_outcome("cuda", False)
        with patch.object(backend, "_cudnn_present", return_value=True), patch(
            "ctranslate2.get_cuda_device_count", return_value=1
        ):
            self.assertFalse(backend.gpu_is_usable())

    def test_observed_success_is_remembered(self):
        backend._record_cuda_outcome("cuda", True)
        with patch("ctranslate2.get_cuda_device_count", return_value=0):
            self.assertTrue(backend.gpu_is_usable())

    def test_failure_verdict_persists_across_processes(self):
        # A fresh process must not repeat the optimistic guess, or the app
        # picks the heavy model and fails over to CPU on every single launch.
        import json

        backend._record_cuda_outcome("cuda", False)
        with open(self.capability_path, encoding="utf-8") as f:
            self.assertFalse(json.load(f)["cuda_ok"])

        # Simulate a restart: in-process memory cleared, verdict stands.
        backend._CUDA_VERIFIED = None
        with patch.object(backend, "_cudnn_present", return_value=True), patch(
            "ctranslate2.get_cuda_device_count", return_value=1
        ):
            self.assertFalse(backend.gpu_is_usable())

    def test_stored_verdict_ignored_when_environment_changes(self):
        # Installing cuDNN must not leave the user pinned to CPU forever.
        import json

        os.makedirs(os.path.dirname(self.capability_path), exist_ok=True)
        with open(self.capability_path, "w", encoding="utf-8") as f:
            json.dump({"cuda_ok": False, "signature": "stale-signature"}, f)

        backend._CUDA_VERIFIED = None
        with patch.object(backend, "_cudnn_present", return_value=True), patch(
            "ctranslate2.get_cuda_device_count", return_value=1
        ):
            self.assertTrue(backend.gpu_is_usable())

    def test_cpu_outcomes_do_not_change_cuda_verdict(self):
        backend._record_cuda_outcome("cpu", True)
        self.assertIsNone(backend._CUDA_VERIFIED)
        backend._record_cuda_outcome("cpu", False)
        self.assertIsNone(backend._CUDA_VERIFIED)

    def test_runtime_for_gpu_follows_capability(self):
        with patch.object(backend, "_cuda_runtime_available", return_value=True):
            self.assertEqual(backend.runtime_for_gpu(True), ("cuda", "float16"))
        with patch.object(backend, "_cuda_runtime_available", return_value=False):
            self.assertEqual(backend.runtime_for_gpu(True), ("cpu", "int8"))
        self.assertEqual(backend.runtime_for_gpu(False), ("cpu", "int8"))


class TestModelNameMapping(unittest.TestCase):
    def test_base_maps_to_base_en_and_is_idempotent(self):
        self.assertEqual(backend.model_name_for_mode("base"), "base.en")
        self.assertEqual(backend.model_name_for_mode("base.en"), "base.en")

    def test_everything_else_maps_to_turbo(self):
        for name in ("turbo", "large", "large-v3-turbo", "", None):
            self.assertEqual(backend.model_name_for_mode(name), "turbo")


class TestRepeatCollapse(unittest.TestCase):
    """Whisper loops on noise; nobody dictates the same words three times running."""

    def test_phrase_repeated_three_or_more_times_collapses_to_one(self):
        text, runs = backend.collapse_repeated_ngrams("Thank you. Thank you. Thank you. Thank you.")
        self.assertEqual(text, "Thank you.")
        self.assertEqual(runs, 1)

    def test_two_repeats_are_left_alone(self):
        for text in ("no no", "I said no, no, and no.", "very very good"):
            self.assertEqual(backend.collapse_repeated_ngrams(text), (text, 0))

    def test_case_and_punctuation_are_ignored_and_the_ending_survives(self):
        text, runs = backend.collapse_repeated_ngrams("Thank you, thank you, thank you.")
        self.assertEqual(text, "Thank you.")
        self.assertEqual(runs, 1)

    def test_nested_repeats_collapse_fully(self):
        text, runs = backend.collapse_repeated_ngrams("a a a b a a a b a a a b")
        self.assertEqual(text, "a b")
        self.assertEqual(runs, 4)

    def test_real_text_around_the_loop_is_kept(self):
        text, _ = backend.collapse_repeated_ngrams("send the file now now now now please")
        self.assertEqual(text, "send the file now please")

    def test_lines_are_independent_and_untouched_lines_keep_their_spacing(self):
        text, runs = backend.collapse_repeated_ngrams("hello  world\nyes yes yes")
        self.assertEqual(text, "hello  world\nyes")
        self.assertEqual(runs, 1)

    def test_ngram_length_limit(self):
        six = "one two three four five six"
        seven = six + " seven"
        self.assertEqual(backend.collapse_repeated_ngrams(" ".join([six] * 3))[0], six)
        self.assertEqual(backend.collapse_repeated_ngrams(" ".join([seven] * 3))[1], 0)

    def test_empty_and_short_input(self):
        self.assertEqual(backend.collapse_repeated_ngrams(""), ("", 0))
        self.assertEqual(backend.collapse_repeated_ngrams("ok"), ("ok", 0))


class _Segment:
    def __init__(self, text, avg_logprob=-0.3, no_speech_prob=0.1):
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


class TestSegmentFilter(unittest.TestCase):
    def test_confident_speech_is_kept(self):
        self.assertTrue(backend.segment_is_speech(-0.3, 0.1))

    def test_no_speech_probability_alone_drops(self):
        self.assertFalse(backend.segment_is_speech(-0.3, backend.NO_SPEECH_PROB_MAX + 0.05))

    def test_low_logprob_alone_drops(self):
        self.assertFalse(backend.segment_is_speech(backend.AVG_LOGPROB_MIN - 0.5, 0.1))

    def test_missing_scores_keep_the_segment(self):
        self.assertTrue(backend.segment_is_speech(None, None))
        self.assertTrue(backend.segment_is_speech("n/a", "n/a"))

    def test_filter_reports_counts_without_text(self):
        segments = [
            _Segment(" hello there "),
            _Segment("Thanks for watching!", no_speech_prob=0.9),
            _Segment("   "),
            _Segment("okay", avg_logprob=-2.0),
        ]
        texts, dropped, total = backend.filter_segments(segments)
        self.assertEqual(texts, ["hello there"])
        self.assertEqual(dropped, 2)
        self.assertEqual(total, 4)


class TestTranscribeDecodeGuards(unittest.TestCase):
    def _run(self, segments, vad_available=True):
        model = MagicMock()
        model.transcribe.return_value = (iter(segments), None)
        with patch.object(backend, "preload_model", return_value=(model, "base.en")), patch.object(
            backend, "_vad_filter_available", return_value=vad_available
        ):
            text, ct2_model = backend.transcribe(
                "take.wav", "base", "cpu", "int8", beam_size=1, initial_prompt=""
            )
        return text, ct2_model, model.transcribe.call_args.kwargs

    def test_dictation_decode_settings(self):
        _text, _model, kwargs = self._run([_Segment("hello")])
        self.assertTrue(kwargs["vad_filter"])
        self.assertEqual(kwargs["vad_parameters"], backend.VAD_PARAMETERS)
        self.assertEqual(kwargs["vad_parameters"]["min_silence_duration_ms"], 500)
        self.assertEqual(kwargs["vad_parameters"]["speech_pad_ms"], 200)
        self.assertFalse(kwargs["condition_on_previous_text"])
        self.assertEqual(kwargs["temperature"], 0.0)

    def test_hallucinated_and_looping_segments_do_not_reach_the_text(self):
        segments = [
            _Segment("hello there"),
            _Segment("Thanks for watching!", no_speech_prob=0.9),
            _Segment("ok ok ok ok"),
        ]
        text, ct2_model, _ = self._run(segments)
        self.assertEqual(text, "hello there ok")
        self.assertEqual(ct2_model, "base.en")

    def test_missing_vad_asset_degrades_instead_of_failing(self):
        _text, _model, kwargs = self._run([_Segment("hello")], vad_available=False)
        self.assertFalse(kwargs["vad_filter"])
        self.assertIsNone(kwargs["vad_parameters"])


if __name__ == "__main__":
    unittest.main()
