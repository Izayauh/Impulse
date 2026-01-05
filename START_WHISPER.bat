@echo off
REM WhisperLocal Easy Launcher - Double-click to start
echo Starting WhisperLocal Dictation...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python flow_local_dictation.py
if errorlevel 1 pause

