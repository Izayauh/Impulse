"""Verify a frozen Impulse build before it is allowed to ship.

The test suite runs against Python source; users run an installer. Every
user-facing defect found in the 2026-08-22 QA pass lived in the gap between
those two things, and all 411 tests passed in every one of those worlds:

  * pywebview's ``webview/js`` assets were not packaged, so ``window.pywebview``
    never existed and every dashboard API call silently returned null
  * ``dashboard.html`` / ``styles.css`` were packaged to paths the app does not
    read
  * frozen builds never created ``logs``/``state``, so the WAV write failed with
    no trail

This script closes that gap. It inspects the packaged tree for the files the app
actually reads, then drives a real transcription through the frozen binary.

Usage:

    python scripts/release/verify_package.py make-sample sample.wav
    python scripts/release/verify_package.py manifest dist/Impulse
    python scripts/release/verify_package.py selftest dist/Impulse/Impulse.exe sample.wav

Every subcommand exits non-zero on failure so a release job stops on it.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys


# The phrase spoken into the sample WAV. Content words from it must come back
# out of the transcript, which is what separates "the engine ran" from "the
# engine returned an empty string and reported success".
SAMPLE_PHRASE = "the quick brown fox jumps over the lazy dog"

# A transcript must recover at least this fraction of the phrase's content
# words. Kept below 1.0 because the sample is synthetic speech and base.en is
# the smallest production model; the point is to prove real transcription, not
# to grade accuracy.
MIN_WORD_RECALL = 0.5

# Files the app reads at runtime, relative to the frozen tree root. Each entry
# is here because its absence shipped, or would ship, a silent failure.
REQUIRED_FILES = [
    ("Impulse.exe", "the application itself"),
    # pywebview injects window.pywebview from these; without them the dashboard
    # renders and every api call returns null.
    ("_internal/webview/js/api.js", "pywebview JS bridge"),
    # gui_host resolves the dashboard relative to its own module dir.
    ("_internal/whisper_local/ui/dashboard.html", "dashboard markup (module dir)"),
    ("_internal/whisper_local/ui/dashboard_stats.js", "dashboard fallback data (module dir)"),
    ("_internal/whisper_local/ui/styles.css", "dashboard stylesheet (module dir)"),
    # Bundle-root copies, read by the other dashboard resolution path.
    ("_internal/dashboard.html", "dashboard markup (bundle root)"),
    ("_internal/dashboard_stats.js", "dashboard fallback data (bundle root)"),
    # start_tray resolves this via res_path('ui/assets/mic_logo.png').
    ("_internal/ui/assets/mic_logo.png", "tray logo"),
    # Offline fallback engine and model: dictation must work with no network.
    ("_internal/models/ggml-base.en.bin", "offline fallback model"),
    ("_internal/whisper-cli.exe", "whisper.cpp binary"),
    ("_internal/whisper.dll", "whisper.cpp library"),
    ("_internal/Impulse.ico", "application icon"),
]

# Families that ship per-architecture variants, so they are matched by glob
# rather than by name. Pinning exact DLL names is what broke when CTranslate2
# moved to CUDA 13.
REQUIRED_GLOBS = [
    ("_internal/ggml*.dll", "ggml runtime libraries"),
    ("_internal/ggml-cpu*.dll", "ggml CPU backend"),
]


def _content_words(text: str) -> list[str]:
    """Lowercase alphanumeric words, with the phrase's stop words dropped."""
    stop = {"the", "over", "a", "an", "and"}
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in stop]


def word_recall(expected: str, actual: str) -> float:
    """Fraction of the expected phrase's content words present in ``actual``.

    Order-insensitive and punctuation-insensitive, because ASR output differs
    from the prompt in both without being wrong.
    """
    wanted = _content_words(expected)
    if not wanted:
        return 1.0
    got = set(_content_words(actual))
    return sum(1 for w in wanted if w in got) / len(wanted)


def _fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def cmd_manifest(dist_dir: str) -> int:
    """Assert the packaged tree contains every file the app reads."""
    if not os.path.isdir(dist_dir):
        return _fail(f"no such build directory: {dist_dir}")

    missing = []
    for rel, why in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(dist_dir, rel)):
            missing.append(f"{rel}  ({why})")

    for pattern, why in REQUIRED_GLOBS:
        if not glob.glob(os.path.join(dist_dir, pattern)):
            missing.append(f"{pattern}  ({why})")

    if missing:
        print(f"Packaged tree is missing {len(missing)} required item(s):", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        return _fail("the build would ship broken; see the list above")

    checked = len(REQUIRED_FILES) + len(REQUIRED_GLOBS)
    print(f"Manifest OK: all {checked} required entries present in {dist_dir}")
    return 0


def cmd_make_sample(wav_path: str) -> int:
    """Speak SAMPLE_PHRASE to a 16 kHz mono WAV using Windows SAPI."""
    wav_path = os.path.abspath(wav_path)
    os.makedirs(os.path.dirname(wav_path) or ".", exist_ok=True)
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo("
        "16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, "
        "[System.Speech.AudioFormat.AudioChannel]::Mono); "
        f"$s.SetOutputToWaveFile('{wav_path}', $f); "
        f"$s.Speak('{SAMPLE_PHRASE}'); "
        "$s.Dispose()"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return _fail(f"SAPI synthesis failed: {proc.stderr.strip()}")
    if not os.path.isfile(wav_path) or os.path.getsize(wav_path) < 1024:
        return _fail(f"SAPI produced no usable audio at {wav_path}")

    print(f"Sample OK: {wav_path} ({os.path.getsize(wav_path) / 1024:.0f} KB)")
    return 0


def _parse_report(stdout: str) -> dict | None:
    """Pull the selftest's JSON report out of stdout.

    The transcription route logs progress lines to the same stream, so scan
    backwards for the last line that parses as the report object.
    """
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict) and "ok" in parsed:
            return parsed
    return None


def cmd_selftest(exe_path: str, wav_path: str, timeout: int) -> int:
    """Transcribe through the frozen binary and assert the result is real."""
    if not os.path.isfile(exe_path):
        return _fail(f"no such executable: {exe_path}")
    if not os.path.isfile(wav_path):
        return _fail(f"no such sample: {wav_path}")

    # CreateProcess does not accept the forward-slash paths os.path does, so
    # hand it something Windows will definitely launch.
    exe_path = os.path.abspath(exe_path)
    wav_path = os.path.abspath(wav_path)

    # subprocess pipes work against a GUI-subsystem exe, which is why this runs
    # here rather than in PowerShell, where `&` does not even wait for it.
    try:
        proc = subprocess.run(
            [exe_path, "--selftest", wav_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return _fail(f"selftest did not finish within {timeout}s")
    except OSError as exc:
        # A build that cannot even start must say so plainly; this is the
        # shape of a missing DLL or a wrong-architecture binary.
        return _fail(f"could not launch {exe_path}: {exc}")

    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)

    report = _parse_report(proc.stdout)
    if report is None:
        return _fail(
            f"selftest printed no JSON report (exit {proc.returncode}); "
            "the frozen build failed before it could transcribe"
        )
    if not report.get("ok"):
        return _fail(f"selftest reported failure: {report.get('error') or report}")

    transcript = str(report.get("transcript") or "").strip()
    if not transcript:
        return _fail("selftest succeeded but returned an empty transcript")

    recall = word_recall(SAMPLE_PHRASE, transcript)
    if recall < MIN_WORD_RECALL:
        return _fail(
            f"transcript recovered {recall:.0%} of the spoken phrase "
            f"(need {MIN_WORD_RECALL:.0%}); got: {transcript!r}"
        )

    print(
        f"Selftest OK: model={report.get('model')} "
        f"audio={report.get('audio_sec')}s processing={report.get('processing_sec')}s "
        f"recall={recall:.0%}"
    )
    print(f"  transcript: {transcript}")
    return 0


def cmd_datadirs(data_dir: str) -> int:
    """Assert the app created its own working directories on first run.

    Frozen builds once shipped without doing this, so recordings failed at the
    WAV write and file logging was dead, with nothing written down anywhere.
    """
    if not os.path.isdir(data_dir):
        return _fail(f"the app created no data directory at {data_dir}")

    missing = [name for name in ("state", "logs") if not os.path.isdir(os.path.join(data_dir, name))]
    if missing:
        return _fail(f"the app did not create {', '.join(missing)} under {data_dir}")

    print(f"Data directories OK: state, logs present under {data_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("manifest", help="check the packaged tree for required files")
    p.add_argument("dist_dir", help="the frozen build directory, e.g. dist/Impulse")

    p = sub.add_parser("make-sample", help="synthesize the test WAV with Windows SAPI")
    p.add_argument("wav_path")

    p = sub.add_parser("selftest", help="transcribe a sample through the frozen binary")
    p.add_argument("exe_path")
    p.add_argument("wav_path")
    p.add_argument("--timeout", type=int, default=900, help="seconds (default: 900)")

    p = sub.add_parser("datadirs", help="check the app created its working directories")
    p.add_argument("data_dir", help=r"e.g. %%LOCALAPPDATA%%\Impulse")

    args = parser.parse_args(argv)

    if args.command == "manifest":
        return cmd_manifest(args.dist_dir)
    if args.command == "make-sample":
        return cmd_make_sample(args.wav_path)
    if args.command == "selftest":
        return cmd_selftest(args.exe_path, args.wav_path, args.timeout)
    if args.command == "datadirs":
        return cmd_datadirs(args.data_dir)
    return _fail(f"unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
