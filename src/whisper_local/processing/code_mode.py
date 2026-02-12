"""Code dictation intelligence for spoken code transcripts.

This module implements a hybrid strategy inspired by grammar-driven systems
(deterministic spoken token mapping) and intent-based systems (confidence-
gated transformations). It keeps low-risk corrections cheap and applies
heavier structure transforms only when text is likely code.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CodeIntent:
    """Decision payload for confidence-gated code transforms."""

    score: float
    explicit_trigger: bool
    looks_code_like: bool


class CodeModeCorrector:
    """Apply spoken-code corrections with optional confidence gating."""

    _CODE_START_RE = re.compile(
        r"^\s*(def|class|import|from|if|elif|else|for|while|return|print|with|try|except|function|const|let|var)\b",
        re.IGNORECASE,
    )
    _CODE_CHAR_RE = re.compile(r"[(){}\[\]=<>:+\-*/%.,_]")
    _CASE_STOP_RE = re.compile(r"\b(?:versus|and|or|then|with|comma|colon|semicolon)\b", re.IGNORECASE)

    _KNOWN_LIBS = ("pandas", "numpy", "torch", "flask", "django", "fastapi", "matplotlib", "sklearn")
    _CODE_HINT_KEYWORDS = {
        "def",
        "class",
        "import",
        "from",
        "return",
        "lambda",
        "self",
        "args",
        "kwargs",
        "function",
        "const",
        "let",
        "var",
        "public",
        "private",
        "protected",
        "interface",
        "namespace",
        "module",
        "async",
        "await",
        "if",
        "elif",
        "else",
        "for",
        "while",
        "try",
        "except",
        "finally",
    }
    _EXPLICIT_TRIGGERS = {
        "code mode",
        "write code",
        "programming",
        "python",
        "javascript",
        "typescript",
        "c sharp",
        "c plus plus",
        "function",
        "class",
        "method",
        "import",
        "def",
    }
    _PROSE_HINTS = {
        "thank you",
        "thanks",
        "how are you",
        "good morning",
        "good afternoon",
        "good evening",
        "see you",
        "dear",
        "sincerely",
        "best regards",
    }

    # Deterministic spoken grammar replacements; ordered longest-first.
    _SPOKEN_SYMBOL_RULES = (
        (r"\bgreater\s+than\s+or\s+equal\s+to\b", ">="),
        (r"\bless\s+than\s+or\s+equal\s+to\b", "<="),
        (r"\bdoes\s+not\s+equal\b", "!="),
        (r"\bnot\s+equal(?:s)?\b", "!="),
        (r"\bdouble\s+equal(?:s)?\b", "=="),
        (r"\bequals\s+equals\b", "=="),
        (r"\btriple\s+equals\b", "==="),
        (r"\bplus\s+equals\b", "+="),
        (r"\bminus\s+equals\b", "-="),
        (r"\btimes\s+equals\b", "*="),
        (r"\bdivide(?:d)?\s+by\s+equals\b", "/="),
        (r"\bdouble\s+underscore\b", "__"),
        (r"\bopen\s+(?:parenthesis|paren)\b", "("),
        (r"\bclose\s+(?:parenthesis|paren)\b", ")"),
        (r"\bopen\s+(?:square\s+)?bracket\b", "["),
        (r"\bclose\s+(?:square\s+)?bracket\b", "]"),
        (r"\bopen\s+(?:curly\s+)?brace\b", "{"),
        (r"\bclose\s+(?:curly\s+)?brace\b", "}"),
        (r"\bcomma\b", ","),
        (r"\bsemicolon\b", ";"),
        (r"\bcolon\b", ":"),
        (r"\bdot\b", "."),
        (r"\barrow\b", "->"),
        (r"\bequals\b", "="),
        (r"\bgreater\s+than\b", ">"),
        (r"\bless\s+than\b", "<"),
        (r"\bplus\b", "+"),
        (r"\bminus\b", "-"),
        (r"\b(?:times|multiply|multiplied\s+by)\b", "*"),
        (r"\b(?:divided\s+by|divide\s+by)\b", "/"),
        (r"\bmodulo\b", "%"),
        (r"\band\s+and\b", "&&"),
        (r"\bor\s+or\b", "||"),
    )

    def __init__(
        self,
        enabled: bool = False,
        *,
        auto_detect: bool = False,
        min_confidence: float = 0.58,
        safe_confidence: float = 0.35,
    ) -> None:
        self.enabled = enabled
        self.auto_detect = auto_detect
        self.min_confidence = min_confidence
        self.safe_confidence = safe_confidence

    def set_enabled(self, enabled: bool) -> None:
        """Toggle code-mode correction on/off."""
        self.enabled = enabled

    def analyze_intent(self, text: str) -> CodeIntent:
        """Estimate whether transcript is code-like."""
        if not text:
            return CodeIntent(score=0.0, explicit_trigger=False, looks_code_like=False)

        score = 0.0
        lowered = text.lower()
        starts_as_code = bool(self._CODE_START_RE.match(text.strip()))
        explicit = any(trigger in lowered for trigger in self._EXPLICIT_TRIGGERS)
        if explicit:
            score += 0.5
        if starts_as_code:
            score += 0.35

        code_keyword_hits = 0
        for keyword in self._CODE_HINT_KEYWORDS:
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                code_keyword_hits += 1
        score += min(0.25, code_keyword_hits * 0.05)

        symbol_phrase_hits = 0
        for pattern, _ in self._SPOKEN_SYMBOL_RULES:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                symbol_phrase_hits += 1
        score += min(0.2, symbol_phrase_hits * 0.04)

        score += min(0.15, len(self._CODE_CHAR_RE.findall(text)) * 0.03)

        if re.search(r"\b(?:snake|camel|pascal|constant)\s+case\b", lowered):
            score += 0.12

        prose_hits = sum(1 for phrase in self._PROSE_HINTS if phrase in lowered)
        score -= min(0.3, prose_hits * 0.1)

        score = max(0.0, min(1.0, score))
        looks_code_like = starts_as_code or score >= self.min_confidence
        return CodeIntent(score=score, explicit_trigger=explicit, looks_code_like=looks_code_like)

    def correct(self, text: str, *, force: bool = False) -> str:
        """Correct common spoken-code transcription errors."""
        if not text or not self.enabled:
            return text

        if force:
            mode = "full"
        elif self.auto_detect:
            intent = self.analyze_intent(text)
            if not intent.explicit_trigger and not intent.looks_code_like and intent.score < self.safe_confidence:
                return text
            mode = "full" if (intent.explicit_trigger or intent.looks_code_like or intent.score >= self.min_confidence) else "safe"
        else:
            mode = "full"

        lines = text.splitlines() or [text]
        out_lines = [self._correct_line(line, mode=mode) for line in lines]
        return "\n".join(out_lines)

    def _correct_line(self, line: str, *, mode: str) -> str:
        original = line
        s = line.strip()
        if not s:
            return original

        s = self._apply_common_replacements(s)
        s = self._apply_library_normalization(s)
        s = self._apply_spoken_case_formatting(s)

        if mode == "full":
            s = self._apply_spoken_symbol_grammar(s)
            if self._looks_code_like(s):
                s = self._format_code_like_line(s)

        return s.strip()

    def _apply_common_replacements(self, s: str) -> str:
        s = re.sub(r"\bdeath\b", "def", s, flags=re.IGNORECASE)
        s = re.sub(r"\bself\s+comma\b", "self,", s, flags=re.IGNORECASE)
        s = re.sub(r"\bnot\s+equals\b", "!=", s, flags=re.IGNORECASE)
        s = re.sub(r"\bequals\s+equals\b", "==", s, flags=re.IGNORECASE)

        # __init__ spoken variants.
        s = re.sub(
            r"\b(?:in\s+it|init|dunder\s+init)\s+underscore\s+underscore\b",
            "__init__",
            s,
            flags=re.IGNORECASE,
        )
        s = re.sub(
            r"\bunderscore\s+underscore\s+(?:in\s+it|init|dunder\s+init)\s+underscore\s+underscore\b",
            "__init__",
            s,
            flags=re.IGNORECASE,
        )
        s = re.sub(r"\b(?:in\s+it|dunder\s+init)\b", "__init__", s, flags=re.IGNORECASE)

        # Underscore tokens.
        s = re.sub(r"\bunderscore\s+underscore\b", "__", s, flags=re.IGNORECASE)
        s = re.sub(r"\bunderscore\b", "_", s, flags=re.IGNORECASE)
        s = re.sub(r"(?<=\w)\s+_\s+(?=\w)", "_", s)

        # Common spoken delimiters.
        s = re.sub(r"\bcomma\b", ",", s, flags=re.IGNORECASE)
        s = re.sub(r"\bcolon\s*$", ":", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+:", ":", s)

        # Basic whitespace cleanup.
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s

    def _apply_library_normalization(self, s: str) -> str:
        for lib in self._KNOWN_LIBS:
            s = re.sub(rf"\b{lib}\b", lib, s, flags=re.IGNORECASE)

        s = re.sub(r"\bas\s+PD\b", "as pd", s, flags=re.IGNORECASE)
        s = re.sub(r"\bas\s+NP\b", "as np", s, flags=re.IGNORECASE)
        return s

    def _apply_spoken_case_formatting(self, s: str) -> str:
        def _extract_case_words(raw: str) -> list[str]:
            stop_match = self._CASE_STOP_RE.search(raw)
            segment = raw if stop_match is None else raw[:stop_match.start()]
            return [w for w in re.split(r"[_\s]+", segment.strip()) if w]

        def _camel(m: re.Match) -> str:
            raw = m.group(1)
            trailing_space = " " if raw.endswith(" ") else ""
            words = _extract_case_words(raw)
            if not words:
                return m.group(0)
            words = ["camel", "case"] + words
            first = words[0].lower()
            rest = "".join(w[:1].upper() + w[1:] for w in words[1:])
            return first + rest + trailing_space

        def _pascal(m: re.Match) -> str:
            raw = m.group(1)
            trailing_space = " " if raw.endswith(" ") else ""
            words = _extract_case_words(raw)
            if not words:
                return m.group(0)
            return "".join(w[:1].upper() + w[1:] for w in words) + trailing_space

        def _snake(m: re.Match) -> str:
            raw = m.group(1)
            trailing_space = " " if raw.endswith(" ") else ""
            words = _extract_case_words(raw)
            if not words:
                return m.group(0)
            return "_".join(w.lower() for w in words) + trailing_space

        def _const(m: re.Match) -> str:
            raw = m.group(1)
            trailing_space = " " if raw.endswith(" ") else ""
            words = _extract_case_words(raw)
            if not words:
                return m.group(0)
            return "_".join(w.upper() for w in words) + trailing_space

        stop = r"(?=\b(?:versus|and|or|then|with|comma|colon|semicolon)\b|$)"
        s = re.sub(rf"\bcamel\s+case\s+([a-zA-Z0-9_ ]+?){stop}", _camel, s, flags=re.IGNORECASE)
        s = re.sub(rf"\bpascal\s+case\s+([a-zA-Z0-9_ ]+?){stop}", _pascal, s, flags=re.IGNORECASE)
        s = re.sub(rf"\bsnake\s+case\s+([a-zA-Z0-9_ ]+?){stop}", _snake, s, flags=re.IGNORECASE)
        s = re.sub(rf"\bconstant\s+case\s+([a-zA-Z0-9_ ]+?){stop}", _const, s, flags=re.IGNORECASE)
        return s

    def _apply_spoken_symbol_grammar(self, s: str) -> str:
        for pattern, replacement in self._SPOKEN_SYMBOL_RULES:
            s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)
        return s

    def _looks_code_like(self, s: str) -> bool:
        if self._CODE_START_RE.match(s):
            return True
        if len(self._CODE_CHAR_RE.findall(s)) >= 2:
            return True
        lowered = s.lower()
        return any(re.search(rf"\b{re.escape(keyword)}\b", lowered) for keyword in self._CODE_HINT_KEYWORDS)

    def _format_code_like_line(self, s: str) -> str:
        # Normalize leading keyword case.
        s = re.sub(
            r"^\s*(Def|Class|Import|From|If|Elif|Else|For|While|Return|Print|With|Try|Except|Finally|Function|Const|Let|Var)\b",
            lambda m: m.group(1).lower(),
            s,
        )

        # Ensure colon for common Python blocks.
        if re.match(r"^\s*(def|class|if|elif|else|for|while|with|try|except|finally)\b", s) and not s.endswith(":"):
            s = s.rstrip() + ":"

        # Function signature shaping:
        # "def foo self, x:" -> "def foo(self, x):"
        m = re.match(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*(.*)$", s, flags=re.IGNORECASE)
        if m:
            name = m.group(1)
            tail = m.group(2).strip()
            tail = re.sub(r":\s*$", "", tail).strip()

            if tail and not tail.startswith("("):
                s = f"def {name}({tail})"
            elif not tail:
                s = f"def {name}"
            else:
                s = f"def {name}{tail}"

            if not s.endswith(":"):
                s += ":"

        # Class signature shaping.
        class_m = re.match(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)(.*)$", s, flags=re.IGNORECASE)
        if class_m:
            class_name = class_m.group(1)
            tail = class_m.group(2).strip()
            tail = re.sub(r":\s*$", "", tail).strip()
            if tail and not tail.startswith("("):
                s = f"class {class_name}({tail})"
            elif not tail:
                s = f"class {class_name}"
            else:
                s = f"class {class_name}{tail}"
            if not s.endswith(":"):
                s += ":"

        # Cleanup for punctuation/operators spacing.
        s = re.sub(r"\s*,\s*", ", ", s)
        s = re.sub(r",\s*\)", ")", s)
        s = re.sub(r"\(\s+", "(", s)
        s = re.sub(r"\s+\)", ")", s)
        s = re.sub(r"\s+([\]\}])", r"\1", s)
        s = re.sub(r"\s+([:;,.])", r"\1", s)
        s = re.sub(r"([(\[{])\s+", r"\1", s)
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s
