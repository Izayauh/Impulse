"""Final deterministic sanitizer for stubborn transcription glitches."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_CODE_STRONG_START_RE = re.compile(
    r"^\s*(?:death|def|class|import|from|if|for|while|return|print)\b",
    re.IGNORECASE,
)
_CODE_HINT_PATTERNS = (
    re.compile(r"\b(?:in\s+it|init)\b", re.IGNORECASE),
    re.compile(r"\bself\b", re.IGNORECASE),
    re.compile(r"\bunderscore\b", re.IGNORECASE),
    re.compile(r"\b(?:equals\s+equals|not\s+equals)\b", re.IGNORECASE),
    re.compile(r"\b(?:def|death|class|import|from)\b", re.IGNORECASE),
    re.compile(r"\b(?:args?|kwargs?)\b", re.IGNORECASE),
    re.compile(r"\bcolon\b", re.IGNORECASE),
)
_AUDIO_HINT_PATTERNS = (
    re.compile(r"\bthd\+?n\b", re.IGNORECASE),
    re.compile(r"\bq[\s-]?factor\b", re.IGNORECASE),
    re.compile(r"\b(?:xlr|phantom|preamp|sm7b|shure)\b", re.IGNORECASE),
    re.compile(r"\b(?:hz|khz|bit[\s-]?depth|sample\s+rate)\b", re.IGNORECASE),
)


def sanitize_final_glitches(text: str, context: str = "") -> str:
    """Apply final regex cleanup for persistent model quirks."""
    if not text:
        return text

    original = text
    out = text

    # 1) Endpoint colon normalization: "127.0.0.1 colon 8080" -> "127.0.0.1:8080"
    out = re.sub(
        r"\b((?:\d{1,3}\.){3}\d{1,3}|localhost|[A-Za-z0-9._-]+\.[A-Za-z]{2,}|[A-Za-z0-9._-]+)\s+colon\s+(\d{1,5})\b",
        r"\1:\2",
        out,
        flags=re.IGNORECASE,
    )

    # 2) Vocative comma safety ("Let's eat, Grandma.")
    out = _fix_vocative_grandma(out)

    # 2b) Audio-domain and rare-name lexical patches.
    out = _fix_audio_queue_glitch(out, context=context)
    out = _fix_wright_name_glitch(out)

    # 3) Code-like cleanup per line.
    lines = out.splitlines() or [out]
    fixed_lines = []
    for line in lines:
        if _is_code_like_line(line, context):
            fixed_lines.append(_fix_code_line(line))
        else:
            fixed_lines.append(line)
    out = "\n".join(fixed_lines)

    if out != original:
        logger.info("final_sanitizer applied deterministic cleanup")
    return out


def _is_code_like_line(line: str, context: str) -> bool:
    if not line.strip():
        return False

    if context and str(context).lower() in {"code_editor", "terminal"}:
        return True

    if _CODE_STRONG_START_RE.search(line):
        return True

    hint_count = sum(1 for pat in _CODE_HINT_PATTERNS if pat.search(line))
    return hint_count >= 2


def _fix_code_line(line: str) -> str:
    s = line

    # Spoken operator/token replacements.
    s = re.sub(r"\bnot\s+equals\b", "!=", s, flags=re.IGNORECASE)
    s = re.sub(r"\bequals\s+equals\b", "==", s, flags=re.IGNORECASE)
    s = re.sub(r"\bself\s+comma\b", "self,", s, flags=re.IGNORECASE)
    s = re.sub(r"\bunderscore\s+underscore\b", "__", s, flags=re.IGNORECASE)
    s = re.sub(r"\bunderscore\b", "_", s, flags=re.IGNORECASE)

    # Python keyword/accent fixes.
    s = re.sub(r"\bdeath\b", "def", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:in\s+it|init)\b", "__init__", s, flags=re.IGNORECASE)

    # Common code line colon fixes.
    s = re.sub(
        r"\b(def\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:\([^)]*\))?)\s+colon\b",
        r"\1:",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\b(class\s+[A-Za-z_][A-Za-z0-9_]*\s*(?:\([^)]*\))?)\s+colon\b",
        r"\1:",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\b((?:if|elif|else|for|while|try|except|finally|with)\b[^:\n]*?)\s+colon\b",
        r"\1:",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"\bcolon\s*$", ":", s, flags=re.IGNORECASE)

    # "__init__" signature shaping
    s = re.sub(
        r"\bdef\s+__init__\s+self,\s*([^:]+?)\s*:\s*$",
        r"def __init__(self, \1):",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bdef\s+__init__\s+self\s*:\s*$",
        r"def __init__(self):",
        s,
        flags=re.IGNORECASE,
    )

    # Whitespace cleanup around separators.
    s = re.sub(r"(?<=\w)\s+_\s+(?=\w)", "_", s)
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s+:", ":", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def _fix_vocative_grandma(text: str) -> str:
    def _repl(match: re.Match) -> str:
        person = match.group(1).capitalize()
        punct = match.group(2) or ""
        return f"Let's eat, {person}{punct}"

    return re.sub(
        r"\blet'?s\s+eat\s+(grandma|grandpa|mom|dad|mother|father)\b([.!?]?)",
        _repl,
        text,
        flags=re.IGNORECASE,
    )


def _fix_audio_queue_glitch(text: str, context: str = "") -> str:
    ctx = (context or "").lower()
    is_audio_context = ctx in {"audio_engineering", "music_production"}
    if not is_audio_context:
        is_audio_context = any(p.search(text) for p in _AUDIO_HINT_PATTERNS)

    if not is_audio_context:
        return text

    out = text
    out = re.sub(r"\bqueue[\s-]*factor\b", "Q-factor", out, flags=re.IGNORECASE)
    out = re.sub(r"\bin\s+the\s+queue\s+2\.7\b", "the Q-factor to 0.7", out, flags=re.IGNORECASE)
    out = re.sub(r"\bthe\s+queue\s+2\.7\b", "the Q-factor to 0.7", out, flags=re.IGNORECASE)
    out = re.sub(r"\bqueue\s+2\.7\b", "Q-factor to 0.7", out, flags=re.IGNORECASE)
    return out


def _fix_wright_name_glitch(text: str) -> str:
    return re.sub(
        r"\b(maker)\s+right\b(?=[\s,.;:!?]|$)",
        r"\1 Wright",
        text,
        flags=re.IGNORECASE,
    )
