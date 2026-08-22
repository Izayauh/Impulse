"""Tests for GPU capability detection.

The rule these protect: only a GPU that can actually run inference may
attract the heavy model. Selecting turbo on a card whose CUDA path is
unusable produces the slowest configuration the app can reach (turbo on
CPU), which is worse than simply choosing the small model.
"""

import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import whisper_local.faster_whisper_backend as backend


class TestCudaCapabilityProbe(unittest.TestCase):
    def setUp(self):
        backend._CUDA_VERIFIED = None
        self.addCleanup(setattr, backend, "_CUDA_VERIFIED", None)

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
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "gpu_capability.json")
            with patch.object(backend, "_capability_file", return_value=path):
                backend._record_cuda_outcome("cuda", False)
                with open(path, encoding="utf-8") as f:
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
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "gpu_capability.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"cuda_ok": False, "signature": "stale-signature"}, f)

            with patch.object(backend, "_capability_file", return_value=path):
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


if __name__ == "__main__":
    unittest.main()
