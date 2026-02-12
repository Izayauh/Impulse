@echo off
REM WhisperLocal Project Cleanup Script
REM This script removes redundant and unused files identified in the audit

echo ========================================
echo  WhisperLocal Project Cleanup
echo ========================================
echo.
echo This script will delete the following files:
echo.
echo UNUSED WHISPER_LOCAL MODULES:
echo   - whisper_local\logging_config.py
echo   - whisper_local\performance.py
echo   - whisper_local\crash_reporter.py
echo   - whisper_local\updater.py
echo   - whisper_local\health.py
echo.
echo REDUNDANT LAUNCHERS:
echo   - start_dictation.bat
echo   - start_dictation.ps1
echo.
echo TEST/DEBUG SCRIPTS:
echo   - test_gpu_monitor.py
echo   - test_idle_stability.py
echo   - gpu_chunk.ps1
echo   - gpu_run.ps1
echo   - test_system.ps1
echo   - scripts\security_audit.py
echo.
echo TOTAL: 13 files to delete
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Deleting files...
echo.

REM Delete unused whisper_local modules
if exist "whisper_local\logging_config.py" (
    del "whisper_local\logging_config.py"
    echo [DELETED] whisper_local\logging_config.py
)

if exist "whisper_local\performance.py" (
    del "whisper_local\performance.py"
    echo [DELETED] whisper_local\performance.py
)

if exist "whisper_local\crash_reporter.py" (
    del "whisper_local\crash_reporter.py"
    echo [DELETED] whisper_local\crash_reporter.py
)

if exist "whisper_local\updater.py" (
    del "whisper_local\updater.py"
    echo [DELETED] whisper_local\updater.py
)

if exist "whisper_local\health.py" (
    del "whisper_local\health.py"
    echo [DELETED] whisper_local\health.py
)

REM Delete redundant launchers
if exist "start_dictation.bat" (
    del "start_dictation.bat"
    echo [DELETED] start_dictation.bat
)

if exist "start_dictation.ps1" (
    del "start_dictation.ps1"
    echo [DELETED] start_dictation.ps1
)

REM Delete test/debug scripts
if exist "test_gpu_monitor.py" (
    del "test_gpu_monitor.py"
    echo [DELETED] test_gpu_monitor.py
)

if exist "test_idle_stability.py" (
    del "test_idle_stability.py"
    echo [DELETED] test_idle_stability.py
)

if exist "gpu_chunk.ps1" (
    del "gpu_chunk.ps1"
    echo [DELETED] gpu_chunk.ps1
)

if exist "gpu_run.ps1" (
    del "gpu_run.ps1"
    echo [DELETED] gpu_run.ps1
)

if exist "test_system.ps1" (
    del "test_system.ps1"
    echo [DELETED] test_system.ps1
)

if exist "scripts\security_audit.py" (
    del "scripts\security_audit.py"
    echo [DELETED] scripts\security_audit.py
)

echo.
echo ========================================
echo  Cleanup Complete!
echo ========================================
echo.
echo The following files remain:
echo.
echo CORE APPLICATION:
echo   - flow_local_dictation.py (MAIN APP)
echo   - first_run_wizard.py
echo   - START_WHISPER.bat (use this to launch)
echo.
echo WHISPER_LOCAL PACKAGE:
echo   - whisper_local\__init__.py
echo   - whisper_local\config.py
echo   - whisper_local\stats.py
echo   - whisper_local\gpu_monitor.py
echo.
echo BUILD TOOLS:
echo   - build_installer.ps1
echo   - create_release_package.ps1
echo.
echo TESTS (optional):
echo   - tests\ directory (run: pytest tests/)
echo.
echo.
echo To launch WhisperLocal, double-click: START_WHISPER.bat
echo.
pause
