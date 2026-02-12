# Legacy wrapper kept for compatibility.
# Canonical startup script: run_whisperlocal.bat

Write-Host "[WhisperLocal] start_dictation.ps1 is a compatibility launcher." -ForegroundColor Yellow
Write-Host "[WhisperLocal] Running in DEBUG mode so startup errors stay visible." -ForegroundColor Yellow
Write-Host "[WhisperLocal] Canonical launcher: run_whisperlocal.bat." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "..\..\run_whisperlocal.bat") --debug







