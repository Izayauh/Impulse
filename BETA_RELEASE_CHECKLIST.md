# WhisperLocal Beta Release Checklist

Target version: `1.0.0-beta.1`

## 1) Preflight

- [ ] `git status` is clean
- [ ] Licensing env policy selected (recommended below)
- [ ] Telemetry policy selected (currently opt-in by default)

Recommended beta env:

```powershell
$env:WHISPER_REQUIRE_LICENSE = "1"
$env:WHISPER_DEV_BYPASS_LICENSE = "0"
$env:WHISPER_FORCE_DISABLE = "0"
$env:WHISPER_LICENSE_OFFLINE_GRACE_DAYS = "3"
$env:WHISPER_LICENSE_REVALIDATE_HOURS = "24"
$env:WHISPER_BETA_EXPIRES_ON = "2026-04-30"
```

## 2) Validate app

```powershell
python -m pytest tests --ignore=tests/integration
powershell -ExecutionPolicy Bypass -File scripts\windows\test_system.ps1
```

## 3) Build installer

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release\build_installer.ps1 -Clean
```

Notes:
- Version is sourced from `src/whisper_local/config.py`.
- Inno output name uses `WhisperLocal-Setup-<version>.exe`.
- Set `WHISPER_BOOTSTRAP_BASE_URL` before the build if you want the single-file bootstrap installer too.

## 4) Create delivery package

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release\create_release_package.ps1
```

This auto-detects latest installer and produces:
- `dist\WhisperLocal-Setup-<version>-Complete.zip`
- `dist\WhisperLocal-Setup-<version>-Complete.zip.sha256`

## 5) Smoke test installer on clean machine

- [ ] Bootstrap installer downloads hosted payload and finishes successfully
- [ ] Install/uninstall works
- [ ] First-run wizard opens
- [ ] Dictation blocked when unlicensed
- [ ] Activation works with beta key
- [ ] Offline grace behavior works
- [ ] Force-disable (`WHISPER_FORCE_DISABLE=1`) blocks dictation

## 6) Publish beta

- [ ] Create GitHub pre-release tag: `v1.0.0-beta.1`
- [ ] Upload bootstrap installer + payload manifest if external hosting is configured
- [ ] Upload split installer package + sha256
- [ ] Include known issues + expiration policy in release notes
