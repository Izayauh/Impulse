# Impulse Release Checklist

Version comes from `APP_VERSION` in `src/whisper_local/config.py`. The tag drives
everything else.

## 1) Preflight

- [ ] `git status` is clean
- [ ] `APP_VERSION` matches the tag you are about to push
- [ ] Licensing and telemetry policy reviewed (telemetry is off by default)

## 2) What CI does for you

Pushing a `v*` tag runs `.github/workflows/release.yml`, which will **refuse to
publish** unless all of this passes:

- the full test suite, on the tagged commit
- the packaged tree contains every file the app reads at runtime
- the frozen `Impulse.exe` transcribes a generated sample and returns the words
- the built installer installs silently, and the installed copy transcribes too
- the app creates its own `state` and `logs` directories on a clean profile

A release that cannot dictate does not ship. This exists because the test suite
runs against Python source while users run an installer, and every user-facing
defect found in the August 2026 QA pass lived in the gap between the two.

## 3) Reproducing the gate locally

Worth doing before tagging, since it is faster than a round trip through CI:

```powershell
python -m PyInstaller --clean --noconfirm scripts\release\build_config.spec
python scripts\release\verify_package.py manifest dist\Impulse
python scripts\release\verify_package.py make-sample sample.wav
python scripts\release\verify_package.py selftest dist\Impulse\Impulse.exe sample.wav
```

Build gotcha: PyInstaller 6.3.0 breaks on setuptools >= 70, pinned in
`requirements.txt`.

## 4) Building the installer by hand

Only needed outside CI:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\release\build_installer.ps1 -Clean
powershell -ExecutionPolicy Bypass -File scripts\release\create_release_package.ps1
```

Produces `dist\Impulse-Setup-<version>.exe`, plus the delivery zip and its
`.sha256`. Set `WHISPER_BOOTSTRAP_BASE_URL` before building if you also want the
single-file bootstrap installer.

## 5) What still needs a human

CI proves the app installs and transcribes. It cannot prove the parts that need
a real person, a real key, and a machine with no history:

- [ ] First-run wizard reads correctly and picks the right microphone
- [ ] Activation succeeds with a real licence key
- [ ] Dictation lands in a real application, not just the selftest harness
- [ ] Dashboard opens and shows live stats rather than fallback data
- [ ] Offline grace behaves when the network is cut
- [ ] Uninstall leaves nothing behind

`scripts/qa/fresh-machine-test.ps1` drives the download, checksum, silent
install and key issuance, then hands you the 60-second manual part:

```powershell
irm https://raw.githubusercontent.com/Izayauh/Impulse/main/scripts/qa/fresh-machine-test.ps1 | iex
```

## 6) Publish

- [ ] Push the tag; confirm the gate went green rather than assuming it did
- [ ] Check the release carries the installer, its parts, and the `.sha256`
- [ ] Release notes state known issues
