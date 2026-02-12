"""Standalone bootstrap entrypoint for whisper_local.ui.gui_host.

This file is a thin launcher; the dashboard host implementation lives in
src/whisper_local/ui/gui_host.py.
"""

from __future__ import annotations

import pathlib
import sys


def _bootstrap_src_path() -> None:
    root = pathlib.Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_bootstrap_src_path()

from whisper_local.ui.gui_host import main


if __name__ == "__main__":
    raise SystemExit(main())
