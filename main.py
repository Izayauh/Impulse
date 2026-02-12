import logging
import pathlib
import re
import sys
from typing import Any, Dict, Tuple


def _bootstrap_src_path() -> None:
    root = pathlib.Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_bootstrap_src_path()

from brain import ContextRouter
from tools import grammar_check, read_project_file


LOGGER = logging.getLogger(__name__)


def _context_to_text(current_file_context: Any) -> str:
    if isinstance(current_file_context, str):
        return current_file_context
    if current_file_context is None:
        return "unknown"

    app_type = getattr(current_file_context, "app_type", "unknown")
    window_title = getattr(current_file_context, "window_title", "")
    if window_title:
        return f"{app_type}:{window_title}"
    return str(app_type)


def _extract_filename(raw_text: str, args: Dict[str, Any]) -> str:
    filename = args.get("filename")
    if isinstance(filename, str) and filename.strip():
        return filename.strip()

    match = re.search(
        r"\b(?:read|open|show|summarize)\s+(?:the\s+)?(?:file\s+)?([A-Za-z0-9_.\-\\/]+)",
        raw_text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    if re.search(r"\breadme\b", raw_text, flags=re.IGNORECASE):
        return "README.md"
    return ""


class ContextAwareAgent:
    """Wires the Brain(router) with deterministic tool actions."""

    def __init__(self, router: ContextRouter | None = None):
        self.router = router or ContextRouter()

    def handle(self, raw_text: str, current_file_context: Any = None) -> Tuple[str, bool, str]:
        context_text = _context_to_text(current_file_context)
        action = self.router.route(raw_text, context_text)

        intent = str(action.get("intent", "transcribe")).strip().lower()
        tool = str(action.get("tool", "none")).strip().lower()
        args = action.get("args", {})
        if not isinstance(args, dict):
            args = {}

        if intent == "transcribe":
            # Low-latency path: return raw text immediately.
            return raw_text, True, "transcribe"

        if intent == "correction":
            corrected = grammar_check(raw_text)
            return corrected, True, "correction"

        if intent == "command":
            filename = _extract_filename(raw_text, args)
            if not filename:
                LOGGER.warning("command intent without filename: %s", raw_text)
                return raw_text, False, "command_missing_filename"
            try:
                file_content = read_project_file(filename)
                answer = self.router.answer_with_file_context(
                    user_text=raw_text,
                    file_content=file_content,
                    current_file_context=context_text,
                    filename=filename,
                )
                return answer, True, f"command:{tool or 'read_file'}"
            except Exception as exc:
                LOGGER.warning("command path failed for %s: %s", filename, exc)
                return raw_text, False, "command_failed"

        return raw_text, False, f"unknown_intent:{intent}"


def main() -> int:
    from whisper_local.flow_local_dictation import (
        _acquire_single_instance,
        run_whisper_main_loop,
        set_transcript_action_handler,
        start_tray,
    )

    _acquire_single_instance()

    agent = ContextAwareAgent()
    set_transcript_action_handler(agent.handle)
    LOGGER.info("Context-aware router wiring enabled")

    start_tray()
    run_whisper_main_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
