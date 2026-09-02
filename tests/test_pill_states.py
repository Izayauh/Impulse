"""The pill's four moments: listening, working, landed, idle.

Working must not say "processing"; landed shows "+N" and today's total for one
second and then the pill is gone; idle is nothing on screen.
"""

import inspect
import os
import queue
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.ui import AmbientPill as pill_module
from whisper_local.ui.AmbientPill import PillState, is_qt_available


@unittest.skipUnless(is_qt_available(), "PySide6 or PyQt6 not installed")
class PillStatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from whisper_local.ui.AmbientPill import AmbientPill

        cls.pill = AmbientPill(queue.Queue(), is_armed_fn=lambda: True)

    @classmethod
    def tearDownClass(cls):
        cls.pill.close()

    def setUp(self):
        self.pill.set_status("armed")

    def _wait(self, ms):
        from PySide6.QtTest import QTest

        QTest.qWait(ms)

    def test_working_has_no_processing_text(self):
        self.pill.set_status("⚙️ Transcribing...")
        self.assertEqual(self.pill._state, PillState.PROCESSING)
        self.assertTrue(self.pill.isVisible())
        self.pill.grab()  # exercises the sweep and arc drawing
        source = inspect.getsource(pill_module)
        self.assertNotIn('"Processing', source)

    def test_landed_shows_counts_then_hides(self):
        self.pill.set_status("⚙️ Transcribing...")
        self.pill.show_landed(42, 1326)
        self.assertEqual(self.pill._state, PillState.LANDED)
        self.assertTrue(self.pill.isVisible())
        self.assertEqual(self.pill._landed_words, 42)
        self.assertEqual(self.pill._landed_total, 1326)
        self.pill.grab()  # exercises the check and text drawing
        self._wait(pill_module._LANDED_MS + 300)
        self.assertEqual(self.pill._state, PillState.ARMED)
        self.assertFalse(self.pill.isVisible(), "pill stayed on screen after the landed second")

    def test_zero_words_never_lands(self):
        self.pill.set_status("⚙️ Transcribing...")
        self.pill.show_landed(0, 500)
        self.assertEqual(self.pill._state, PillState.ARMED)
        self.assertFalse(self.pill.isVisible())

    def test_new_recording_cancels_landed_timer(self):
        self.pill.show_landed(3, 10)
        self.pill.set_status("recording")
        self.assertEqual(self.pill._state, PillState.RECORDING)
        self._wait(pill_module._LANDED_MS + 300)
        self.assertEqual(self.pill._state, PillState.RECORDING, "landed timer hid a live recording")

    def test_idle_is_hidden(self):
        self.pill.show_landed(5, 5)
        self.pill.set_status("idle")
        self.assertFalse(self.pill.isVisible())
        self.assertFalse(self.pill._landed_timer.isActive())


if __name__ == "__main__":
    unittest.main()
