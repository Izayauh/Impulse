"""Shared faster-whisper/CTranslate2 runtime helpers."""

from __future__ import annotations

import ctypes
import os
import site
import threading
from typing import Dict, List, Tuple


_MODEL_CACHE: Dict[Tuple[str, str, str], object] = {}
_MODEL_CACHE_LOCK = threading.Lock()
_DLL_DIRECTORY_HANDLES = []
_CUDA_DLL_HANDLES = []


def model_name_for_mode(model_name: str) -> str:
    _ = model_name
    return "turbo"


def runtime_for_gpu(has_gpu: bool) -> Tuple[str, str]:
    if has_gpu and _cuda_runtime_available():
        return "cuda", "float16"
    return "cpu", "int8"


def _cuda_runtime_available() -> bool:
    if os.name != "nt":
        return True
    _configure_cuda_dll_paths()
    try:
        _preload_cuda_dlls()
        return True
    except OSError:
        return False


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


def _find_cuda_dll(name: str) -> str | None:
    for base in _candidate_site_package_dirs():
        nvidia_dir = os.path.join(base, "nvidia")
        for package_name in ("cudnn", "cublas", "cuda_nvrtc"):
            candidate = os.path.join(nvidia_dir, package_name, "bin", name)
            if os.path.isfile(candidate):
                return candidate
    return None


def _preload_cuda_dlls() -> None:
    if _CUDA_DLL_HANDLES:
        return

    names = (
        "cublas64_12.dll",
        "cublasLt64_12.dll",
        "cudnn64_9.dll",
        "cudnn_adv64_9.dll",
        "cudnn_cnn64_9.dll",
        "cudnn_engines_precompiled64_9.dll",
        "cudnn_engines_runtime_compiled64_9.dll",
        "cudnn_graph64_9.dll",
        "cudnn_heuristic64_9.dll",
        "cudnn_ops64_9.dll",
    )
    loaded = []
    try:
        for name in names:
            path = _find_cuda_dll(name) or name
            loaded.append(ctypes.WinDLL(path))
    except OSError:
        loaded.clear()
        raise
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
            return model, ct2_model, device, compute_type
        except Exception as exc:
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
            return text, ct2_model, device, compute_type
        except Exception as exc:
            errors.append(f"{device}/{compute_type}: {exc}")
    raise RuntimeError("; ".join(errors))
