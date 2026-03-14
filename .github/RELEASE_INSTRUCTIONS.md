# Release Instructions for WhisperLocal

This document explains how to create and publish new releases of WhisperLocal.

## Automated Releases (Recommended)

Releases are automated via GitHub Actions. When you push a version tag, the workflow automatically:
1. Builds the installer using PyInstaller and Inno Setup
2. Downloads the required Whisper models from Hugging Face
3. Creates a GitHub Release with the split installer assets attached
4. Calculates and publishes SHA256 checksums

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
   - Go to [Actions tab](https://github.com/Izayauh/whisper/actions)
   - Watch the "Build and Release" workflow
   - Build takes approximately 15-30 minutes (downloading models is the slowest part)

5. **Verify the release**:
   - Go to [Releases](https://github.com/Izayauh/whisper/releases)
   - Download and test the installer on a clean Windows machine

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
   - Python 3.8+
   - PyInstaller: `pip install pyinstaller`
   - Inno Setup 6: [Download](https://jrsoftware.org/isdl.php)

2. **Required files present**:
   - `whisper-cli.exe`
   - `*.dll` files (ggml-base.dll, ggml-cpu.dll, etc.)
   - `models/` directory with AI models

### Build Steps

1. **Build the installer locally**:
   ```powershell
   .\build_installer.ps1
   ```

2. **Verify the output**:
   ```powershell
   # Check the installer was created
   dir dist\WhisperLocal-Setup-*.exe
   ```

3. **Create the release on GitHub**:
   - Go to https://github.com/Izayauh/whisper/releases/new
   - Create a new tag (e.g., `v1.0.0`)
   - Add release title: "WhisperLocal v1.0.0"
   - Add release notes
   - Upload `dist\WhisperLocal-Setup-1.0.0.exe`
   - Upload every matching `dist\WhisperLocal-Setup-1.0.0-*.bin` file
   - Upload `dist\WhisperLocal-Setup-1.0.0.sha256`
   - Click "Publish release"

## Pre-Release Checklist

Before creating a release, verify:

- [ ] All tests pass locally
- [ ] Application starts correctly
- [ ] Dictation works (WIN + CTRL hotkey)
- [ ] Settings window opens (WIN + CTRL + S)
- [ ] Release includes the installer EXE and all required `.bin` parts
- [ ] All three AI models are included
- [ ] CHANGELOG.md is updated
- [ ] Version numbers are consistent across files

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

- Ensure all source files exist in `dist\WhisperLocal\`
- Check that `Whisper.ico` is present
- Verify `installer.iss` syntax is correct

### "Build takes too long"

The build can take 15-30 minutes due to:
- Downloading ~5 GB of AI models
- Installing dependencies
- Compressing the installer

This is normal for the first build. Consider caching if builds become too slow.

## Files Involved in Release

| File | Purpose |
|------|---------|
| `.github/workflows/release.yml` | Automated build workflow |
| `build_installer.ps1` | Local build script |
| `build_config.spec` | PyInstaller configuration |
| `installer.iss` | Inno Setup installer script |
| `CHANGELOG.md` | Version history |

## Contact

If you encounter issues with the release process, open an issue on GitHub.

