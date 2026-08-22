"""Dashboard host wiring and refresh-path tests."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


class TestDashboardOpenWiring(unittest.TestCase):
    @patch("whisper_local.flow_local_dictation.threading.Thread")
    def test_shared_launcher_spawns_thread_with_gui_host_open_dashboard(self, mock_thread):
        import whisper_local.flow_local_dictation as flow

        thread_instance = MagicMock()
        mock_thread.return_value = thread_instance

        flow._launch_dashboard_from_ui_trigger()

        mock_thread.assert_called_once()
        _, kwargs = mock_thread.call_args
        self.assertIs(kwargs.get("target"), flow.open_dashboard)
        self.assertTrue(kwargs.get("daemon"))
        thread_instance.start.assert_called_once()

    @patch("whisper_local.flow_local_dictation._launch_dashboard_from_ui_trigger")
    def test_tray_dashboard_action_routes_through_shared_launcher(self, mock_launch):
        from whisper_local.flow_local_dictation import _tray_open_dashboard

        _tray_open_dashboard()
        mock_launch.assert_called_once_with()

    @patch("whisper_local.flow_local_dictation._launch_dashboard_from_ui_trigger")
    def test_pill_dashboard_action_routes_through_shared_launcher(self, mock_launch):
        from whisper_local.flow_local_dictation import FloatingPill

        pill = object.__new__(FloatingPill)
        FloatingPill._open_dashboard(pill)
        mock_launch.assert_called_once_with()


class TestDashboardSpawnProcess(unittest.TestCase):
    @patch("whisper_local.ui.gui_host.subprocess.Popen")
    @patch("whisper_local.ui.gui_host.os.path.isfile", return_value=True)
    def test_spawn_uses_bootstrap_script_when_available(self, _mock_isfile, mock_popen):
        import whisper_local.ui.gui_host as gui_host

        with patch.object(gui_host.sys, "executable", "python.exe"):
            ok = gui_host._spawn_dashboard_process()

        self.assertTrue(ok)
        cmd = mock_popen.call_args.args[0]
        kwargs = mock_popen.call_args.kwargs
        self.assertEqual(cmd[0], "python.exe")
        self.assertTrue(cmd[1].endswith("gui_host.py"))
        self.assertIn("env", kwargs)

    @patch("whisper_local.ui.gui_host.subprocess.Popen")
    @patch("whisper_local.ui.gui_host.os.path.isfile", return_value=False)
    def test_spawn_falls_back_to_module_and_sets_src_pythonpath(self, _mock_isfile, mock_popen):
        import whisper_local.ui.gui_host as gui_host

        ok = gui_host._spawn_dashboard_process()

        self.assertTrue(ok)
        cmd = mock_popen.call_args.args[0]
        kwargs = mock_popen.call_args.kwargs
        self.assertEqual(cmd[1:], ["-m", "whisper_local.ui.gui_host"])
        self.assertIn("env", kwargs)
        expected_src = os.path.join(os.path.dirname(gui_host._dashboard_bootstrap_script()), "src")
        self.assertIn(expected_src, kwargs["env"].get("PYTHONPATH", ""))


class TestDashboardRealtimeRefreshPath(unittest.TestCase):
    def test_dashboard_api_reflects_stats_tracker_updates_between_polls(self):
        from whisper_local.stats import StatsTracker
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            stats_file = os.path.join(tmp_dir, "whisper_stats.json")
            tracker = StatsTracker(stats_file=stats_file)

            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "STATS_FILE", stats_file
            ):
                api = gui_host.DashboardAPI()

                initial_total = api.get_stats()["totalWords"]

                tracker.record_transcription("alpha beta gamma", "base.en")
                first_total = api.get_stats()["totalWords"]

                tracker.record_transcription("delta epsilon", "base.en")
                second_total = api.get_stats()["totalWords"]

                self.assertEqual(first_total, initial_total + 3)
                self.assertEqual(second_total, first_total + 2)

                recent = api.get_transcription_history()
                self.assertGreaterEqual(len(recent), 1)
                self.assertEqual(recent[0]["fullText"], "delta epsilon")

                ping = api.bridge_ping()
                self.assertTrue(ping.get("ok"))
                self.assertEqual(ping.get("bridge"), "pywebview")

    def test_dashboard_api_migrates_legacy_stats_into_canonical_state_file(self):
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            canonical_stats = os.path.join(tmp_dir, "state", "whisper_stats.json")
            legacy_stats = os.path.join(tmp_dir, "whisper_stats.json")
            os.makedirs(os.path.dirname(canonical_stats), exist_ok=True)

            with open(canonical_stats, "w", encoding="utf-8") as f:
                f.write('{"total_words": 0, "daily_words": {}}')

            with open(legacy_stats, "w", encoding="utf-8") as f:
                f.write(
                    '{"total_words": 321, "total_sessions": 9, "daily_words": {"2026-02-08": 120}, "recent_transcripts": []}'
                )

            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", canonical_stats), patch.object(
                gui_host, "_migration_completed", False
            ):
                api = gui_host.DashboardAPI()
                stats = api.get_stats()

                self.assertEqual(stats["totalWords"], 321)

                with open(canonical_stats, "r", encoding="utf-8") as f:
                    saved = f.read()
                self.assertIn('"total_words": 321', saved)

    def test_dashboard_api_migrates_legacy_achievements_into_state_file(self):
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            canonical_stats = os.path.join(tmp_dir, "state", "whisper_stats.json")
            canonical_ach = os.path.join(tmp_dir, "state", "whisper_achievements.json")
            legacy_ach = os.path.join(tmp_dir, "whisper_achievements.json")
            os.makedirs(os.path.dirname(canonical_stats), exist_ok=True)

            with open(canonical_stats, "w", encoding="utf-8") as f:
                f.write('{"total_words": 1, "daily_words": {"2026-02-08": 1}}')
            with open(canonical_ach, "w", encoding="utf-8") as f:
                f.write('{"unlocked": []}')
            with open(legacy_ach, "w", encoding="utf-8") as f:
                f.write('{"unlocked": ["daily_100", "total_1k"]}')

            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", canonical_stats), patch.object(
                gui_host, "_migration_completed", False
            ):
                api = gui_host.DashboardAPI()
                unlocked = api.get_achievements()

                self.assertEqual(set(unlocked), {"daily_100", "total_1k"})

                with open(canonical_ach, "r", encoding="utf-8") as f:
                    saved = f.read()
                self.assertIn('"daily_100"', saved)

    def test_dashboard_model_mode_is_hardware_aware(self):
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            canonical_stats = os.path.join(tmp_dir, "state", "whisper_stats.json")
            os.makedirs(os.path.dirname(canonical_stats), exist_ok=True)
            with open(canonical_stats, "w", encoding="utf-8") as f:
                f.write('{"total_words": 1, "daily_words": {"2026-02-08": 1}}')

            high_vram_info = type("GpuInfo", (), {"memory_total_mb": 12288.0})()
            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", canonical_stats), patch.object(
                gui_host, "_migration_completed", False
            ), patch.object(gui_host, "gpu_monitor", MagicMock(get_gpu_info=MagicMock(return_value=high_vram_info))):
                api = gui_host.DashboardAPI()

                # Retired modes coerce to auto; a 12 GB GPU resolves auto to turbo.
                for requested in ("medium", "fast", "auto"):
                    payload = api.set_model_mode(requested)
                    self.assertEqual(payload["mode"], "auto")
                    self.assertEqual(payload["activeModel"], "turbo")
                    self.assertEqual(payload["engine"], "faster-whisper")

                # Manual pins are honored as-is.
                payload = api.set_model_mode("turbo")
                self.assertEqual(payload["mode"], "turbo")
                self.assertEqual(payload["activeModel"], "turbo")

                payload = api.set_model_mode("base")
                self.assertEqual(payload["mode"], "base")
                self.assertEqual(payload["manualModel"], "base")
                self.assertEqual(payload["activeModel"], "base")
                self.assertEqual(payload["profile"], "base")

    def test_dashboard_model_mode_auto_picks_base_without_gpu(self):
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            canonical_stats = os.path.join(tmp_dir, "state", "whisper_stats.json")
            os.makedirs(os.path.dirname(canonical_stats), exist_ok=True)
            with open(canonical_stats, "w", encoding="utf-8") as f:
                f.write('{"total_words": 1, "daily_words": {"2026-02-08": 1}}')

            no_gpu_info = type("GpuInfo", (), {"memory_total_mb": 0.0})()
            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", canonical_stats), patch.object(
                gui_host, "_migration_completed", False
            ), patch.object(gui_host, "gpu_monitor", MagicMock(get_gpu_info=MagicMock(return_value=no_gpu_info))):
                api = gui_host.DashboardAPI()

                payload = api.set_model_mode("auto")
                self.assertEqual(payload["mode"], "auto")
                self.assertEqual(payload["activeModel"], "base")
                self.assertEqual(payload["profile"], "base")

    def test_dashboard_vocabulary_add_word_persists(self):
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            canonical_stats = os.path.join(tmp_dir, "state", "whisper_stats.json")
            os.makedirs(os.path.dirname(canonical_stats), exist_ok=True)
            with open(canonical_stats, "w", encoding="utf-8") as f:
                f.write('{"total_words": 1, "daily_words": {"2026-02-08": 1}}')

            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", canonical_stats), patch.object(
                gui_host, "_migration_completed", False
            ):
                api = gui_host.DashboardAPI()

                first = api.add_vocabulary_word("Ableton")
                self.assertTrue(first["ok"])
                self.assertTrue(first["added"])
                self.assertIn("Ableton", first["words"])

                second = api.add_vocabulary_word("ableton")
                self.assertTrue(second["ok"])
                self.assertFalse(second["added"])
                self.assertEqual(second["words"], ["Ableton"])

    def test_dashboard_hotkey_set_and_get_persists(self):
        import whisper_local.ui.gui_host as gui_host

        with tempfile.TemporaryDirectory() as tmp_dir:
            canonical_stats = os.path.join(tmp_dir, "state", "whisper_stats.json")
            os.makedirs(os.path.dirname(canonical_stats), exist_ok=True)
            with open(canonical_stats, "w", encoding="utf-8") as f:
                f.write('{"total_words": 1, "daily_words": {"2026-02-08": 1}}')

            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", canonical_stats), patch.object(
                gui_host, "_migration_completed", False
            ):
                api = gui_host.DashboardAPI()
                updated = api.set_hotkey("alt+space")
                self.assertTrue(updated["ok"])
                self.assertEqual(updated["hotkey"], "alt+space")

                current = api.get_hotkey()
                self.assertTrue(current["ok"])
                self.assertEqual(current["hotkey"], "alt+space")


if __name__ == "__main__":
    unittest.main()
