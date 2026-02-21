"""Continual Context: Dynamic local vocabulary learning system."""

import os
import json
from typing import List
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
        return DEFAULT_CONTEXT
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("words", DEFAULT_CONTEXT)
            elif isinstance(data, list):
                return data
            return DEFAULT_CONTEXT
    except Exception:
        return DEFAULT_CONTEXT

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
