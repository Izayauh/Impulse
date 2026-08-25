"""Some hosts bind Ctrl+V to their own paste and swallow a clipboard paste.

Reported 2026-08-24 while filming the demo: renaming an Ableton track by voice
put something other than the dictated words into the track name, while Impulse
logged "Pasted OK" because it only ever checked that the keystroke was sent.
"""

import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def _load():
    import importlib
    return importlib.import_module("whisper_local.flow_local_dictation")


def _ctx(process_name="", window_title="", window_class=""):
    c = types.SimpleNamespace()
    c.process_name = process_name
    c.window_title = window_title
    c.window_class = window_class
    return c


class PasteTargetTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_daws_are_detected(self):
        for proc in ("ableton live 12 suite.exe", "FL64.exe", "reaper.exe",
                     "Cubase13.exe", "Bitwig Studio.exe"):
            self.assertTrue(
                self.mod._target_swallows_paste(_ctx(process_name=proc.lower())),
                f"{proc} should be typed into, not pasted",
            )

    def test_detects_from_window_title_too(self):
        self.assertTrue(
            self.mod._target_swallows_paste(_ctx(window_title="my song - ableton live 12 suite"))
        )

    def test_ordinary_apps_still_use_the_clipboard(self):
        for proc in ("notepad.exe", "chrome.exe", "code.exe", "slack.exe", "winword.exe"):
            self.assertFalse(
                self.mod._target_swallows_paste(_ctx(process_name=proc)),
                f"{proc} should keep using clipboard paste",
            )

    def test_missing_context_falls_back_to_paste(self):
        self.assertFalse(self.mod._target_swallows_paste(None))
        self.assertFalse(self.mod._target_swallows_paste(_ctx()))

    def test_daw_target_types_and_never_sends_ctrl_v(self):
        with mock.patch.object(self.mod.pyautogui, "write") as write, \
             mock.patch.object(self.mod.pyautogui, "hotkey") as hotkey, \
             mock.patch.object(self.mod.pyperclip, "copy"):
            ok = self.mod.instant_paste("backup vocals", _ctx(process_name="ableton live 12 suite.exe"))
        self.assertTrue(ok)
        write.assert_called_once()
        self.assertEqual(write.call_args[0][0], "backup vocals")
        hotkey.assert_not_called()

    def test_normal_target_still_pastes(self):
        with mock.patch.object(self.mod.pyautogui, "write") as write, \
             mock.patch.object(self.mod.pyautogui, "hotkey") as hotkey, \
             mock.patch.object(self.mod.pyperclip, "copy") as copy:
            ok = self.mod.instant_paste("hello there", _ctx(process_name="notepad.exe"))
        self.assertTrue(ok)
        hotkey.assert_called_once_with("ctrl", "v")
        copy.assert_called_once_with("hello there")
        write.assert_not_called()

    def test_typing_still_leaves_text_on_the_clipboard(self):
        """So the user can paste by hand if the host also filters keystrokes."""
        with mock.patch.object(self.mod.pyautogui, "write"), \
             mock.patch.object(self.mod.pyperclip, "copy") as copy:
            self.mod.type_text("backup vocals")
        copy.assert_called_once_with("backup vocals")


if __name__ == "__main__":
    unittest.main()
