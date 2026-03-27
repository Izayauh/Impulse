@echo off
echo [WhisperLocal] Starting WhisperLocal (dev mode)...

set WHISPER_DEV_BYPASS_LICENSE=1

cd /d "%~dp0\..\.."
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)
python main.py --debug %*

