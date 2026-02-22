"""Lightweight tone/style profiles for transcription refinement via Ollama.

Each profile adjusts the *voice* of the transcript while keeping the original
meaning intact.  When Ollama is unavailable or the profile is ``"off"`` the
raw text passes through unchanged — zero-risk fallback by design.

Usage:
    from whisper_local.processing.text_stylizer import TextStylizer, next_profile

    stylizer = TextStylizer(model="llama3.2:3b")
    result = stylizer.stylize("um so yeah it basically works", "clean")
"""

from __future__ import annotations

import json
import logging
from typing import Dict
from urllib import error, request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile definitions (ordered for hotkey cycling)
# ---------------------------------------------------------------------------

PROFILE_ORDER: list[str] = ["off", "clean", "casual", "formal", "technical"]

PROFILES: Dict[str, Dict[str, str]] = {
    "off": {
        "label": "Off",
        "description": "No LLM call — raw transcript passes through.",
        "prompt": "",
    },
    "clean": {
        "label": "Clean",
        "description": "Grammar & spelling fixes, filler removal.",
        "prompt": (
            "Fix grammar, spelling, and remove filler words (um, uh, like, you know). "
            "Keep the original tone, vocabulary, and sentence structure. "
            "Don't rephrase or add words. Output only the corrected text."
        ),
    },
    "casual": {
        "label": "Casual",
        "description": "Relaxed, conversational tone.",
        "prompt": (
            "Rewrite in a relaxed, conversational tone. Use contractions. "
            "Keep the meaning and all details. Output only the rewritten text."
        ),
    },
    "formal": {
        "label": "Formal",
        "description": "Professional, formal tone.",
        "prompt": (
            "Rewrite in a professional, formal tone. Use complete sentences. "
            "No slang or contractions. Keep the meaning and all details. "
            "Output only the rewritten text."
        ),
    },
    "technical": {
        "label": "Technical",
        "description": "Technical clarity, jargon preserved.",
        "prompt": (
            "Clean up for technical clarity. Preserve jargon, version numbers, "
            "and variable names exactly. Fix grammar and remove filler words. "
            "Output only the cleaned text."
        ),
    },
}


def next_profile(current: str) -> str:
    """Return the next profile in the cycle, wrapping around."""
    try:
        idx = PROFILE_ORDER.index(current)
    except ValueError:
        idx = -1
    return PROFILE_ORDER[(idx + 1) % len(PROFILE_ORDER)]


class TextStylizer:
    """Apply tone/style profiles to transcription text via local Ollama."""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        endpoint: str = "http://127.0.0.1:11434",
        timeout_sec: int = 60,
    ) -> None:
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout_sec = timeout_sec
        self._ollama_available_checked = False
        self._ollama_available = False

    def stylize(self, text: str, profile: str) -> str:
        """Apply *profile* to *text* via Ollama.

        Returns the original text unchanged when:
        - profile is ``"off"``
        - text is empty
        - Ollama is unavailable
        - the LLM call fails for any reason
        """
        if profile == "off" or not text or not text.strip():
            return text

        profile_def = PROFILES.get(profile)
        if not profile_def or not profile_def.get("prompt"):
            return text

        if not self._is_ollama_available():
            logger.warning("Ollama unavailable; stylization skipped.")
            return text

        prompt = f"{profile_def['prompt']}\n\n{text}"
        try:
            result = self._call_ollama(prompt)
            if result and result.strip():
                return result.strip()
            logger.warning("LLM returned empty response; keeping original text.")
            return text
        except Exception as exc:
            logger.warning("Stylization failed; returning original text: %s", exc)
            return text

    # ------------------------------------------------------------------
    # Ollama HTTP helpers
    # ------------------------------------------------------------------

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": 4096,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.endpoint}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except error.URLError as exc:
            raise RuntimeError(f"Ollama unavailable: {exc}") from exc

        data = json.loads(raw)
        return str(data.get("response", "")).strip()

    def _is_ollama_available(self) -> bool:
        if self._ollama_available_checked:
            return self._ollama_available
        self._ollama_available_checked = True
        try:
            req = request.Request(
                f"{self.endpoint}/api/tags",
                method="GET",
            )
            with request.urlopen(req, timeout=3):
                pass
            self._ollama_available = True
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    def reset_availability(self) -> None:
        """Force re-check of Ollama availability on next call."""
        self._ollama_available_checked = False
        self._ollama_available = False
