"""Tests for the anonymous setup-funnel events.

The contract these protect: nothing sends without consent, once-only
events fire once per install, payloads carry no identity or content,
and a dead network can never raise into the app.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import whisper_local.funnel as funnel


class TestFunnelEvents(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.marker = os.path.join(tmp.name, "state", "funnel_sent.json")
        for p in (
            patch.object(funnel, "_marker_file", return_value=self.marker),
            patch.object(funnel, "get_install_id", return_value="11111111-2222-3333-4444-555555555555"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_nothing_sends_without_consent(self):
        with patch.object(funnel, "_consent_given", return_value=False), patch.object(
            funnel.threading, "Thread"
        ) as thread:
            self.assertFalse(funnel.record_funnel_event("first_launch"))
            thread.assert_not_called()
        self.assertFalse(os.path.exists(self.marker))

    def test_invalid_event_rejected(self):
        with patch.object(funnel, "_consent_given", return_value=True), patch.object(
            funnel.threading, "Thread"
        ) as thread:
            self.assertFalse(funnel.record_funnel_event("totally_made_up"))
            thread.assert_not_called()

    def test_once_events_fire_once(self):
        with patch.object(funnel, "_consent_given", return_value=True), patch.object(
            funnel.threading, "Thread"
        ) as thread:
            self.assertTrue(funnel.record_funnel_event("first_launch"))
            self.assertFalse(funnel.record_funnel_event("first_launch"))
            self.assertEqual(thread.call_count, 1)
        sent = json.load(open(self.marker, encoding="utf-8"))
        self.assertIn("first_launch", sent)

    def test_license_blocked_repeats(self):
        # Repeated stalls are the signal; this event is deliberately not once-only.
        with patch.object(funnel, "_consent_given", return_value=True), patch.object(
            funnel.threading, "Thread"
        ) as thread:
            self.assertTrue(funnel.record_funnel_event("license_blocked", {"reason": "not_activated"}))
            self.assertTrue(funnel.record_funnel_event("license_blocked", {"reason": "not_activated"}))
            self.assertEqual(thread.call_count, 2)

    def test_payload_shape_carries_no_identity(self):
        captured = {}

        def fake_thread(target=None, args=(), daemon=None):
            captured["payload"] = args[0]

            class T:
                def start(self):
                    pass

            return T()

        with patch.object(funnel, "_consent_given", return_value=True), patch.object(
            funnel.threading, "Thread", side_effect=fake_thread
        ):
            self.assertTrue(funnel.record_funnel_event("activated"))

        payload = captured["payload"]
        self.assertEqual(
            sorted(payload.keys()),
            ["app_version", "event", "install_id", "os", "props", "ts"],
        )
        self.assertEqual(payload["event"], "activated")
        self.assertEqual(payload["install_id"], "11111111-2222-3333-4444-555555555555")
        serialized = json.dumps(payload)
        self.assertNotIn(os.environ.get("USERNAME", "\x00"), serialized)

    def test_network_failure_never_raises(self):
        with patch.object(funnel.request, "urlopen", side_effect=OSError("no network")):
            funnel._post({"event": "first_launch"})  # must not raise


if __name__ == "__main__":
    unittest.main()


class TestSettingsBomTolerance(unittest.TestCase):
    def test_settings_with_bom_still_load(self):
        # Notepad's "UTF-8" writes a BOM; that must not wipe settings.
        from whisper_local import settings_manager

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "state", "user_settings.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b'\xef\xbb\xbf{"telemetry_enabled": true}')
            sm = settings_manager.SettingsManager(user_data_dir=tmp_dir)
            self.assertTrue(sm.get_setting("telemetry_enabled"))
