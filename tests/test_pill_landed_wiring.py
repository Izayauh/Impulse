"""The flow lands the pill with this take's words and today's total."""

import os
import queue
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local import flow_local_dictation as flow


class _QtLikePill:
    def show_landed(self, word_count, today_total):
        pass

    def set_status(self, *args):
        pass


class _TkLikePill:
    def set_status(self, *args):
        pass


class PillLandedWiringTest(unittest.TestCase):
    def setUp(self):
        self._saved_gui = getattr(flow, "gui", None)
        self._saved_queue = flow.ui_queue
        flow.ui_queue = queue.Queue()

    def tearDown(self):
        flow.gui = self._saved_gui
        flow.ui_queue = self._saved_queue

    def test_qt_pill_gets_words_and_total(self):
        pill = _QtLikePill()
        flow.gui = pill
        flow._push_landed(42, 1326)
        fn, args = flow.ui_queue.get_nowait()
        self.assertEqual(fn, pill.show_landed)
        self.assertEqual(args, (42, 1326))

    def test_fallback_pill_keeps_pasted_status(self):
        pill = _TkLikePill()
        flow.gui = pill
        flow._push_landed(42, 1326)
        fn, args = flow.ui_queue.get_nowait()
        self.assertEqual(fn, pill.set_status)
        self.assertEqual(args[0], "✅ Pasted!")

    def test_zero_words_does_not_land(self):
        pill = _QtLikePill()
        flow.gui = pill
        flow._push_landed(0, 1326)
        fn, _ = flow.ui_queue.get_nowait()
        self.assertEqual(fn, pill.set_status)


if __name__ == "__main__":
    unittest.main()
