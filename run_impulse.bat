@echo off
:: Impulse - Developer Launcher
:: Activates the .venv virtual environment and starts the application.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] No .venv found. Run: python -m venv .venv && pip install -r requirements.txt
)

python main.py %*
