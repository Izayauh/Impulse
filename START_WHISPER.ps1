# WhisperLocal Easy Launcher
# Double-click this file to start the application

Write-Host "Starting WhisperLocal Dictation..." -ForegroundColor Cyan

# Change to script directory
Set-Location $PSScriptRoot

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Run the application
python flow_local_dictation.py

# Keep window open if there's an error
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Press any key to close..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

