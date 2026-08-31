# Impulse Beta Release Checklist

Target version: set the next prerelease tag, for example `v1.0.6-beta.1`.

## 1) Preflight

- [ ] `git status` is clean
- [ ] `src/whisper_local/config.py`, `pyproject.toml`, and both Inno Setup scripts use the intended version
- [ ] `CHANGELOG.md` describes the user-visible changes and known issues
- [ ] Release credentials and required GitHub secrets are configured

## 2) Validate the app

```powershell
python -m pytest tests --ignore=tests/integration
powershell -ExecutionPolicy Bypass -File scripts\windows\test_system.ps1
```

## 3) Build the installer

Preferred: push the prerelease tag and let `.github/workflows/release.yml` build the release on the pinned Python 3.11 path.

For a local Windows build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release\build_installer.ps1 -Clean
```

The release workflow and local build both require:

- `runtime\bin\whisper-cli.exe`
- `runtime\bin\ggml-base.dll`, `ggml.dll`, and `whisper.dll`
- at least one `runtime\bin\ggml-cpu*.dll` variant
- `runtime\models\ggml-base.en.bin`

## 4) Verify release assets

- [ ] `Impulse-Setup-<version>.exe` exists
- [ ] Every matching split `.bin` part is present beside the installer
- [ ] The published SHA256 matches the installer
- [ ] If bootstrap hosting is configured, its manifest contains the exact runtime files produced by this build

## 5) Test on a clean Windows machine

Run:

```powershell
irm https://raw.githubusercontent.com/Izayauh/Impulse/main/scripts/qa/fresh-machine-test.ps1 | iex
```

Then verify:

- [ ] Silent per-user install completes and `Impulse.exe` is found
- [ ] First-run wizard detects or clearly asks for a microphone
- [ ] Dictation remains unavailable before activation
- [ ] A valid license activates successfully
- [ ] First model preparation finishes without freezing the UI
- [ ] `WIN + CTRL` records, transcribes, and pastes into at least two applications
- [ ] Dashboard and settings open
- [ ] Impulse exits cleanly and starts again
- [ ] Upgrade from the previous release preserves expected user data
- [ ] Uninstall behavior matches the documented data-retention choice

## 6) Publish deliberately

- [ ] Release notes describe install steps and known limitations honestly
- [ ] Download the published assets and repeat the checksum check
- [ ] Keep the release marked prerelease until the clean-machine test passes
