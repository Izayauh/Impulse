"""
Tests for the numeric formatting module.

Run with: python -m pytest tests/test_numeric_formatter.py -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.processing.numeric_formatter import format_numbers


class TestWhisperOutputCases(unittest.TestCase):
    """Real Whisper output from the spec."""

    def test_ip_with_port(self):
        self.assertEqual(
            format_numbers("127. 0. 0. 1: 8080"),
            "127.0.0.1:8080",
        )

    def test_decimal(self):
        self.assertEqual(
            format_numbers("the Q-factor to 0. 7"),
            "the Q-factor to 0.7",
        )

    def test_sentence_boundary_preserved(self):
        self.assertEqual(
            format_numbers("I said 3. Next we moved on"),
            "I said 3. Next we moved on",
        )


class TestIPAddresses(unittest.TestCase):

    def test_fully_spaced(self):
        self.assertEqual(
            format_numbers("192. 168. 1. 1"),
            "192.168.1.1",
        )

    def test_mixed_spacing(self):
        self.assertEqual(
            format_numbers("10 .0. 0 .1"),
            "10.0.0.1",
        )

    def test_with_spaced_port(self):
        self.assertEqual(
            format_numbers("10. 0. 0. 1 : 443"),
            "10.0.0.1:443",
        )

    def test_already_correct(self):
        self.assertEqual(
            format_numbers("127.0.0.1:8080"),
            "127.0.0.1:8080",
        )

    def test_ip_no_port(self):
        self.assertEqual(
            format_numbers("connect to 192. 168. 1. 100 and test"),
            "connect to 192.168.1.100 and test",
        )

    def test_ip_in_sentence(self):
        self.assertEqual(
            format_numbers("the server at 10. 0. 0. 1 is down"),
            "the server at 10.0.0.1 is down",
        )


class TestPortNumbers(unittest.TestCase):

    def test_port_after_ip_no_space(self):
        self.assertEqual(
            format_numbers("127. 0. 0. 1:8080"),
            "127.0.0.1:8080",
        )

    def test_port_after_ip_with_space(self):
        self.assertEqual(
            format_numbers("127. 0. 0. 1 :8080"),
            "127.0.0.1:8080",
        )

    def test_port_both_spaces(self):
        self.assertEqual(
            format_numbers("127. 0. 0. 1 : 8080"),
            "127.0.0.1:8080",
        )

    def test_time_format_untouched(self):
        """5:30 is a time, not a port — must not be altered."""
        self.assertEqual(
            format_numbers("at 5:30 in the morning"),
            "at 5:30 in the morning",
        )

    def test_standalone_colon_number_untouched(self):
        """A colon+number without an IP prefix must not collapse."""
        self.assertEqual(
            format_numbers("chapter 1: 8 tips"),
            "chapter 1: 8 tips",
        )


class TestDecimalNumbers(unittest.TestCase):

    def test_space_after_dot(self):
        self.assertEqual(format_numbers("0. 7"), "0.7")

    def test_space_before_dot(self):
        self.assertEqual(format_numbers("0 .7"), "0.7")

    def test_space_both_sides(self):
        self.assertEqual(format_numbers("0 . 7"), "0.7")

    def test_already_correct(self):
        self.assertEqual(format_numbers("3.14"), "3.14")

    def test_decimal_in_sentence(self):
        self.assertEqual(
            format_numbers("gain of 6. 5 dB"),
            "gain of 6.5 dB",
        )

    def test_multiple_decimals(self):
        self.assertEqual(
            format_numbers("between 0. 7 and 1. 5"),
            "between 0.7 and 1.5",
        )

    def test_pi(self):
        self.assertEqual(
            format_numbers("pi is about 3. 14159"),
            "pi is about 3.14159",
        )


class TestVersionNumbers(unittest.TestCase):

    def test_three_part(self):
        self.assertEqual(
            format_numbers("Python 3. 11. 4"),
            "Python 3.11.4",
        )

    def test_already_correct(self):
        self.assertEqual(
            format_numbers("version 3.11.4"),
            "version 3.11.4",
        )

    def test_two_part_version(self):
        self.assertEqual(
            format_numbers("node 18. 17"),
            "node 18.17",
        )


class TestSentenceBoundaries(unittest.TestCase):
    """Periods that end a sentence must NOT be collapsed."""

    def test_next_word_capitalized(self):
        self.assertEqual(
            format_numbers("I said 3. Next we moved on"),
            "I said 3. Next we moved on",
        )

    def test_digit_then_uppercase_word(self):
        self.assertEqual(
            format_numbers("item 3. The next step"),
            "item 3. The next step",
        )

    def test_no_digit_after_period(self):
        """Period followed by a letter — never matched by the regex."""
        self.assertEqual(
            format_numbers("count is 5. That is all"),
            "count is 5. That is all",
        )

    def test_digit_then_lowercase_collapses(self):
        """When followed by lowercase, it's almost certainly a decimal."""
        self.assertEqual(
            format_numbers("factor of 2. 5 times"),
            "factor of 2.5 times",
        )


class TestEdgeCases(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(format_numbers(""), "")

    def test_no_numbers(self):
        text = "Hello world, this has no numbers."
        self.assertEqual(format_numbers(text), text)

    def test_ip_then_sentence(self):
        """IP followed by a normal sentence — period stays."""
        self.assertEqual(
            format_numbers("server 192. 168. 1. 1. Check the logs"),
            "server 192.168.1.1. Check the logs",
        )

    def test_does_not_extend_collapsed_ip(self):
        """After IP collapse, a trailing '. 2' must not merge into the IP."""
        result = format_numbers("192. 168. 1. 1. 2 things")
        # IP collapses to 192.168.1.1, then ". 2" — "2" followed by
        # lowercase "things" so it would collapse, but the lookbehind
        # (preceded by ".") prevents it.
        self.assertIn("192.168.1.1", result)
        # "1" and "2" must NOT merge
        self.assertNotIn("1.2", result)


if __name__ == "__main__":
    unittest.main()

