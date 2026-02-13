"""Snippet storage and retrieval for WhisperLocal.

Persists text-replacement shortcuts to ``snippets.json``
in the user state directory.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List

from whisper_local.config import get_user_data_dir

log = logging.getLogger(__name__)

# Minimum similarity for fuzzy snippet trigger matching.
_FUZZY_SNIPPET_THRESHOLD = 0.80


def snippets_file(user_data_dir: str | None = None) -> str:
    base = user_data_dir or get_user_data_dir()
    return os.path.join(base, "state", "snippets.json")


def load_snippets(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, IOError):
        return []
    if isinstance(data, dict):
        items = data.get("snippets", [])
    elif isinstance(data, list):
        items = data
    else:
        return []
    return [s for s in items if isinstance(s, dict) and s.get("trigger")]


def save_snippets(path: str, items: List[Dict[str, Any]]) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"snippets": items}, f, indent=2)
        return True
    except (OSError, IOError):
        return False


def add_snippet(path: str, trigger: str, replacement: str, scope: str = "personal") -> Dict[str, Any]:
    trigger = str(trigger or "").strip()
    replacement = str(replacement or "").strip()
    if not trigger or not replacement:
        return {"ok": False, "error": "Trigger and replacement are required"}

    items = load_snippets(path)
    new_id = int(time.time() * 1000)
    entry = {
        "id": new_id,
        "scope": scope,
        "trigger": trigger,
        "replacement": replacement,
    }
    items.insert(0, entry)
    save_snippets(path, items)
    return {"ok": True, "snippet": entry, "snippets": items}


def delete_snippet(path: str, snippet_id: int) -> Dict[str, Any]:
    items = load_snippets(path)
    before = len(items)
    items = [s for s in items if s.get("id") != snippet_id]
    if len(items) == before:
        return {"ok": False, "error": "Snippet not found"}
    save_snippets(path, items)
    return {"ok": True, "snippets": items}


def _is_literal_value(s: str) -> bool:
    """Return True if *s* looks like a path, variable, or non-prose token."""
    return bool(re.search(r"[\\/_]", s)) or " " not in s


def apply_snippets(text: str, path: str) -> str:
    """Apply snippet trigger->replacement substitutions to transcribed text.

    Two-pass matching:
    1. Exact regex matching (case-insensitive, word-boundary).
    2. Fuzzy matching via sliding word windows to catch Whisper
       misrecognitions of trigger phrases.

    Longer triggers are applied first so that "Whisper Local Directory"
    matches before "Whisper Local" would.

    When the replacement is a literal value (file path, variable name, etc.),
    any trailing sentence punctuation that the post-processor appended to the
    trigger phrase is absorbed so it doesn't stick to the replacement.
    """
    if not text:
        return text
    items = load_snippets(path)
    if not items:
        return text

    log.debug("[snippets] loaded %d snippets from disk", len(items))

    # Sort by trigger length descending so longer triggers match first.
    items.sort(key=lambda s: len(s.get("trigger", "")), reverse=True)

    # Pass 1: exact regex matching (existing behaviour).
    for s in items:
        trigger = s.get("trigger", "")
        replacement = s.get("replacement", "")
        if not trigger:
            continue
        # Match the trigger phrase and capture any trailing punctuation.
        pattern = r"(?i)\b" + re.escape(trigger) + r"\b([.,;:!?])?"
        literal = _is_literal_value(replacement)

        def _repl(m: re.Match, _rep: str = replacement, _lit: bool = literal) -> str:
            punct = m.group(1) or ""
            # Keep trailing punctuation for prose replacements; drop it for
            # paths / variables / other literal values.
            return _rep if _lit else _rep + punct

        text = re.sub(pattern, _repl, text)

    # Pass 2: fuzzy matching for triggers Whisper misrecognised.
    text = _fuzzy_snippet_pass(text, items)

    return text


def _fuzzy_snippet_pass(text: str, items: List[Dict[str, Any]]) -> str:
    """Replace near-miss transcriptions of snippet triggers.

    Tries same-size and expanded windows (n+1, n+2) to handle Whisper
    word-splitting.  Expanded windows are concatenated (spaces removed)
    before comparison so that "able ton" matches "Ableton".
    """
    text_words = text.split()
    if not text_words:
        return text

    replaced: set[int] = set()

    for s in items:
        trigger = s.get("trigger", "")
        replacement = s.get("replacement", "")
        if not trigger:
            continue

        trigger_tokens = trigger.split()
        n = len(trigger_tokens)
        if n == 0:
            continue
        trigger_lower = trigger.lower()
        trigger_concat = trigger_lower.replace(" ", "")
        literal = _is_literal_value(replacement)

        window_sizes = [n]
        if n + 1 <= len(text_words):
            window_sizes.append(n + 1)
        if n + 2 <= len(text_words):
            window_sizes.append(n + 2)

        best_match = None  # (start_idx, win_size, score, window_text)

        for ws in window_sizes:
            for i in range(len(text_words) - ws + 1):
                if any(j in replaced for j in range(i, i + ws)):
                    continue

                window = " ".join(text_words[i : i + ws])
                window_lower = window.lower()

                if window_lower == trigger_lower:
                    continue

                # Skip if the window already contains the trigger as a
                # substring (already handled by pass 1).
                if trigger_lower in window_lower:
                    continue

                if ws == n:
                    ratio = SequenceMatcher(None, window_lower, trigger_lower).ratio()
                else:
                    window_concat = window_lower.replace(" ", "")
                    ratio = SequenceMatcher(None, window_concat, trigger_concat).ratio()

                if ratio >= _FUZZY_SNIPPET_THRESHOLD:
                    if best_match is None or ratio > best_match[2]:
                        best_match = (i, ws, ratio, window)

        if best_match is not None:
            i, ws, ratio, window = best_match
            trail_punct = ""
            last_word = text_words[i + ws - 1]
            if last_word and last_word[-1] in ".,;:!?":
                trail_punct = last_word[-1]

            final = replacement if literal else replacement + trail_punct
            log.info(
                "[snippets-fuzzy] '%s' -> '%s' (score=%.2f)",
                window, final, ratio,
            )
            text_words[i] = final
            for j in range(i + 1, i + ws):
                text_words[j] = ""
            replaced.update(range(i, i + ws))

    return " ".join(w for w in text_words if w)
