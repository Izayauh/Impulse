"""StatsController reads that feed the Home view (lane 3 of the redesign)."""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.controllers.stats_controller import StatsController


def _day(offset: int) -> str:
    return (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")


class StatsHomeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.controller = StatsController(self.tmp.name, os.path.join(self.tmp.name, "missing.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def _insert(self, date: str, words: int, wpm: float = 0.0) -> None:
        conn = sqlite3.connect(self.controller._db_path)
        conn.execute(
            "INSERT INTO transcription_logs (date, word_count, wpm) VALUES (?, ?, ?)",
            (date, words, wpm),
        )
        conn.commit()
        conn.close()

    # -- 14-day series ------------------------------------------------------

    def test_chart_data_zero_fills_every_day_of_the_window(self):
        data = self.controller.get_chart_data(14)
        self.assertEqual(len(data["dates"]), 14)
        self.assertEqual(len(data["labels"]), 14)
        self.assertEqual(data["datasets"][0]["data"], [0] * 14)
        self.assertEqual(data["dates"][-1], _day(0))
        self.assertEqual(data["dates"][0], _day(13))

    def test_chart_data_places_words_on_their_date_and_sums_takes(self):
        self._insert(_day(0), 5)
        self._insert(_day(0), 7)
        self._insert(_day(3), 40)
        self._insert(_day(13), 9)
        self._insert(_day(14), 999)  # one day outside the window
        data = self.controller.get_chart_data(14)
        series = dict(zip(data["dates"], data["datasets"][0]["data"]))
        self.assertEqual(series[_day(0)], 12)
        self.assertEqual(series[_day(3)], 40)
        self.assertEqual(series[_day(13)], 9)
        self.assertNotIn(_day(14), series)
        self.assertEqual(sum(data["datasets"][0]["data"]), 61)

    # -- today's takes ------------------------------------------------------

    def test_today_takes_counts_only_today(self):
        self.assertEqual(self.controller.get_today_takes(), 0)
        self.controller.record_transcription(5, "base.en", 2.0, 150.0)
        self.controller.record_transcription(7, "base.en", 3.0, 140.0)
        self._insert(_day(1), 50)
        self.assertEqual(self.controller.get_today_takes(), 2)

    # -- best day -----------------------------------------------------------

    def test_best_day_is_zero_with_no_date_on_a_fresh_store(self):
        self.assertEqual(self.controller.get_best_day(), {"words": 0, "date": None})

    def test_best_day_sums_takes_per_date_and_reports_that_date(self):
        self._insert(_day(5), 600)
        self._insert(_day(5), 700)  # 1,300 on one day beats any single take
        self._insert(_day(2), 1000)
        self._insert(_day(0), 100)
        self.assertEqual(self.controller.get_best_day(), {"words": 1300, "date": _day(5)})

    # -- totals and summary -------------------------------------------------

    def test_avg_wpm_ignores_takes_that_measured_no_speed(self):
        self._insert(_day(9), 300, 0.0)  # migrated from JSON, no wpm
        self._insert(_day(0), 10, 120.0)
        self._insert(_day(0), 10, 160.0)
        self.assertEqual(self.controller.get_totals()["avgWpm"], 140)

    def test_avg_wpm_is_zero_when_nothing_was_measured(self):
        self._insert(_day(0), 10, 0.0)
        self.assertEqual(self.controller.get_totals()["avgWpm"], 0)

    def test_home_summary_bundles_the_hero_card_reads(self):
        self._insert(_day(4), 900, 130.0)
        self.controller.record_transcription(20, "base.en", 8.0, 150.0)
        self.controller.record_transcription(30, "base.en", 12.0, 150.0)
        summary = self.controller.get_home_summary()
        self.assertEqual(summary["todayWords"], 50)
        self.assertEqual(summary["todayTakes"], 2)
        self.assertEqual(summary["bestDay"], {"words": 900, "date": _day(4)})
        self.assertEqual(summary["totalWords"], 950)
        self.assertEqual(summary["totalSessions"], 3)
        self.assertEqual(summary["avgWpm"], 143)

    def test_home_summary_is_all_zeros_on_a_fresh_store(self):
        summary = self.controller.get_home_summary()
        self.assertEqual(summary["todayWords"], 0)
        self.assertEqual(summary["todayTakes"], 0)
        self.assertEqual(summary["bestDay"], {"words": 0, "date": None})
        self.assertEqual(summary["totalWords"], 0)
        self.assertEqual(summary["avgWpm"], 0)


if __name__ == "__main__":
    unittest.main()
