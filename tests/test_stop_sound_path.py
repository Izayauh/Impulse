"""The stop-take sound must resolve in a frozen build, where the spec places
message-send.mp3 at the bundle root rather than beside the module."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local import flow_local_dictation as F  # noqa: E402


def test_source_layout_resolves_module_relative_file():
    path = F.resolve_sound_effect_path()
    assert os.path.basename(path) == "message-send.mp3"
    assert os.path.exists(path)


def test_frozen_layout_falls_back_to_bundle_root(tmp_path, monkeypatch):
    bundled = tmp_path / "message-send.mp3"
    bundled.write_bytes(b"ID3")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(F.os.path, "exists", lambda p: p == str(bundled))
    assert F.resolve_sound_effect_path() == str(bundled)
