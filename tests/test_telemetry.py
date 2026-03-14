import os
import json
import logging
import uuid
import pytest
from unittest.mock import patch, MagicMock

from whisper_local.telemetry import (
    TelemetryCollector,
    TelemetrySubmitter,
    get_install_id,
    sanitize_payload,
)


def test_sanitize_payload_redacts_user_paths():
    payload = {
        "event": "crash",
        "file_path": "C:\\Users\\JohnDoe\\Documents\\secret.txt",
        "working_dir": "c:\\users\\admin\\appdata\\roaming",
    }
    sanitized = sanitize_payload(payload)
    
    assert "JohnDoe" not in sanitized["file_path"]
    assert sanitized["file_path"] == "<USER_DIR>\\Documents\\secret.txt"
    assert "admin" not in sanitized["working_dir"]
    assert sanitized["working_dir"] == "<USER_DIR>\\appdata\\roaming"


def test_sanitize_payload_redacts_transcripts():
    payload = {
        "event": "transcription_error",
        "data": {
            "transcript": "This is a secret meeting.",
            "transcribed_text": "Another secret.",
            "text": "More secrets...",
            "duration": 5.2,
            "nested": {
                "transcript": "Deep secret"
            }
        }
    }
    sanitized = sanitize_payload(payload)
    
    assert sanitized["data"]["transcript"] == "<redacted>"
    assert sanitized["data"]["transcribed_text"] == "<redacted>"
    assert sanitized["data"]["text"] == "<redacted>"
    assert sanitized["data"]["duration"] == 5.2
    assert sanitized["data"]["nested"]["transcript"] == "<redacted>"


def test_get_install_id_is_stable(tmp_path):
    # Patch the symbol used by whisper_local.telemetry.get_install_id.
    with patch("whisper_local.telemetry.get_user_data_dir", return_value=str(tmp_path)):
        id1 = get_install_id()
        id2 = get_install_id()
        
        assert id1 == id2
        assert len(id1) > 10
        
        # Verify it was written to disk
        id_file = tmp_path / "state" / "install_id.txt"
        assert id_file.exists()
        assert id_file.read_text().strip() == id1


def test_telemetry_collector_queue():
    collector = TelemetryCollector(max_queue_size=2)
    
    # Add events
    collector.record_event("info", {"msg": "event 1"})
    collector.record_event("error", {"msg": "event 2"})
    
    assert collector.pending_count == 2
    
    # Exceed max queue size
    collector.record_event("warning", {"msg": "event 3"})
    
    # Queue size should still be 2 (event 3 dropped)
    assert collector.pending_count == 2
    
    # Drain
    events = collector.drain()
    assert len(events) == 2
    assert events[0]["type"] == "info"
    assert events[0]["msg"] == "event 1"
    assert events[1]["type"] == "error"
    assert events[1]["msg"] == "event 2"
    
    # Queue is empty now
    assert collector.pending_count == 0


@patch("urllib.request.urlopen")
def test_telemetry_submitter_flush(mock_urlopen):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response
    
    collector = TelemetryCollector()
    collector.record_event("perf", {"load": 0.5})
    collector.record_event("error", {"msg": "test"})
    
    submitter = TelemetrySubmitter(collector, github_token="fake_token", interval_sec=10)
    
    # Flush should pick up 2 events
    submitter.flush()
    
    assert collector.pending_count == 0
    assert mock_urlopen.call_count == 1
    
    # Verify the request payload
    req = mock_urlopen.call_args[0][0]
    assert req.method == "POST"
    assert req.headers["Authorization"] == "Bearer fake_token"
    
    body = req.data.decode("utf-8")
    parsed_body = json.loads(body)
    
    assert "perf" in parsed_body["body"]
    assert "error" in parsed_body["body"]
    assert parsed_body["labels"] == ["telemetry", "beta"]
