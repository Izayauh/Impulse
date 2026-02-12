"""Tests for context-aware voice-agent router."""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.agent.router import VoiceAgentRouter


class TestVoiceAgentRouter(unittest.TestCase):
    @patch("whisper_local.agent.router.VoiceAgentRouter._call_ollama")
    def test_transcribe_route_keeps_text(self, mock_call):
        mock_call.return_value = '{"action":"transcribe","filename":null}'
        router = VoiceAgentRouter()
        src = "just transcribe this exactly"
        result = router.process(src)
        self.assertEqual(result.action, "transcribe")
        self.assertEqual(result.output_text, src)
        self.assertTrue(result.handled)

    @patch("whisper_local.agent.router.grammar_check")
    @patch("whisper_local.agent.router.VoiceAgentRouter._call_ollama")
    def test_grammar_route_uses_grammar_tool(self, mock_call, mock_grammar):
        mock_call.return_value = '{"action":"grammar_fix","filename":null}'
        mock_grammar.return_value = "I am testing this."
        router = VoiceAgentRouter()
        result = router.process("i is testing this")
        self.assertEqual(result.action, "grammar_fix")
        self.assertEqual(result.output_text, "I am testing this.")
        mock_grammar.assert_called_once()

    @patch("whisper_local.agent.router.read_project_file")
    @patch("whisper_local.agent.router.VoiceAgentRouter._call_ollama")
    def test_file_command_route_reads_file(self, mock_call, mock_read):
        mock_call.return_value = '{"action":"file_command","filename":"README.md"}'
        mock_read.return_value = "project readme content"
        router = VoiceAgentRouter()
        result = router.process("open readme")
        self.assertEqual(result.action, "file_command")
        self.assertEqual(result.output_text, "project readme content")
        self.assertTrue(result.handled)
        mock_read.assert_called_once_with("README.md")

    @patch("whisper_local.agent.router.VoiceAgentRouter._call_ollama")
    def test_ollama_failure_falls_back(self, mock_call):
        mock_call.side_effect = RuntimeError("ollama unavailable")
        router = VoiceAgentRouter()
        src = "normal text"
        result = router.process(src)
        self.assertEqual(result.action, "transcribe")
        self.assertEqual(result.output_text, src)

    @patch("whisper_local.agent.router.read_project_file")
    @patch("whisper_local.agent.router.VoiceAgentRouter._call_ollama")
    def test_file_command_uses_text_filename_when_missing(self, mock_call, mock_read):
        mock_call.return_value = '{"action":"file_command","filename":null}'
        mock_read.return_value = "ok"
        router = VoiceAgentRouter()
        result = router.process("read README.md")
        self.assertEqual(result.action, "file_command")
        self.assertEqual(result.output_text, "ok")
        mock_read.assert_called_once_with("README.md")


if __name__ == "__main__":
    unittest.main()
