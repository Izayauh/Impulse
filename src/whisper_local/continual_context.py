"""Continual Context: Dynamic local vocabulary learning system."""

import os
import json
from typing import List
from urllib import error, request as url_request
from whisper_local.config import get_user_data_dir

# Initial default context that used to be hardcoded in flow_local_dictation.py
DEFAULT_CONTEXT = [
    "Shure SM7B", "Audient iD14", "XLR", "Preamp", "Phantom Power 48V",
    "Ableton Live", "Pro Tools", "VST plugins", "Sidechain compression",
    "High-pass filter HPF", "Low-pass filter LPF", "Q-factor", "THD+N",
    "Signal-to-Noise Ratio SNR", "Hz", "kHz", "Bit-depth",
    "Python", "JSON", "C++", "CUDA", "WSL", "GitHub", "pandas", "numpy",
    "PyTorch", "TensorFlow", "Transformer", "__init__", "snake_case",
    "camelCase", "def", "import", "Dota 2", "RuneScape", "Mid lane",
    "Gank", "DPS", "Aggro", "localhost", "127.0.0.1", "sudo", "apt-get"
]

def context_file() -> str:
    """Return the path to the continual context database."""
    return os.path.join(get_user_data_dir(), "state", "continual_context.json")

def load_context() -> List[str]:
    """Load the current learned vocabulary."""
    path = context_file()
    if not os.path.exists(path):
        save_context(DEFAULT_CONTEXT)
        return list(DEFAULT_CONTEXT)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return list(data.get("words", DEFAULT_CONTEXT))
            elif isinstance(data, list):
                return list(data)
            return list(DEFAULT_CONTEXT)
    except Exception:
        return list(DEFAULT_CONTEXT)

def save_context(words: List[str]) -> bool:
    """Save the vocabulary buffer to disk."""
    path = context_file()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Deduplicate while preserving order
        seen = set()
        clean = []
        for w in words:
            w = str(w).strip()
            if w and w.casefold() not in seen:
                seen.add(w.casefold())
                clean.append(w)
                
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"words": clean}, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving continual context: {e}")
        return False

def add_learned_word(word: str) -> bool:
    """Add a new word to the continual context database."""
    word = str(word).strip()
    if not word:
        return False
        
    words = load_context()
    if word.casefold() not in [w.casefold() for w in words]:
        words.append(word)
        return save_context(words)
    return False

def get_continual_context_string() -> str:
    """Return the context as a comma-separated string for Whisper."""
    words = load_context()
    return ", ".join(words)


def extract_and_learn(text: str, model: str, endpoint: str) -> List[str]:
    """Extract proper nouns/technical terms from text and add them to the context.

    Uses Ollama (non-blocking caller responsibility) to identify new vocabulary.
    Returns a list of newly-added words, or [] on any error or if Ollama is
    unavailable.
    """
    text = str(text or "").strip()
    if not text:
        return []

    try:
        # Availability check — fast 3-second probe
        tags_req = url_request.Request(f"{endpoint}/api/tags")
        try:
            url_request.urlopen(tags_req, timeout=3)
        except error.URLError:
            return []

        prompt = (
            "Extract proper nouns, product names, and technical terms from the "
            "following text. Return ONLY a JSON array of strings. Skip common "
            "words and words shorter than 3 characters. Return [] if there are "
            f"no relevant terms.\n\nText: {text}"
        )
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 2048},
        }).encode()

        gen_req = url_request.Request(
            f"{endpoint}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with url_request.urlopen(gen_req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        raw = result.get("response", "").strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else ""
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        terms = json.loads(raw)
        if not isinstance(terms, list):
            return []

        added = []
        for term in terms:
            if len(added) >= 10:
                break
            term = str(term).strip()
            if len(term) < 3:
                continue
            if add_learned_word(term):
                added.append(term)

        return added

    except Exception:
        return []
