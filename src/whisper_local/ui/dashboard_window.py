"""Compatibility shim for legacy imports.

The dashboard host was moved to ``whisper_local.ui.gui_host``.
This module re-exports the public entry points so existing imports continue
to work during migration.
"""

from whisper_local.ui.gui_host import DASHBOARD_HTML_PATH, DashboardAPI, main, open_dashboard


def create_dashboard_window():
    """Legacy API retained for compatibility."""
    return None


def export_stats_for_browser():
    """Legacy browser-export path removed in HTML-first native mode."""
    return False


def open_dashboard_browser():
    """Legacy browser-launch path removed in HTML-first native mode."""
    return False


def open_dashboard_direct():
    """Open dashboard using the native host."""
    return open_dashboard()


if __name__ == "__main__":
    raise SystemExit(main())
