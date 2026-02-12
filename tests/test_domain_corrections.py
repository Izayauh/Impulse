"""
Tests for the domain-specific terminology correction module.

Run with: python -m pytest tests/test_domain_corrections.py -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.domain_corrections import DomainCorrector


class TestAudioEngineeringWhisperOutputs(unittest.TestCase):
    """Real Whisper mis-transcriptions from the spec."""

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_case1_voltage_phantom_power(self):
        self.assertEqual(
            self.c.correct("48 v of phantom power"),
            "48V of Phantom Power",
        )

    def test_case2_gear_names(self):
        self.assertEqual(
            self.c.correct("the shure sm7b"),
            "the Shure SM7B",
        )

    def test_case3_file_format_bit_depth_sample_rate(self):
        self.assertEqual(
            self.c.correct(
                "rendering as a wave file at 24-Bit-depth "
                "48 kilohertz sample rate"
            ),
            "rendering as a WAV file at 24-bit depth 48kHz sample rate",
        )

    def test_case4_thdn_signal_to_noise(self):
        self.assertEqual(
            self.c.correct("thd+n ratings and the signal to noise ratio"),
            "THD+N ratings and the signal-to-noise ratio",
        )

    def test_case5_hpf_hertz_q_factor(self):
        self.assertEqual(
            self.c.correct(
                "high pass filter to 80 hertz and the q factor to 0.7"
            ),
            "high-pass filter to 80Hz and the Q-factor to 0.7",
        )


class TestUnitFormatting(unittest.TestCase):
    """Unit formatting rules in isolation."""

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_voltage_collapse(self):
        self.assertEqual(self.c.correct("48 v"), "48V")

    def test_voltage_already_correct(self):
        self.assertEqual(self.c.correct("48V"), "48V")

    def test_kilohertz_spelled_out(self):
        self.assertEqual(self.c.correct("44 kilohertz"), "44kHz")

    def test_hertz_spelled_out(self):
        self.assertEqual(self.c.correct("80 hertz"), "80Hz")

    def test_khz_abbreviated_with_space(self):
        self.assertEqual(self.c.correct("48 khz"), "48kHz")

    def test_hz_abbreviated_with_space(self):
        self.assertEqual(self.c.correct("20 hz"), "20Hz")

    def test_db_with_space(self):
        self.assertEqual(self.c.correct("gain is 6 db"), "gain is 6dB")

    def test_standalone_khz_casing(self):
        self.assertEqual(self.c.correct("measured in khz"), "measured in kHz")

    def test_standalone_hz_casing(self):
        self.assertEqual(self.c.correct("measured in hz"), "measured in Hz")

    def test_standalone_db_casing(self):
        self.assertEqual(self.c.correct("measured in db"), "measured in dB")


class TestTechnicalTerms(unittest.TestCase):
    """Technical term normalization."""

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_thdn_no_spaces(self):
        self.assertEqual(self.c.correct("thd+n"), "THD+N")

    def test_thdn_with_spaces(self):
        self.assertEqual(self.c.correct("thd + n"), "THD+N")

    def test_signal_to_noise(self):
        self.assertEqual(
            self.c.correct("the signal to noise ratio"),
            "the signal-to-noise ratio",
        )

    def test_high_pass_filter(self):
        self.assertEqual(
            self.c.correct("a high pass filter"),
            "a high-pass filter",
        )

    def test_low_pass_filter(self):
        self.assertEqual(
            self.c.correct("the low pass filter"),
            "the low-pass filter",
        )

    def test_q_factor(self):
        self.assertEqual(self.c.correct("set the q factor"), "set the Q-factor")

    def test_bit_depth_space(self):
        self.assertEqual(self.c.correct("24 bit depth"), "24 bit depth")

    def test_bit_depth_hyphen_removed(self):
        self.assertEqual(self.c.correct("24 bit-depth"), "24 bit depth")

    def test_phantom_power_with_voltage(self):
        """Phantom Power capitalized when voltage context is present."""
        self.assertEqual(
            self.c.correct("48V phantom power"),
            "48V Phantom Power",
        )

    def test_phantom_power_without_voltage(self):
        """Phantom power NOT capitalized without voltage context."""
        self.assertEqual(
            self.c.correct("enable phantom power"),
            "enable phantom power",
        )


class TestFileFormats(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_wave_file(self):
        self.assertEqual(self.c.correct("export as a wave file"), "export as a WAV file")

    def test_wave_format(self):
        self.assertEqual(self.c.correct("the wave format"), "the WAV format")

    def test_mp3_with_space(self):
        self.assertEqual(self.c.correct("convert to mp 3"), "convert to MP3")

    def test_mp3_no_space(self):
        self.assertEqual(self.c.correct("convert to mp3"), "convert to MP3")

    def test_flac(self):
        self.assertEqual(self.c.correct("lossless flac"), "lossless FLAC")


class TestGearBrandNames(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_sm7b(self):
        self.assertEqual(self.c.correct("the sm7b mic"), "the SM7B mic")

    def test_shure(self):
        self.assertEqual(self.c.correct("a shure microphone"), "a Shure microphone")

    def test_xlr(self):
        self.assertEqual(self.c.correct("connect the xlr cable"), "connect the XLR cable")

    def test_already_correct_casing(self):
        self.assertEqual(self.c.correct("the Shure SM7B"), "the Shure SM7B")


class TestProtectedRegions(unittest.TestCase):
    """Corrections must NOT be applied inside quotes or code blocks."""

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_double_quoted_string(self):
        text = 'the setting is "48 v" in the manual'
        result = self.c.correct(text)
        self.assertIn('"48 v"', result)

    def test_inline_code(self):
        text = "run `high pass filter` in the config"
        result = self.c.correct(text)
        self.assertIn("`high pass filter`", result)

    def test_fenced_code_block(self):
        text = "set it up:\n```\n48 v phantom power\n```\nthen test"
        result = self.c.correct(text)
        self.assertIn("48 v phantom power", result)

    def test_text_outside_quotes_still_corrected(self):
        text = 'the shure "sm7b" and the xlr cable'
        result = self.c.correct(text)
        self.assertIn("Shure", result)
        self.assertIn("XLR", result)
        # sm7b inside quotes stays untouched
        self.assertIn('"sm7b"', result)


class TestEdgeCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.c = DomainCorrector(["audio_engineering"])

    def test_empty_string(self):
        self.assertEqual(self.c.correct(""), "")

    def test_none_passthrough(self):
        self.assertEqual(self.c.correct(""), "")

    def test_no_corrections_needed(self):
        text = "This sentence has nothing to correct."
        self.assertEqual(self.c.correct(text), text)

    def test_multiple_corrections_one_sentence(self):
        result = self.c.correct(
            "the shure sm7b uses xlr with 48 v phantom power"
        )
        self.assertIn("Shure", result)
        self.assertIn("SM7B", result)
        self.assertIn("XLR", result)
        self.assertIn("48V", result)
        self.assertIn("Phantom Power", result)

    def test_case_insensitive_input(self):
        self.assertEqual(self.c.correct("SHURE SM7B"), "Shure SM7B")
        self.assertEqual(self.c.correct("THD+N"), "THD+N")


class TestProfileManagement(unittest.TestCase):

    def test_unknown_profile_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DomainCorrector(["nonexistent"])
        self.assertIn("nonexistent", str(ctx.exception))

    def test_empty_profiles_list(self):
        c = DomainCorrector([])
        self.assertEqual(c.correct("48 v"), "48 v")

    def test_duplicate_profile_applies_twice_harmlessly(self):
        c = DomainCorrector(["audio_engineering", "audio_engineering"])
        self.assertEqual(c.correct("48 v"), "48V")


if __name__ == "__main__":
    unittest.main()

