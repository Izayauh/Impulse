import os
import sys
import datetime as dt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from whisper_local.licensing import LicensingManager


def test_unactivated_license_is_invalid(tmp_path, monkeypatch):
    monkeypatch.delenv("WHISPER_DEV_BYPASS_LICENSE", raising=False)
    monkeypatch.delenv("WHISPER_REQUIRE_LICENSE", raising=False)
    manager = LicensingManager(data_dir=str(tmp_path))
    status = manager.get_license_status(offline_fallback=True, allow_online_check=False)
    assert status["is_valid"] is False
    assert status["reason"] == "not_activated"


def test_license_not_required_env_allows_access(tmp_path, monkeypatch):
    monkeypatch.setenv("WHISPER_REQUIRE_LICENSE", "0")
    manager = LicensingManager(data_dir=str(tmp_path))
    status = manager.get_license_status(offline_fallback=True, allow_online_check=False)
    assert status["is_valid"] is True
    assert status["reason"] == "license_not_required"


def test_beta_expiry_blocks_access(tmp_path, monkeypatch):
    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    monkeypatch.setenv("WHISPER_BETA_EXPIRES_ON", yesterday)
    manager = LicensingManager(data_dir=str(tmp_path))
    status = manager.get_license_status(offline_fallback=True, allow_online_check=False)
    assert status["is_valid"] is False
    assert status["reason"] == "beta_expired"


def test_cached_license_valid_within_offline_grace(tmp_path, monkeypatch):
    monkeypatch.setenv("WHISPER_LICENSE_OFFLINE_GRACE_DAYS", "3")
    manager = LicensingManager(data_dir=str(tmp_path))
    now = dt.datetime.now(dt.timezone.utc)
    manager._save_license_state(
        {
            "active": True,
            "key": "BETA-1234",
            "revoked": False,
            "last_check": (now - dt.timedelta(days=1)).isoformat(),
            "last_online_check": None,
            "meta": {},
            "last_error": None,
        }
    )

    status = manager.get_license_status(offline_fallback=True, allow_online_check=False)
    assert status["is_valid"] is True
    assert status["reason"] == "offline_grace"


def test_cached_license_invalid_after_offline_grace(tmp_path, monkeypatch):
    monkeypatch.setenv("WHISPER_LICENSE_OFFLINE_GRACE_DAYS", "1")
    manager = LicensingManager(data_dir=str(tmp_path))
    now = dt.datetime.now(dt.timezone.utc)
    manager._save_license_state(
        {
            "active": True,
            "key": "BETA-1234",
            "revoked": False,
            "last_check": (now - dt.timedelta(days=2)).isoformat(),
            "last_online_check": None,
            "meta": {},
            "last_error": None,
        }
    )

    status = manager.get_license_status(offline_fallback=True, allow_online_check=False)
    assert status["is_valid"] is False
    assert status["reason"] == "offline_grace_expired"


def test_beta_expiry_days_none_when_not_set(tmp_path, monkeypatch):
    monkeypatch.delenv("WHISPER_BETA_EXPIRES_ON", raising=False)
    manager = LicensingManager(data_dir=str(tmp_path))
    assert manager.days_until_beta_expiry() is None


def test_beta_expiry_days_counts_correctly(tmp_path, monkeypatch):
    future = (dt.date.today() + dt.timedelta(days=5)).isoformat()
    monkeypatch.setenv("WHISPER_BETA_EXPIRES_ON", future)
    manager = LicensingManager(data_dir=str(tmp_path))
    assert manager.days_until_beta_expiry() == 5


def test_beta_expiry_days_zero_when_expired(tmp_path, monkeypatch):
    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    monkeypatch.setenv("WHISPER_BETA_EXPIRES_ON", yesterday)
    manager = LicensingManager(data_dir=str(tmp_path))
    assert manager.days_until_beta_expiry() == 0


def test_status_includes_beta_expiry_days(tmp_path, monkeypatch):
    future = (dt.date.today() + dt.timedelta(days=3)).isoformat()
    monkeypatch.setenv("WHISPER_BETA_EXPIRES_ON", future)
    monkeypatch.setenv("WHISPER_REQUIRE_LICENSE", "0")
    manager = LicensingManager(data_dir=str(tmp_path))
    status = manager.get_license_status(offline_fallback=True, allow_online_check=False)
    assert "beta_expiry_days" in status
    assert status["beta_expiry_days"] == 3
