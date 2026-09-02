"""Settings page bridge: Ollama probe, version getter, and the dashboard contract."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "whisper_local", "ui")


def _controller(endpoint):
    from whisper_local.controllers.settings_controller import SettingsController

    mgr = MagicMock()
    mgr.get_all.return_value = {"ollama_endpoint": endpoint}
    return SettingsController(mgr, "hotkey.json", "vocab.json", "snippets.json")


class TestOllamaProbe(unittest.TestCase):
    def test_reachable_when_tags_endpoint_answers(self):
        ctl = _controller("http://127.0.0.1:11434/")
        with patch("whisper_local.controllers.settings_controller.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = MagicMock()
            self.assertTrue(ctl.check_ollama())
            req = urlopen.call_args.args[0]
            self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/tags")
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(urlopen.call_args.kwargs.get("timeout"), 0.5)

    def test_unreachable_on_any_error(self):
        ctl = _controller("http://127.0.0.1:11434")
        with patch(
            "whisper_local.controllers.settings_controller.request.urlopen",
            side_effect=OSError("connection refused"),
        ):
            self.assertFalse(ctl.check_ollama())

    def test_unreachable_when_no_endpoint_stored(self):
        ctl = _controller("")
        with patch("whisper_local.controllers.settings_controller.request.urlopen") as urlopen:
            self.assertFalse(ctl.check_ollama())
            urlopen.assert_not_called()

    def test_version_comes_from_config(self):
        from whisper_local.config import APP_VERSION

        self.assertEqual(_controller("").get_app_version(), APP_VERSION)


class TestBridgeExposure(unittest.TestCase):
    def test_root_bridge_exposes_settings_page_helpers(self):
        import whisper_local.ui.gui_host as gui_host
        from whisper_local.config import APP_VERSION

        with tempfile.TemporaryDirectory() as tmp_dir:
            stats_file = os.path.join(tmp_dir, "whisper_stats.json")
            with patch.object(gui_host, "get_user_data_dir", return_value=tmp_dir), patch.object(
                gui_host, "get_app_dir", return_value=tmp_dir
            ), patch.object(gui_host, "STATS_FILE", stats_file):
                api = gui_host.DashboardAPI()
                self.assertEqual(api.get_app_version(), APP_VERSION)
                with patch.object(api.settings, "check_ollama", return_value=False) as probe:
                    self.assertFalse(api.check_ollama())
                    probe.assert_called_once_with()
                # The hotkey path calls this by name; it stays a no-op on the bridge.
                self.assertIsNone(api.open_settings())


class TestDashboardSettingsContract(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(UI_DIR, "dashboard.html"), encoding="utf-8") as f:
            self.html = f.read()
        with open(os.path.join(UI_DIR, "styles.css"), encoding="utf-8") as f:
            self.css = f.read()

    def test_settings_is_a_view_not_a_modal(self):
        self.assertIn("function openSettings()", self.html)
        self.assertIn("switchView('settings')", self.html)
        self.assertIn("function renderSettings()", self.html)
        for removed in ("settings-modal", "closeSettings", "handleModalBackdrop", "modal-open", "primary-btn"):
            self.assertNotIn(removed, self.html, removed)
            self.assertNotIn(removed, self.css, removed)

    def test_settings_view_calls_bridge_helpers(self):
        self.assertIn("a.check_ollama()", self.html)
        self.assertIn("a.get_app_version()", self.html)

    def test_licensing_calls_are_present_and_unchanged(self):
        self.assertIn("activate: (key) => invoke(a => a.licensing ? a.licensing.activate(key) : null)", self.html)
        self.assertIn("deactivate: () => invoke(a => a.licensing ? a.licensing.deactivate() : null)", self.html)
        self.assertIn("getStatus: () => invoke(a => a.licensing ? a.licensing.get_status() : null)", self.html)
        self.assertIn("handleLicenseActivation(key, 'paywall-error')", self.html)
        self.assertIn('id="paywall-overlay"', self.html)
        self.assertIn('id="paywall-key"', self.html)
        self.assertIn('id="settings-license-key"', self.html)


if __name__ == "__main__":
    unittest.main()
