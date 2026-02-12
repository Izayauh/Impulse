"""
Numeric formatting module for WhisperLocal.

Fixes spaced-out numeric sequences that Whisper produces — IPv4 addresses,
port numbers, decimals, and version strings — while carefully avoiding
false positives at sentence boundaries and in time formats.

Usage:
    from numeric_formatter import format_numbers

    format_numbers("127. 0. 0. 1: 8080")   # → "127.0.0.1:8080"
    format_numbers("the Q-factor to 0. 7")  # → "the Q-factor to 0.7"
"""

import re


# ============================================================================
# IPv4 address + optional port
# ============================================================================

# Four 1-3 digit groups separated by (possibly spaced) dots,
# with a word boundary after the last octet so we don't eat into
# longer digit strings like phone numbers.
_IP_RE = re.compile(
    r'(\d{1,3})\s*\.\s*(\d{1,3})\s*\.\s*(\d{1,3})\s*\.\s*(\d{1,3})\b'
    r'(\s*:\s*(\d+))?'
)


def _collapse_ip_addresses(text: str) -> str:
    """Collapse spaces in IPv4 addresses and optional :port suffixes.

    "127. 0. 0. 1 : 8080"  →  "127.0.0.1:8080"
    "192. 168. 1. 1"        →  "192.168.1.1"
    """
    def _replacer(m):
        ip = f"{m.group(1)}.{m.group(2)}.{m.group(3)}.{m.group(4)}"
        if m.group(6):          # port present
            ip += f":{m.group(6)}"
        return ip
    return _IP_RE.sub(_replacer, text)


# ============================================================================
# Decimal and version-number collapsing
# ============================================================================

# Matches  digit(s) <spaced dot> digit(s)  where at least one space
# exists on either side of the dot.  Won't match "3.7" (already correct).
#
# (?<!\.) prevents the first \d+ from starting right after an existing dot,
# which stops us from extending already-collapsed numbers like "192.168.1.1"
# into their neighbours (e.g. "192.168.1.1. 2" must NOT become "…1.12").
_SPACED_DOT_RE = re.compile(
    r'(?<!\.)(\d+)(?:\s+\.\s*|\s*\.\s+)(\d+)'
)


def _collapse_spaced_decimals(text: str) -> str:
    """Collapse spaced dots between digits (decimals & version numbers).

    Runs iteratively so multi-part versions resolve fully:
        "3. 11. 4"  →  pass 1 "3.11. 4"  →  pass 2 "3.11.4"

    A match is suppressed when the first non-space character after the
    second digit group is uppercase — that signals a sentence boundary
    (the period ended a sentence and the digit starts the next one).
    """
    prev = None
    while prev != text:
        prev = text
        snapshot = text          # capture for the closure below

        def _replacer(m, _snap=snapshot):
            # Look at what follows the second number group in the
            # *current* version of the text to detect sentence boundaries.
            rest = _snap[m.end():]
            stripped = rest.lstrip()
            if stripped and stripped[0].isupper():
                return m.group(0)       # sentence boundary — leave it alone
            return m.group(1) + '.' + m.group(2)

        text = _SPACED_DOT_RE.sub(_replacer, text)
    return text


# ============================================================================
# Public API
# ============================================================================

def format_numbers(text: str) -> str:
    """Fix spaced-out numeric sequences in Whisper transcripts.

    Processing order:
        1. IPv4 addresses (+ optional port suffix)
        2. Decimals and version numbers (iterative, sentence-boundary safe)

    What is collapsed:
        - ``127. 0. 0. 1``       →  ``127.0.0.1``
        - ``127.0.0.1 : 8080``   →  ``127.0.0.1:8080``
        - ``0. 7``               →  ``0.7``
        - ``3. 11. 4``           →  ``3.11.4``

    What is NOT collapsed:
        - ``I said 3. Next …``  (period ends a sentence — no digit after it)
        - ``5:30``               (time format — no IP pattern preceding it)

    Args:
        text: Raw or partially-processed transcript text.

    Returns:
        Text with numeric sequences properly collapsed.
    """
    if not text:
        return text
    text = _collapse_ip_addresses(text)
    text = _collapse_spaced_decimals(text)
    return text
