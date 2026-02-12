"""Deterministic tool functions for routing actions in Whisper Local."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

LOGGER = logging.getLogger(__name__)
_LANG_TOOL: Optional[Any] = None


def _project_root() -> Path:
    # src/tools.py -> src -> project root
    return Path(__file__).resolve().parent.parent


def _get_language_tool() -> Any:
    global _LANG_TOOL
    if _LANG_TOOL is None:
        import language_tool_python

        _LANG_TOOL = language_tool_python.LanguageTool("en-US")
    return _LANG_TOOL


def grammar_check(text: str) -> str:
    """Apply strict rule-based grammar correction via LanguageTool."""
    if not text:
        return text

    try:
        tool = _get_language_tool()
        matches = tool.check(text)
        import language_tool_python

        return language_tool_python.utils.correct(text, matches)
    except Exception as exc:
        LOGGER.warning("grammar_check failed; returning original text: %s", exc)
        return text


def read_project_file(filename: str) -> str:
    """Read a file safely from within the current project root."""
    if not filename or not filename.strip():
        raise ValueError("filename must be a non-empty string")

    project_root = _project_root()
    requested = filename.strip()

    if "\x00" in requested:
        raise ValueError("filename contains invalid characters")

    requested_path = Path(requested)
    if requested_path.is_absolute():
        raise ValueError("absolute paths are not allowed")

    # First try explicit relative path under project root.
    explicit_candidate = (project_root / requested_path).resolve()
    try:
        explicit_candidate.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("directory traversal detected") from exc

    if explicit_candidate.is_file():
        return explicit_candidate.read_text(encoding="utf-8", errors="replace")

    # If only a filename was provided, securely search under project root.
    if len(requested_path.parts) == 1:
        skip_dirs = {".git", ".venv", "__pycache__"}
        for candidate in project_root.rglob(requested):
            if any(part in skip_dirs for part in candidate.parts):
                continue
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            try:
                resolved.relative_to(project_root)
            except ValueError:
                continue
            return resolved.read_text(encoding="utf-8", errors="replace")

    raise FileNotFoundError(f"file not found in project: {filename}")


def get_active_context() -> str:
    """Placeholder for editor/session context integration."""
    return "User is currently editing main.py"


__all__ = ["grammar_check", "read_project_file", "get_active_context"]
