"""StatsController.get_today_words feeds the pill's landed moment."""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.controllers.stats_controller import StatsController


class StatsTodayWordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.controller = StatsController(self.tmp.name, os.path.join(self.tmp.name, "missing.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_store_reads_zero(self):
        self.assertEqual(self.controller.get_today_words(), 0)

    def test_sums_only_todays_takes(self):
        self.controller.record_transcription(5, "base.en", 2.0, 150.0)
        self.controller.record_transcription(7, "base.en", 3.0, 140.0)
        conn = sqlite3.connect(self.controller._db_path)
        conn.execute(
            "INSERT INTO transcription_logs (date, word_count) VALUES ('2000-01-01', 999)"
        )
        conn.commit()
        conn.close()
        self.assertEqual(self.controller.get_today_words(), 12)


if __name__ == "__main__":
    unittest.main()
