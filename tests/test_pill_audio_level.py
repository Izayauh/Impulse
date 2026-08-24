"""The HUD's level meter must read on any input device, not just hot consumer mics.

Isaiah's Audient iD14 speaks at roughly RMS 0.002-0.02; a laptop mic with
automatic gain lands near 0.07. The old fixed multiplier only animated the
second case, so the pill looked frozen while he was talking.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.ui.AmbientPill import normalize_level, _LEVEL_FLOOR


def _sweep(peak_speech):
    """Simulate a take: silence, then speech peaking at *peak_speech*."""
    ema = 0.0
    peak = 0.0
    out = []
    # 0.2s of near-silence, then speech that swells and falls
    profile = [0.00012] * 6 + [peak_speech * f for f in (0.3, 0.6, 1.0, 0.8, 0.4)]
    for level in profile:
        ema = 0.8 * ema + 0.2 * level
        peak = max(ema, peak * 0.995)
        out.append(normalize_level(ema, peak))
    return out


class PillAudioLevelTest(unittest.TestCase):
    def test_silence_reads_zero(self):
        self.assertEqual(normalize_level(0.0, 0.05), 0.0)
        self.assertEqual(normalize_level(0.00012, 0.05), 0.0)

    def test_studio_interface_still_swings(self):
        """The regression: a quiet, gain-staged input must animate visibly."""
        levels = _sweep(0.012)
        self.assertGreater(max(levels), 0.5, "quiet studio mic barely moved the bars")

    def test_hot_laptop_mic_still_swings(self):
        levels = _sweep(0.07)
        self.assertGreater(max(levels), 0.5)

    def test_two_devices_land_in_the_same_range(self):
        """Device independence: a 6x louder interface must not read 6x higher."""
        quiet = max(_sweep(0.012))
        loud = max(_sweep(0.07))
        self.assertAlmostEqual(quiet, loud, delta=0.2)

    def test_level_tracks_relative_loudness(self):
        peak = 0.05
        soft = normalize_level(0.01, peak)
        hard = normalize_level(0.045, peak)
        self.assertLess(soft, hard)
        self.assertGreater(soft, 0.0)

    def test_never_exceeds_one(self):
        for ema, peak in ((0.5, 0.1), (1.0, 0.001), (_LEVEL_FLOOR * 3, _LEVEL_FLOOR)):
            self.assertLessEqual(normalize_level(ema, peak), 1.0)
            self.assertGreaterEqual(normalize_level(ema, peak), 0.0)


if __name__ == "__main__":
    unittest.main()
