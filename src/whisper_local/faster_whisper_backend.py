"""Shared faster-whisper/CTranslate2 runtime helpers."""

from __future__ import annotations

import ctypes
import os
import site
import sys
import threading
from typing import Dict, List, Tuple


_MODEL_CACHE: Dict[Tuple[str, str, str], object] = {}
_MODEL_CACHE_LOCK = threading.Lock()
_DLL_DIRECTORY_HANDLES = []
_CUDA_DLL_HANDLES = []

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


def _record_cuda_outcome(device: str, succeeded: bool) -> None:
    """Remember what a real CUDA attempt proved, so selection self-corrects."""
    global _CUDA_VERIFIED
    if device == "cuda":
        _CUDA_VERIFIED = succeeded


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
    segments, _info = model.transcribe(
        filename,
        language="en",
        beam_size=beam_size,
        condition_on_previous_text=False,
        vad_filter=False,
        initial_prompt=initial_prompt,
    )
    text = " ".join((segment.text or "").strip() for segment in segments).strip()
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
