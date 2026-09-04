# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for WhisperLocal
Bundles the dictation system with all dependencies, DLLs, and models.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# Get the directory where this spec file is located
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
ROOT_DIR = os.path.abspath(os.path.join(SPEC_DIR, '..', '..'))

# Application metadata
APP_NAME = 'Impulse'
APP_VERSION = '1.0.5-beta.4-dev'
MAIN_SCRIPT = os.path.join(ROOT_DIR, 'main.py')

# Bake telemetry token into the frozen build so it works without
# the env var being set on the end user's machine.
_telemetry_token = os.environ.get("WHISPER_TELEMETRY_TOKEN", "")
_build_config_path = os.path.join(ROOT_DIR, 'src', 'whisper_local', '_build_config.py')
with open(_build_config_path, 'w', encoding='utf-8') as _f:
    _f.write(f'# Auto-generated at build time — do not edit or commit\n')
    _f.write(f'TELEMETRY_TOKEN = {repr(_telemetry_token)}\n')

# Collect hidden imports for all required packages
hidden_imports = [
    'sounddevice',
    'soundfile',
    'keyboard',
    'pyperclip',
    'pyautogui',
    'pystray',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',
    'ctypes',
    'ctypes.wintypes',
    'tkinter',
    'tkinter.font',
    'json',
    'queue',
    'threading',
    'subprocess',
    'tempfile',
    'uuid',
    'datetime',
    'shlex',
    'shutil',
    're',
    'math',
    'msvcrt',
    'requests',
    'packaging',
    # Optional imports
    'winotify',
]

# Collect all submodules for complex packages
hidden_imports += collect_submodules('sounddevice')
hidden_imports += collect_submodules('soundfile')
hidden_imports += collect_submodules('pystray')
hidden_imports += collect_submodules('PIL')
hidden_imports += collect_submodules('faster_whisper')
hidden_imports += collect_submodules('ctranslate2')

# DLLs to bundle (whisper.cpp dependencies). Modern whisper.cpp releases
# ship per-CPU-arch variants (ggml-cpu-haswell.dll etc.) instead of one
# ggml-cpu.dll, so glob the whole family rather than naming files.
import glob as _glob
dll_files = [
    (os.path.relpath(p, ROOT_DIR), '.')
    for pattern in ('ggml*.dll', 'whisper.dll')
    for p in sorted(_glob.glob(os.path.join(ROOT_DIR, 'runtime', 'bin', pattern)))
]

# Executables to bundle
exe_files = [
    (os.path.join('runtime', 'bin', 'whisper-cli.exe'), '.'),
]

# Build binaries list - filter to only existing files
binaries = []

def _safe_collect_dynamic_libs(package_name):
    try:
        return collect_dynamic_libs(package_name)
    except Exception as exc:
        print(f"Warning: dynamic libs not collected for {package_name}: {exc}")
        return []

binaries += _safe_collect_dynamic_libs('ctranslate2')
binaries += _safe_collect_dynamic_libs('nvidia.cublas')
binaries += _safe_collect_dynamic_libs('nvidia.cuda_nvrtc')
binaries += _safe_collect_dynamic_libs('nvidia.cudnn')

for dll, dest in dll_files:
    dll_path = os.path.join(ROOT_DIR, dll)
    if os.path.exists(dll_path):
        binaries.append((dll_path, dest))
    else:
        print(f"Warning: DLL not found: {dll_path}")

for exe, dest in exe_files:
    exe_path = os.path.join(ROOT_DIR, exe)
    if os.path.exists(exe_path):
        binaries.append((exe_path, dest))
    else:
        print(f"Warning: EXE not found: {exe_path}")

# Data files to bundle
datas = [
    # Offline fallback model only. faster-whisper "turbo" (the primary engine)
    # downloads on first run; base.en keeps whisper.cpp fallback dictation
    # working with no network. Medium/large GGML models are no longer bundled.
    (os.path.join(ROOT_DIR, 'runtime', 'models', 'ggml-base.en.bin'), 'models'),
    # Application icon
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'Impulse.ico'), '.'),
    # Include package static assets
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'message-send.mp3'), '.'),
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'dashboard.html'), '.'),
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'dashboard_stats.js'), '.'),
    # gui_host resolves the dashboard relative to its own module dir
    # (_internal/whisper_local/ui), so the UI files must also live there.
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'dashboard.html'), os.path.join('whisper_local', 'ui')),
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'dashboard_stats.js'), os.path.join('whisper_local', 'ui')),
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'styles.css'), os.path.join('whisper_local', 'ui')),
    # styles.css loads Geist and Geist Mono via url("assets/fonts/...") relative
    # to itself, so the folder must sit next to it in the bundle.
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'assets', 'fonts'), os.path.join('whisper_local', 'ui', 'assets', 'fonts')),
    # start_tray resolves this via res_path('ui/assets/mic_logo.png'), which is
    # relative to the bundle root rather than the package dir.
    (os.path.join(ROOT_DIR, 'src', 'whisper_local', 'ui', 'assets', 'mic_logo.png'), os.path.join('ui', 'assets')),
]

# Filter datas to only existing files
datas = [(src, dest) for src, dest in datas if os.path.exists(src)]

# Collect additional data files from packages
datas += collect_data_files('sounddevice')
datas += collect_data_files('soundfile')
# pywebview injects window.pywebview from its bundled JS assets (webview/js);
# without them the dashboard renders but every api call silently fails.
datas += collect_data_files('webview')
# faster-whisper's vad_filter needs its bundled Silero model (assets/silero_vad_*.onnx);
# without it the frozen build silently skips VAD and hallucinates on silence.
datas += collect_data_files('faster_whisper')

# Analysis configuration
a = Analysis(
    [MAIN_SCRIPT],
    pathex=[ROOT_DIR, os.path.join(ROOT_DIR, 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'scipy',
        'pandas',
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'docutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate binaries/datas
a.binaries = list(set(a.binaries))
a.datas = list(set(a.datas))

# Create the PYZ archive
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],  # Don't include binaries in EXE (use COLLECT instead)
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression if available
    upx_exclude=[
        # Don't compress these (causes issues)
        'vcruntime140.dll',
        'python*.dll',
        'ggml*.dll',
        'whisper*.dll',
    ],
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT_DIR, 'src', 'whisper_local', 'Impulse.ico'),
    version_info=None,  # Could add version info file here
)

# Collect all files into distribution folder
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python*.dll',
        'ggml*.dll',
        'whisper*.dll',
    ],
    name=APP_NAME,
)

# Print summary
print(f"\n{'='*60}")
print(f"PyInstaller Build Configuration for {APP_NAME} v{APP_VERSION}")
print(f"{'='*60}")
print(f"Main script: {MAIN_SCRIPT}")
print(f"DLLs bundled: {len([b for b in binaries if b[0].endswith('.dll')])}")
print(f"EXEs bundled: {len([b for b in binaries if b[0].endswith('.exe')])}")
print(f"Data files: {len(datas)}")
print(f"Hidden imports: {len(hidden_imports)}")
print(f"Output: dist/{APP_NAME}/")
print(f"{'='*60}\n")
