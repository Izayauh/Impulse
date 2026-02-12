"""User vocabulary storage and prompt composition helpers."""

from __future__ import annotations

import json
import os
from typing import Iterable, List, Tuple


MAX_VOCAB_WORDS_IN_PROMPT = 120
MAX_PROMPT_CHARS = 3500


def vocabulary_file(user_data_dir: str) -> str:
    return os.path.join(user_data_dir, "state", "vocabulary.json")


def _normalize_word(word: str) -> str:
    return " ".join(str(word or "").strip().split())


def _normalize_words(words: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for raw in words or []:
        word = _normalize_word(raw)
        if not word:
            continue
        key = word.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(word)
    return out


def load_vocabulary(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, IOError):
        return []

    if isinstance(data, dict):
        words = data.get("words", [])
    elif isinstance(data, list):
        words = data
    else:
        words = []
    return _normalize_words(words)


def save_vocabulary(path: str, words: Iterable[str]) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        normalized = _normalize_words(words)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"words": normalized}, f, indent=2)
        return True
    except (OSError, IOError):
        return False


def add_vocabulary_word(path: str, word: str) -> Tuple[List[str], bool]:
    candidate = _normalize_word(word)
    words = load_vocabulary(path)
    if not candidate:
        return words, False
    if candidate.casefold() in {w.casefold() for w in words}:
        return words, False
    words.append(candidate)
    save_vocabulary(path, words)
    return words, True


def compose_prompt(base_prompt: str, words: Iterable[str]) -> str:
    base = str(base_prompt or "").strip()
    clean_words = _normalize_words(words)
    if not clean_words:
        return base

    top_words = clean_words[:MAX_VOCAB_WORDS_IN_PROMPT]
    vocab_clause = "Custom vocabulary: " + ", ".join(top_words)
    if not base:
        prompt = vocab_clause
    else:
        prompt = f"{base}, {vocab_clause}"

    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt
    return prompt[:MAX_PROMPT_CHARS].rstrip(", ")
