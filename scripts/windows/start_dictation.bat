@echo off
echo [WhisperLocal] start_dictation.bat is a compatibility launcher.
echo [WhisperLocal] Running in DEBUG mode so startup errors stay visible.
echo [WhisperLocal] Canonical launcher: run_whisperlocal.bat.
call "%~dp0\..\..\run_whisperlocal.bat" --debug %*

