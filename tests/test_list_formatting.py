"""List formatting must never fire on incidental speech, and must never drop words.

Reported 2026-08-24: Isaiah dictates his prompts with Impulse, and sentences
containing the ordinary word "list" came out as bullet lists with everything
before "list" deleted.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.flow_local_dictation import to_bullets, to_numbered_list


class IncidentalSpeechTest(unittest.TestCase):
    """The regression: ordinary sentences that merely contain the trigger words."""

    UNTOUCHED = [
        "I'm trying to figure out the list of people to actually send this email campaign to",
        "the bullet pointed list that's happening right now is really weird",
        "can you check the list and tell me what you think",
        "I need to number the takes before I mix them",
        "put it on the shortlist for next week",
        "the numbered list in the docs is out of date",
    ]

    def test_incidental_mentions_are_left_alone(self):
        for line in self.UNTOUCHED:
            self.assertEqual(to_bullets(line), line, f"to_bullets mangled: {line}")
            self.assertEqual(to_numbered_list(line), line, f"to_numbered_list mangled: {line}")

    def test_no_words_are_ever_dropped_silently(self):
        line = "I'm trying to figure out the list of people to email"
        self.assertIn("figure out", to_bullets(line))


class ExplicitCommandTest(unittest.TestCase):
    def test_bullet_command_still_works(self):
        out = to_bullets("bullet list eggs, milk and bread")
        self.assertEqual(out, "• Eggs\n• Milk\n• Bread")

    def test_bullet_command_with_polite_prefix(self):
        out = to_bullets("please make a bulleted list of eggs, milk and bread")
        self.assertEqual(out, "• Eggs\n• Milk\n• Bread")

    def test_numbered_command_still_works(self):
        out = to_numbered_list("numbered list mix, master and release")
        self.assertEqual(out, "1. Mix\n2. Master\n3. Release")

    def test_single_item_is_left_untouched_rather_than_trimmed(self):
        """Ambiguous single-item cases keep every dictated word."""
        self.assertEqual(to_bullets("bullet list eggs"), "bullet list eggs")


if __name__ == "__main__":
    unittest.main()
