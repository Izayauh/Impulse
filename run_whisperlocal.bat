@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "DEBUG_MODE=0"
set "WEBVIEW_LOG="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--debug" (
    set "DEBUG_MODE=1"
    shift
    goto parse_args
)
if /I "%~1"=="--webview-log" (
    if "%~2"=="" (
        set "WEBVIEW_LOG=debug"
        shift
        goto parse_args
    )
    set "WEBVIEW_LOG=%~2"
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:args_done
if defined WEBVIEW_LOG set "PYWEBVIEW_LOG=%WEBVIEW_LOG%"
if "%DEBUG_MODE%"=="1" (
    set "WHISPERLOCAL_DEBUG=1"
    if not defined PYWEBVIEW_LOG set "PYWEBVIEW_LOG=debug"
)

set "PYTHON_EXE=python.exe"
set "PYTHONW_EXE=pythonw.exe"

if exist ".venv\Scripts\python.exe" if exist ".venv\Scripts\pythonw.exe" (
    ".venv\Scripts\python.exe" -c "import webview" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_EXE=.venv\Scripts\python.exe"
        set "PYTHONW_EXE=.venv\Scripts\pythonw.exe"
    ) else (
        echo [WhisperLocal] .venv is missing pywebview; using system Python.
    )
)

"%PYTHON_EXE%" -c "import webview, sounddevice, soundfile, keyboard, pyperclip, pyautogui, pystray, numpy; from PIL import Image" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [WhisperLocal] Dependency check failed for "%PYTHON_EXE%".
    echo [WhisperLocal] Install missing packages with:
    echo   "%PYTHON_EXE%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

if "%DEBUG_MODE%"=="1" (
    echo [WhisperLocal] Debug mode enabled.
    echo [WhisperLocal] PYWEBVIEW_LOG=%PYWEBVIEW_LOG%
    "%PYTHON_EXE%" main.py
    set "EXIT_CODE=!ERRORLEVEL!"
    if not "!EXIT_CODE!"=="0" echo WhisperLocal exited with error code !EXIT_CODE!.
    pause
    exit /b !EXIT_CODE!
)

start "" "%PYTHONW_EXE%" main.py
if !ERRORLEVEL! NEQ 0 (
    echo [WhisperLocal] Failed to start with pythonw. Launching debug mode...
    set "WHISPERLOCAL_DEBUG=1"
    if not defined PYWEBVIEW_LOG set "PYWEBVIEW_LOG=debug"
    "%PYTHON_EXE%" main.py
    set "EXIT_CODE=!ERRORLEVEL!"
    pause
    exit /b !EXIT_CODE!
)
exit /b 0
