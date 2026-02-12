"""Local LLM router for context-aware voice-agent actions."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib import error, request

from tools import get_active_context, grammar_check, read_project_file

LOGGER = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    action: str
    filename: Optional[str] = None


@dataclass
class RouterResult:
    action: str
    output_text: str
    handled: bool
    details: str = ""


class VoiceAgentRouter:
    """Router pattern implementation using local Ollama."""

    VALID_ACTIONS = {"transcribe", "grammar_fix", "file_command"}

    def __init__(
        self,
        model: str = "llama3:8b",
        endpoint: str = "http://127.0.0.1:11434/api/generate",
        timeout_sec: int = 12,
    ) -> None:
        self.model = model
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec

    def process(self, text: str) -> RouterResult:
        if not text or not text.strip():
            return RouterResult(action="transcribe", output_text=text, handled=False)

        decision = self._route(text)
        if decision.action == "grammar_fix":
            return RouterResult(
                action="grammar_fix",
                output_text=grammar_check(text),
                handled=True,
                details="grammar_check",
            )
        if decision.action == "file_command":
            filename = decision.filename or self._extract_filename_from_text(text)
            if not filename:
                LOGGER.warning("file_command selected but no filename could be resolved")
                return RouterResult(action="transcribe", output_text=text, handled=False)
            try:
                file_text = read_project_file(filename)
                return RouterResult(
                    action="file_command",
                    output_text=file_text,
                    handled=True,
                    details=f"read_project_file:{filename}",
                )
            except Exception as exc:
                LOGGER.warning("file_command failed for %s: %s", filename, exc)
                return RouterResult(action="transcribe", output_text=text, handled=False)

        return RouterResult(action="transcribe", output_text=text, handled=True)

    def _route(self, text: str) -> RouterDecision:
        prompt = self._build_prompt(text, get_active_context())
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }

        try:
            raw = self._call_ollama(payload)
            parsed = self._parse_decision(raw)
            if parsed.action in self.VALID_ACTIONS:
                return parsed
        except Exception as exc:
            LOGGER.warning("router call failed; defaulting to transcribe: %s", exc)

        return RouterDecision(action="transcribe")

    def _call_ollama(self, payload: dict) -> str:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_sec) as response:
                content = response.read().decode("utf-8", errors="replace")
        except error.URLError as exc:
            raise RuntimeError(f"ollama unavailable: {exc}") from exc

        response_json = json.loads(content)
        return str(response_json.get("response", "")).strip()

    @staticmethod
    def _build_prompt(text: str, context: str) -> str:
        return (
            "You are a router. Decide one action for the transcript.\n"
            "Allowed actions: transcribe, grammar_fix, file_command.\n"
            "Return JSON only: {\"action\":\"...\",\"filename\":\"...\"}.\n"
            "Use filename only for file_command, else null.\n"
            "Choose grammar_fix if user asks to fix grammar/rewrite text.\n"
            "Choose file_command if user asks to read/open/show a project file.\n"
            "Otherwise choose transcribe.\n"
            f"Context: {context}\n"
            f"Transcript: {text}\n"
        )

    def _parse_decision(self, llm_output: str) -> RouterDecision:
        if not llm_output:
            return RouterDecision(action="transcribe")

        json_blob = self._extract_json_blob(llm_output)
        if json_blob:
            try:
                data = json.loads(json_blob)
                action = str(data.get("action", "transcribe")).strip().lower()
                filename = data.get("filename")
                if isinstance(filename, str):
                    filename = filename.strip() or None
                else:
                    filename = None
                if action in self.VALID_ACTIONS:
                    return RouterDecision(action=action, filename=filename)
            except json.JSONDecodeError:
                pass

        normalized = llm_output.strip().lower()
        if normalized in self.VALID_ACTIONS:
            return RouterDecision(action=normalized)
        return RouterDecision(action="transcribe")

    @staticmethod
    def _extract_json_blob(text: str) -> Optional[str]:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]

    @staticmethod
    def _extract_filename_from_text(text: str) -> Optional[str]:
        patterns = (
            r"\b(?:read|open|show|display)\s+(?:the\s+)?(?:file\s+)?([A-Za-z0-9_.\-\\/]+)",
            r"\b(?:readme|license|changelog)(?:\.md)?\b",
        )
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            if match.lastindex:
                return match.group(1)
            token = match.group(0).strip().lower()
            if token == "readme":
                return "README.md"
            if token == "license":
                return "LICENSE"
            if token == "changelog":
                return "CHANGELOG.md"
            if token == "readme.md":
                return "README.md"
            if token == "changelog.md":
                return "CHANGELOG.md"
        return None
