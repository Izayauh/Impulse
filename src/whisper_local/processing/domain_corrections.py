"""
Domain-specific terminology correction module for WhisperLocal.

Fixes technical terms, units, brand names, and formatting that Whisper
consistently gets wrong in specialized domains (audio engineering,
networking, programming, etc.).

Each domain is a separate profile that can be loaded independently.
Corrections are NOT applied inside quoted strings or code blocks.

Usage:
    from domain_corrections import DomainCorrector

    corrector = DomainCorrector(["audio_engineering"])
    result = corrector.correct("48 v of phantom power")
    # → "48V of Phantom Power"
"""

import re
from typing import Callable, Union


# ============================================================================
# Rule infrastructure
# ============================================================================

class _PatternRule:
    """A regex-based correction rule."""
    __slots__ = ("pattern", "replacement")

    def __init__(self, pattern: re.Pattern, replacement: Union[str, Callable]):
        self.pattern = pattern
        self.replacement = replacement

    def apply(self, text: str) -> str:
        return self.pattern.sub(self.replacement, text)


class _TextRule:
    """A text-level correction rule (full-text callable)."""
    __slots__ = ("fn",)

    def __init__(self, fn: Callable[[str], str]):
        self.fn = fn

    def apply(self, text: str) -> str:
        return self.fn(text)


def _rule(pattern: str, replacement: Union[str, Callable],
          flags: int = re.IGNORECASE) -> _PatternRule:
    """Convenience helper to create a compiled PatternRule."""
    return _PatternRule(re.compile(pattern, flags), replacement)


# ============================================================================
# Protected-region helpers (skip quoted strings & code blocks)
# ============================================================================

_PROTECTED_RE = re.compile(
    r'```[\s\S]*?```'    # fenced code blocks
    r'|`[^`]+`'          # inline code
    r'|"[^"]*"'          # double-quoted strings
)


def _protect(text: str) -> tuple[str, dict[str, str]]:
    """Replace quoted/code regions with placeholders before corrections."""
    store: dict[str, str] = {}
    counter = [0]

    def _swap(m):
        key = f"\x00P{counter[0]}\x00"
        store[key] = m.group(0)
        counter[0] += 1
        return key

    return _PROTECTED_RE.sub(_swap, text), store


def _restore(text: str, store: dict[str, str]) -> str:
    """Put the original quoted/code regions back."""
    for key, original in store.items():
        text = text.replace(key, original)
    return text


# ============================================================================
# Audio Engineering profile
# ============================================================================

def _phantom_power_contextual(text: str) -> str:
    """Capitalize 'phantom power' only when a voltage value precedes it."""
    def _replacer(m):
        prefix = text[:m.start()]
        if re.search(r'\d+V\b', prefix):
            return "Phantom Power"
        return m.group(0)
    return re.sub(r'\bphantom\s+power\b', _replacer, text, flags=re.IGNORECASE)


def _audio_engineering_rules() -> list:
    """Build the ordered rule list for the audio_engineering profile."""
    return [
        # ── Unit formatting (number + unit combos — must run first) ──────
        # Spelled-out units → collapsed abbreviation
        _rule(r'(\d+)\s*kilohertz\b', r'\1kHz'),
        _rule(r'(\d+)\s*hertz\b',     r'\1Hz'),
        # Abbreviated units with whitespace
        _rule(r'(\d+)\s+v\b',   r'\1V'),
        _rule(r'(\d+)\s+khz\b', r'\1kHz'),
        _rule(r'(\d+)\s+hz\b',  r'\1Hz'),
        _rule(r'(\d+)\s+db\b',  r'\1dB'),
        # Standalone unit casing (won't match inside "48kHz" — no \b there)
        _rule(r'\bkhz\b', 'kHz'),
        _rule(r'\bhz\b',  'Hz'),
        _rule(r'\bdb\b',  'dB'),

        # ── Technical terms ──────────────────────────────────────────────
        _rule(r'\bthd\s*\+\s*n\b',           'THD+N'),
        _rule(r'\bsignal\s+to\s+noise\b',    'signal-to-noise'),
        _rule(r'\bhigh\s+pass\s+filter\b',   'high-pass filter'),
        _rule(r'\blow\s+pass\s+filter\b',    'low-pass filter'),
        _rule(r'\bq\s+factor\b',             'Q-factor'),
        _rule(r'\bbit[\s-]+depth\b',         'bit depth'),
        # Phantom Power (context-dependent — only after a voltage value)
        _TextRule(_phantom_power_contextual),

        # ── File formats ─────────────────────────────────────────────────
        _rule(r'\bwave\s+file\b',   'WAV file'),
        _rule(r'\bwave\s+format\b', 'WAV format'),
        _rule(r'\bmp\s*3\b',        'MP3'),
        _rule(r'\bflac\b',          'FLAC'),

        # ── Gear / brand names ───────────────────────────────────────────
        _rule(r'\bsm7b\b',  'SM7B'),
        _rule(r'\bshure\b', 'Shure'),
        _rule(r'\bxlr\b',   'XLR'),
    ]


# ============================================================================
# Profile registry — add new profiles here
# ============================================================================

_PROFILES: dict[str, Callable[[], list]] = {
    "audio_engineering": _audio_engineering_rules,
    # Future:
    # "networking":   _networking_rules,
    # "programming":  _programming_rules,
}


# ============================================================================
# Public API
# ============================================================================

class DomainCorrector:
    """Apply domain-specific terminology corrections to transcribed text.

    Loads one or more domain profiles and applies their correction rules
    in order.  Quoted strings and code blocks are protected from changes.

    Args:
        profiles: Domain profile names to activate.

    Raises:
        ValueError: If an unknown profile name is given.

    Example::

        corrector = DomainCorrector(["audio_engineering"])
        corrector.correct("48 v of phantom power")
        # → "48V of Phantom Power"
    """

    def __init__(self, profiles: list[str]) -> None:
        self._rules: list = []
        for name in profiles:
            if name not in _PROFILES:
                available = ", ".join(sorted(_PROFILES))
                raise ValueError(
                    f"Unknown profile: {name!r}. Available: {available}"
                )
            self._rules.extend(_PROFILES[name]())

    def correct(self, text: str) -> str:
        """Apply all loaded correction rules to *text*.

        Corrections are NOT applied inside double-quoted strings,
        inline backtick code, or fenced code blocks.

        Args:
            text: Raw or partially-processed transcript text.

        Returns:
            Text with domain-specific formatting applied.
        """
        if not text:
            return text

        text, store = _protect(text)
        for rule in self._rules:
            text = rule.apply(text)
        text = _restore(text, store)
        return text
