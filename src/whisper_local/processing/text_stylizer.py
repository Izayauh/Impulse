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
import os
from typing import Dict
from urllib import error, request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile definitions (ordered for hotkey cycling)
# ---------------------------------------------------------------------------

PROFILE_ORDER: list[str] = ["off", "clean", "polished"]

PROFILES: Dict[str, Dict[str, str]] = {
    "off": {
        "label": "Off",
        "description": "No LLM call — raw transcript passes through.",
        "prompt": "",
    },
    "clean": {
        "label": "Clean",
        "description": "Fillers removed, punctuation restored. No LLM needed.",
        "prompt": "",  # Empty = skip Ollama, rely on existing pipeline
    },
    "polished": {
        "label": "Polished",
        "description": "Light grammar & punctuation polish via local LLM.",
        "prompt": (
            "Fix only grammar, capitalization, and punctuation. "
            "Do not rephrase, reorder, or add any words. "
            "Keep contractions, slang, and the speaker's original vocabulary exactly as-is. "
            "Output only the corrected text, nothing else."
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
        timeout_sec: int | None = None,
        min_words: int | None = None,
    ) -> None:
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout_sec = timeout_sec if timeout_sec is not None else _env_int("WHISPER_STYLIZE_TIMEOUT_SEC", 8)
        self.min_words = min_words if min_words is not None else _env_int("WHISPER_STYLIZE_MIN_WORDS", 12)
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

        if len(text.split()) < self.min_words:
            logger.info(
                "Stylization skipped for short transcript (%s words < %s).",
                len(text.split()),
                self.min_words,
            )
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
                "temperature": 0.15,
                "num_ctx": 1024,
                "num_predict": 160,
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
            with request.urlopen(req, timeout=min(1.0, float(self.timeout_sec))):
                pass
            self._ollama_available = True
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    def reset_availability(self) -> None:
        """Force re-check of Ollama availability on next call."""
        self._ollama_available_checked = False
        self._ollama_available = False


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except ValueError:
        return default
