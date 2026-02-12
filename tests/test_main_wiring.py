"""Tests for Step 3 main wiring (ContextAwareAgent)."""

import unittest
from unittest.mock import patch

import main


class _FakeRouter:
    def __init__(self, action, answer="ok"):
        self._action = action
        self._answer = answer
        self.calls = []

    def route(self, raw_text, current_file_context):
        self.calls.append(("route", raw_text, current_file_context))
        return self._action

    def answer_with_file_context(self, user_text, file_content, current_file_context, filename=""):
        self.calls.append(("answer", user_text, file_content, current_file_context, filename))
        return self._answer


class _FailingAnswerRouter(_FakeRouter):
    def answer_with_file_context(self, user_text, file_content, current_file_context, filename=""):
        raise RuntimeError("ollama offline")


class TestContextAwareAgent(unittest.TestCase):
    def test_transcribe_intent_passthrough(self):
        agent = main.ContextAwareAgent(router=_FakeRouter({"intent": "transcribe", "tool": "none", "args": {}}))
        out, handled, action = agent.handle("raw whisper text", "main.py")
        self.assertEqual(out, "raw whisper text")
        self.assertTrue(handled)
        self.assertEqual(action, "transcribe")

    @patch("main.grammar_check")
    def test_correction_intent_uses_grammar_tool(self, mock_grammar):
        mock_grammar.return_value = "I am testing."
        agent = main.ContextAwareAgent(router=_FakeRouter({"intent": "correction", "tool": "grammar_tool", "args": {}}))
        out, handled, action = agent.handle("i is testing", "notes.txt")
        self.assertEqual(out, "I am testing.")
        self.assertTrue(handled)
        self.assertEqual(action, "correction")
        mock_grammar.assert_called_once_with("i is testing")

    @patch("main.read_project_file")
    def test_command_intent_reads_file_and_answers_with_llm(self, mock_read):
        mock_read.return_value = "README file body"
        router = _FakeRouter(
            {"intent": "command", "tool": "read_file", "args": {"filename": "README.md"}},
            answer="Summary from file",
        )
        agent = main.ContextAwareAgent(router=router)
        out, handled, action = agent.handle("read README", "main.py")
        self.assertEqual(out, "Summary from file")
        self.assertTrue(handled)
        self.assertTrue(action.startswith("command"))
        mock_read.assert_called_once_with("README.md")
        self.assertTrue(any(call[0] == "answer" for call in router.calls))

    @patch("main.read_project_file")
    def test_command_missing_filename_falls_back(self, mock_read):
        agent = main.ContextAwareAgent(
            router=_FakeRouter({"intent": "command", "tool": "read_file", "args": {}})
        )
        out, handled, action = agent.handle("do command please", "main.py")
        self.assertEqual(out, "do command please")
        self.assertFalse(handled)
        self.assertEqual(action, "command_missing_filename")
        mock_read.assert_not_called()

    @patch("main.read_project_file")
    def test_command_ollama_failure_falls_back_to_raw_transcription(self, mock_read):
        mock_read.return_value = "README file body"
        agent = main.ContextAwareAgent(
            router=_FailingAnswerRouter({"intent": "command", "tool": "read_file", "args": {"filename": "README.md"}})
        )
        out, handled, action = agent.handle("summarize README", "main.py")
        self.assertEqual(out, "summarize README")
        self.assertFalse(handled)
        self.assertEqual(action, "command_failed")


if __name__ == "__main__":
    unittest.main()
