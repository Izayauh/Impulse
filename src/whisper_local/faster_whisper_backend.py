"""Shared faster-whisper/CTranslate2 runtime helpers."""

from __future__ import annotations

import ctypes
import logging
import os
import re
import site
import sys
import threading
from typing import Dict, Iterable, List, Tuple


logger = logging.getLogger(__name__)

_MODEL_CACHE: Dict[Tuple[str, str, str], object] = {}
_MODEL_CACHE_LOCK = threading.Lock()
_DLL_DIRECTORY_HANDLES = []
_CUDA_DLL_HANDLES = []

# Dictation-tuned decode guards. Whisper fabricates words on silence and
# noise and loops on phrases; these keep that output away from the paste.
# Silero VAD cuts the non-speech stretches before decoding: a pause has to
# last half a second to split a segment, and each segment keeps 200 ms of
# padding so word onsets are not clipped.
VAD_PARAMETERS = {"min_silence_duration_ms": 500, "speech_pad_ms": 200}
NO_SPEECH_PROB_MAX = 0.6  # above this the decoder itself says "not speech"
AVG_LOGPROB_MIN = -1.0  # below this the decode is a guess, not a transcript
REPEAT_NGRAM_MAX_WORDS = 6
REPEAT_MIN_RUN = 3

_VAD_ASSET_WARNED = False

# What a real CUDA attempt taught us: None = untried, True/False = observed.
# Device visibility alone is not proof the GPU can run inference here.
_CUDA_VERIFIED = None


def model_name_for_mode(model_name: str) -> str:
    """Map a selection-state model to its faster-whisper/CT2 model id.

    Idempotent: both callers and preload_model apply it, so CT2 ids must
    map to themselves ("base.en" -> "base.en", not back to turbo).
    """
    name = str(model_name or "").strip().lower()
    if name in ("base", "base.en"):
        return "base.en"
    return "turbo"


def runtime_for_gpu(has_gpu: bool) -> Tuple[str, str]:
    if has_gpu and _cuda_runtime_available():
        return "cuda", "float16"
    return "cpu", "int8"


def gpu_is_usable() -> bool:
    """Public capability probe for model selection.

    Model choice must follow what the machine can actually accelerate, not
    what a VRAM reading suggests: picking the heavy model on a card whose
    CUDA path is unusable is the slowest possible outcome.
    """
    return _cuda_runtime_available()


def _cuda_runtime_available() -> bool:
    """Report whether CTranslate2 can actually run inference on the GPU here.

    Three things are distinct and were previously conflated:
      1. a card exists (a VRAM reading),
      2. CUDA can see a device (``get_cuda_device_count``),
      3. inference can actually run, which additionally needs cuDNN.

    Only (3) should attract the heavy model; selecting on (1) or (2) leaves
    turbo running on CPU, the slowest pairing available. An observed result
    from a real attempt always wins over any prediction made here.
    """
    if _CUDA_VERIFIED is not None:
        return _CUDA_VERIFIED

    persisted = _load_persisted_cuda_verdict()
    if persisted is not None:
        return persisted

    if os.name == "nt":
        _configure_cuda_dll_paths()
        try:
            _preload_cuda_dlls()
        except OSError:
            pass  # advisory only; CTranslate2 may still resolve them itself

    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() <= 0:
            return False
    except Exception:
        return False

    # cuDNN is required for Whisper inference on CUDA. If it is not present
    # (e.g. not shipped in a frozen bundle), the CUDA path will fail at model
    # load and silently demote to CPU, so do not claim the GPU is usable.
    return _cudnn_present()


def _cudnn_present() -> bool:
    if os.name != "nt":
        return True
    return bool(_find_cuda_dlls("cudnn*.dll"))


def _capability_signature() -> str:
    """Identify the CUDA environment, so a stored verdict self-invalidates.

    If the user installs cuDNN or upgrades CTranslate2, the signature changes
    and the stored verdict is ignored rather than pinning them to CPU forever.
    """
    try:
        import ctranslate2

        version = getattr(ctranslate2, "__version__", "?")
    except Exception:
        version = "?"
    dlls = sorted(os.path.basename(p) for p in _find_cuda_dlls("cudnn*.dll"))
    return f"{version}|{','.join(dlls)}"


def _capability_file() -> str:
    from whisper_local.config import get_user_data_dir

    return os.path.join(get_user_data_dir(), "state", "gpu_capability.json")


def _load_persisted_cuda_verdict():
    try:
        import json

        with open(_capability_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("signature") != _capability_signature():
            return None
        verdict = data.get("cuda_ok")
        return verdict if isinstance(verdict, bool) else None
    except Exception:
        return None


def _persist_cuda_verdict(succeeded: bool) -> None:
    try:
        import json

        path = _capability_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cuda_ok": succeeded, "signature": _capability_signature()}, f, indent=2)
    except Exception:
        pass


def _record_cuda_outcome(device: str, succeeded: bool) -> None:
    """Remember what a real CUDA attempt proved, so selection self-corrects.

    Persisted, because the prediction is optimistic and a fresh process would
    otherwise repeat the same wrong guess on every launch: the app would pick
    the heavy model, fail over to CPU, and stay slow forever.
    """
    global _CUDA_VERIFIED
    if device != "cuda":
        return
    changed = _CUDA_VERIFIED != succeeded
    _CUDA_VERIFIED = succeeded
    if changed:
        _persist_cuda_verdict(succeeded)
        if not succeeded:
            print("[faster-whisper] CUDA unusable here; future runs will select the CPU-friendly model")


def _candidate_site_package_dirs() -> List[str]:
    candidates = []
    try:
        candidates.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        user_site = site.getusersitepackages()
        if user_site:
            candidates.append(user_site)
    except Exception:
        pass
    return [path for path in candidates if path and os.path.isdir(path)]


def _configure_cuda_dll_paths() -> None:
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return

    dll_dirs = []
    for base in _candidate_site_package_dirs():
        nvidia_dir = os.path.join(base, "nvidia")
        for package_name in ("cudnn", "cublas", "cuda_nvrtc"):
            candidate = os.path.join(nvidia_dir, package_name, "bin")
            if os.path.isdir(candidate):
                dll_dirs.append(candidate)

    known_dirs = {path for path, _handle in _DLL_DIRECTORY_HANDLES}
    for dll_dir in dll_dirs:
        if dll_dir in known_dirs:
            continue
        try:
            handle = os.add_dll_directory(dll_dir)
            _DLL_DIRECTORY_HANDLES.append((dll_dir, handle))
        except OSError:
            pass


def _find_cuda_dlls(pattern: str) -> List[str]:
    """Find CUDA DLLs by glob across nvidia wheels and the frozen bundle."""
    import glob

    search_dirs = []
    for base in _candidate_site_package_dirs():
        nvidia_dir = os.path.join(base, "nvidia")
        for package_name in ("cudnn", "cublas", "cuda_nvrtc"):
            search_dirs.append(os.path.join(nvidia_dir, package_name, "bin"))
        # torch and ctranslate2 ship their own CUDA runtimes.
        search_dirs.append(os.path.join(base, "torch", "lib"))
        search_dirs.append(os.path.join(base, "ctranslate2"))
    # PyInstaller lays bundled DLLs beside the executable's _internal dir.
    search_dirs.append(os.path.dirname(os.path.abspath(__file__)))
    if getattr(sys, "frozen", False):
        search_dirs.append(getattr(sys, "_MEIPASS", ""))

    found = []
    for directory in search_dirs:
        if directory and os.path.isdir(directory):
            found.extend(glob.glob(os.path.join(directory, pattern)))
    return found


def _preload_cuda_dlls() -> None:
    if _CUDA_DLL_HANDLES:
        return

    # Discover by pattern, not by pinned version: CUDA/cuDNN majors move
    # (cublas64_12 -> _13, cudnn64_9 -> ...) and a stale literal name here
    # silently demotes GPU machines to CPU.
    loaded = []
    for pattern in ("cublas64_*.dll", "cublasLt64_*.dll", "cudnn*64_*.dll"):
        for path in _find_cuda_dlls(pattern):
            try:
                loaded.append(ctypes.WinDLL(path))
            except OSError:
                pass
    _CUDA_DLL_HANDLES.extend(loaded)


def runtime_candidates(has_gpu: bool) -> List[Tuple[str, str]]:
    if has_gpu and _cuda_runtime_available():
        return [("cuda", "float16"), ("cpu", "int8")]
    return [("cpu", "int8")]


def preload_model(model_name: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    ct2_model = model_name_for_mode(model_name)
    cache_key = (ct2_model, device, compute_type)
    with _MODEL_CACHE_LOCK:
        model = _MODEL_CACHE.get(cache_key)
        if model is None:
            model = WhisperModel(ct2_model, device=device, compute_type=compute_type)
            _MODEL_CACHE[cache_key] = model
    return model, ct2_model


def preload_model_with_fallback(model_name: str, has_gpu: bool):
    errors = []
    for device, compute_type in runtime_candidates(has_gpu):
        try:
            model, ct2_model = preload_model(model_name, device, compute_type)
            _record_cuda_outcome(device, True)
            return model, ct2_model, device, compute_type
        except Exception as exc:
            _record_cuda_outcome(device, False)
            errors.append(f"{device}/{compute_type}: {exc}")
    raise RuntimeError("; ".join(errors))


def segment_is_speech(avg_logprob, no_speech_prob) -> bool:
    """Whisper's own confidence read on a segment.

    faster-whisper only skips a window when both signals fail together; for
    dictation either one alone is enough to say the text was not spoken.
    Missing values keep the segment.
    """
    try:
        if no_speech_prob is not None and float(no_speech_prob) > NO_SPEECH_PROB_MAX:
            return False
        if avg_logprob is not None and float(avg_logprob) < AVG_LOGPROB_MIN:
            return False
    except (TypeError, ValueError):
        return True
    return True


def filter_segments(segments: Iterable) -> Tuple[List[str], int, int]:
    """Keep the segments that read as speech. Returns (texts, dropped, total)."""
    texts: List[str] = []
    dropped = 0
    total = 0
    for segment in segments:
        total += 1
        text = (getattr(segment, "text", "") or "").strip()
        if not text:
            continue
        if not segment_is_speech(
            getattr(segment, "avg_logprob", None), getattr(segment, "no_speech_prob", None)
        ):
            dropped += 1
            continue
        texts.append(text)
    return texts, dropped, total


def _repeat_key(token: str) -> str:
    return re.sub(r"[^\w']+", "", token.lower())


def _collapse_line(tokens: List[str], max_n: int, min_run: int) -> Tuple[List[str], int]:
    keys = [_repeat_key(t) for t in tokens]
    out: List[str] = []
    runs = 0
    i = 0
    while i < len(tokens):
        collapsed = False
        for n in range(1, max_n + 1):
            if i + n * min_run > len(tokens):
                break
            unit = keys[i : i + n]
            if not any(unit):
                continue
            count = 1
            while keys[i + count * n : i + (count + 1) * n] == unit:
                count += 1
            if count >= min_run:
                kept = tokens[i : i + n]
                # Keep the run's final token so its trailing punctuation survives.
                kept[-1] = tokens[i + count * n - 1]
                out.extend(kept)
                i += count * n
                runs += 1
                collapsed = True
                break
        if not collapsed:
            out.append(tokens[i])
            i += 1
    return out, runs


def collapse_repeated_ngrams(
    text: str, max_n: int = REPEAT_NGRAM_MAX_WORDS, min_run: int = REPEAT_MIN_RUN
) -> Tuple[str, int]:
    """Collapse a phrase repeated ``min_run`` or more times in a row to one copy.

    Whisper loops on noise ("thank you. thank you. thank you. thank you.");
    nobody dictates the same words three times running. Comparison ignores
    case and punctuation; lines are handled separately and a line without a
    run is returned untouched. Returns (text, runs_collapsed).
    """
    if not text:
        return text, 0
    total_runs = 0
    lines_out: List[str] = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < min_run:
            lines_out.append(line)
            continue
        runs_in_line = 0
        while True:
            tokens, runs = _collapse_line(tokens, max_n, min_run)
            if not runs:
                break
            runs_in_line += runs
        total_runs += runs_in_line
        lines_out.append(" ".join(tokens) if runs_in_line else line)
    return "\n".join(lines_out), total_runs


def _vad_filter_available() -> bool:
    """True when the bundled Silero model is present.

    A frozen build that did not collect faster_whisper's assets has no VAD
    model; failing the whole transcription for that would be worse than the
    hallucinations the filter prevents, so it degrades to the old behaviour.
    """
    global _VAD_ASSET_WARNED
    try:
        from faster_whisper.utils import get_assets_path

        if os.path.isfile(os.path.join(get_assets_path(), "silero_vad_v6.onnx")):
            return True
    except Exception:
        pass
    if not _VAD_ASSET_WARNED:
        _VAD_ASSET_WARNED = True
        logger.warning("[faster-whisper] Silero VAD asset missing; transcribing without vad_filter")
    return False


def transcribe(
    filename: str,
    model_name: str,
    device: str,
    compute_type: str,
    *,
    beam_size: int,
    initial_prompt: str,
):
    model, ct2_model = preload_model(model_name, device, compute_type)
    use_vad = _vad_filter_available()
    segments, _info = model.transcribe(
        filename,
        language="en",
        beam_size=beam_size,
        # A single temperature: the fallback retries at 0.2..1.0 are where
        # fabricated words come from, and on CPU they multiply decode time.
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=use_vad,
        vad_parameters=dict(VAD_PARAMETERS) if use_vad else None,
        initial_prompt=initial_prompt,
    )
    texts, dropped, total = filter_segments(segments)
    text, collapsed = collapse_repeated_ngrams(" ".join(texts).strip())
    if dropped or collapsed:
        logger.debug(
            "[faster-whisper] post-filter: dropped %d of %d segments as non-speech, collapsed %d repeated runs",
            dropped,
            total,
            collapsed,
        )
    return text, ct2_model


def transcribe_with_fallback(
    filename: str,
    model_name: str,
    has_gpu: bool,
    *,
    beam_size: int,
    initial_prompt: str,
):
    errors = []
    for device, compute_type in runtime_candidates(has_gpu):
        try:
            text, ct2_model = transcribe(
                filename,
                model_name,
                device,
                compute_type,
                beam_size=beam_size,
                initial_prompt=initial_prompt,
            )
            _record_cuda_outcome(device, True)
            return text, ct2_model, device, compute_type
        except Exception as exc:
            _record_cuda_outcome(device, False)
            errors.append(f"{device}/{compute_type}: {exc}")
    raise RuntimeError("; ".join(errors))
