"""dashboard_stats.js ships inside the installer, so it must never carry real usage.

It was previously an export of a real profile: one person's dictated text and
stats were distributed to every user, and the dashboard renders this file
whenever the bridge has not supplied live stats yet.
"""

import json
import os
import re
import unittest

UI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "whisper_local", "ui",
)
STATS_FILE = os.path.join(UI_DIR, "dashboard_stats.js")


def _load_stats():
    raw = open(STATS_FILE, encoding="utf-8").read()
    m = re.search(r"window\.WHISPER_STATS\s*=\s*(\{.*?\});", raw, re.S)
    assert m, "could not find WHISPER_STATS object"
    return json.loads(m.group(1)), raw


class ShippedDemoDataTest(unittest.TestCase):
    def test_no_transcripts_are_shipped(self):
        stats, _ = _load_stats()
        self.assertEqual(
            stats.get("recentTranscripts"), [],
            "shipped demo data must not contain dictated text",
        )

    def test_usage_counters_are_zeroed(self):
        stats, _ = _load_stats()
        for field in ("totalWords", "totalSessions", "bestWpm", "dayStreak", "thisWeek"):
            self.assertEqual(stats.get(field), 0, f"{field} looks like real usage")

    def test_seven_day_series_has_seven_distinct_days(self):
        """The old export listed Sunday twice and omitted Saturday."""
        stats, _ = _load_stats()
        days = [d["day"] for d in stats["last7Days"]]
        self.assertEqual(len(days), 7)
        self.assertEqual(len(set(days)), 7, f"duplicate weekday in {days}")

    def test_no_stale_product_name(self):
        _, raw = _load_stats()
        self.assertNotIn("WhisperLocal", raw)


if __name__ == "__main__":
    unittest.main()
