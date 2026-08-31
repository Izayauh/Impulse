# Release Instructions for Impulse

This document explains how to create and publish new releases of Impulse.

## Automated Releases (Recommended)

Releases are automated via GitHub Actions. When you push a version tag, the workflow automatically:
1. Builds the installer using PyInstaller and Inno Setup
2. Downloads the required Whisper models from Hugging Face
3. Builds the split GitHub release installer path
4. Optionally builds a single-file bootstrap installer when hosted payload URLs are configured
5. Calculates and publishes SHA256 checksums

### Creating a New Release

1. **Update the changelog** (optional but recommended):
   ```bash
   # Edit CHANGELOG.md with your changes
   ```

2. **Commit any final changes**:
   ```bash
   git add .
   git commit -m "Prepare for v1.0.0 release"
   git push origin main
   ```

3. **Create and push a version tag**:
   ```bash
   git tag v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

4. **Monitor the build**:
   - Go to [Actions tab](https://github.com/Izayauh/Impulse/actions)
   - Watch the "Build and Release" workflow
   - Build takes approximately 15-30 minutes (downloading models is the slowest part)

5. **Verify the release**:
   - Go to [Releases](https://github.com/Izayauh/Impulse/releases)
   - Download and test the bootstrap installer on a clean Windows machine when present
   - Also verify the split installer fallback still works

### Version Numbering

Use semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes or complete rewrites
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes and minor improvements

Examples:
- `v1.0.0` - Initial release
- `v1.1.0` - Added new feature
- `v1.1.1` - Bug fix
- `v2.0.0` - Major rewrite

## Manual Release (Alternative)

If you need to create a release manually:

### Prerequisites

1. **Build tools installed**:
   - Python 3.10+ (Python 3.11 matches the automated release)
   - PyInstaller: `pip install pyinstaller`
   - Inno Setup 6: [Download](https://jrsoftware.org/isdl.php)

2. **Required files present**:
   - `whisper-cli.exe`
   - `ggml-base.dll`, `ggml.dll`, `whisper.dll`, and at least one `ggml-cpu*.dll`
   - `runtime/models/ggml-base.en.bin` as the offline fallback model
   - Optional for bootstrap builds: `WHISPER_BOOTSTRAP_BASE_URL` pointing at the public payload folder

### Build Steps

1. **Build the installer locally**:
   ```powershell
   .\scripts\release\build_installer.ps1
   ```

2. **Verify the output**:
   ```powershell
   # Check the split installer was created
   dir dist\Impulse-Setup-*.exe

   # Check the bootstrap installer was created when WHISPER_BOOTSTRAP_BASE_URL is set
   dir dist\Impulse-Bootstrap-Setup-*.exe
   ```

3. **Create the release on GitHub**:
   - Go to https://github.com/Izayauh/Impulse/releases/new
   - Create a new tag (e.g., `v1.0.0`)
   - Add release title: "Impulse v1.0.0"
   - Add release notes
   - Upload `dist\Impulse-Bootstrap-Setup-1.0.0.exe` and `dist\Impulse-Bootstrap-Payload-1.0.0.json` when bootstrap hosting is configured
   - Upload `dist\Impulse-Setup-1.0.0.exe`
   - Upload every matching `dist\Impulse-Setup-1.0.0-*.bin` file
   - Upload `dist\Impulse-Setup-1.0.0.sha256`
   - Click "Publish release"

## Pre-Release Checklist

Before creating a release, verify:

- [ ] All tests pass locally
- [ ] Application starts correctly
- [ ] Dictation works (WIN + CTRL hotkey)
- [ ] Settings window opens (WIN + CTRL + S)
- [ ] Release includes the installer EXE and all required `.bin` parts
- [ ] Bootstrap installer works when `WHISPER_BOOTSTRAP_BASE_URL` is configured
- [ ] The `base.en` offline fallback model is included
- [ ] CHANGELOG.md is updated
- [ ] Version numbers are consistent across files

## Bootstrap Payload Hosting

Set `WHISPER_BOOTSTRAP_BASE_URL` to a public folder URL that will serve the payload files listed in `dist\Impulse-Bootstrap-Payload-<version>.json`.

Example layout:

```text
https://downloads.example.com/whisper/v1.0.4/
  _internal/ggml-base.dll
  _internal/ggml-cpu-<architecture>.dll
  _internal/ggml.dll
  _internal/models/ggml-base.en.bin
  _internal/whisper-cli.exe
  _internal/whisper.dll
```

The manifest generator discovers the CPU/CUDA DLL variants produced by the current build and includes public URLs and SHA256 checksums for every hosted payload file.

## Troubleshooting Build Failures

### "whisper-cli.exe not found"

The workflow downloads whisper-cli.exe from whisper.cpp releases. If this fails:
- Check if whisper.cpp has a new release format
- Manually download from https://github.com/ggerganov/whisper.cpp/releases
- Commit the executable to the repository

### "Model download failed"

Models are downloaded from Hugging Face. If downloads fail:
- Check your internet connection
- Verify the model URLs in the workflow are correct
- Consider hosting models on GitHub LFS

### "Inno Setup failed"

- Ensure all source files exist in `dist\Impulse\`
- Check that `src\whisper_local\Impulse.ico` is present
- Verify `installer.iss` syntax is correct
- Verify `bootstrap_payload.iss.inc` was generated before compiling `bootstrap_installer.iss`

### "Build takes too long"

The build can take 15-30 minutes due to:
- Downloading the model and runtime dependencies
- Installing dependencies
- Compressing the installer

This is normal for the first build. Consider caching if builds become too slow.

## Files Involved in Release

| File | Purpose |
|------|---------|
| `.github/workflows/release.yml` | Automated build workflow |
| `scripts/release/build_installer.ps1` | Local build script |
| `scripts/release/build_config.spec` | PyInstaller configuration |
| `scripts/release/installer.iss` | Inno Setup installer script |
| `CHANGELOG.md` | Version history |

## Contact

If you encounter issues with the release process, open an issue on GitHub.
