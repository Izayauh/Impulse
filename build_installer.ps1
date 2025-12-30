# ============================================================================
# WhisperLocal Build Script
# Builds standalone installer from Python source
# ============================================================================
#
# Prerequisites:
#   1. Python 3.8+ with pip
#   2. PyInstaller: pip install pyinstaller
#   3. Inno Setup: https://jrsoftware.org/isdl.php
#   4. (Optional) UPX for compression: https://upx.github.io/
#
# Usage:
#   .\build_installer.ps1
#   .\build_installer.ps1 -SkipPyInstaller    # Only run Inno Setup
#   .\build_installer.ps1 -SkipInnoSetup      # Only run PyInstaller
#   .\build_installer.ps1 -Clean              # Clean build (remove previous)
#
# ============================================================================

param(
    [switch]$SkipPyInstaller,
    [switch]$SkipInnoSetup,
    [switch]$Clean,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Configuration
# ============================================================================
$AppName = "WhisperLocal"
$AppVersion = "1.0.0"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildDir = Join-Path $ScriptDir "build_output"
$DistDir = Join-Path $ScriptDir "dist"
$SpecFile = Join-Path $ScriptDir "build_config.spec"
$IssFile = Join-Path $ScriptDir "installer.iss"

# Inno Setup paths (common installation locations)
$InnoSetupPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
)

# ============================================================================
# Helper Functions
# ============================================================================
function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host " $Message" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[*] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

function Test-Command {
    param([string]$Command)
    try {
        if (Get-Command $Command -ErrorAction SilentlyContinue) {
            return $true
        }
    } catch {}
    return $false
}

function Get-InnoSetupPath {
    foreach ($path in $InnoSetupPaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

function Get-FileHash256 {
    param([string]$FilePath)
    $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
    return $hash.Hash.ToLower()
}

# ============================================================================
# Prerequisite Checks
# ============================================================================
function Test-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    $allGood = $true
    
    # Check Python
    if (Test-Command "python") {
        $pyVersion = python --version 2>&1
        Write-Success "Python: $pyVersion"
    } else {
        Write-Error "Python not found in PATH"
        $allGood = $false
    }
    
    # Check PyInstaller
    try {
        $piVersion = python -c "import PyInstaller; print(PyInstaller.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "PyInstaller: $piVersion"
        } else {
            Write-Error "PyInstaller not installed. Run: pip install pyinstaller"
            $allGood = $false
        }
    } catch {
        Write-Error "PyInstaller not installed. Run: pip install pyinstaller"
        $allGood = $false
    }
    
    # Check Inno Setup
    $innoPath = Get-InnoSetupPath
    if ($innoPath) {
        Write-Success "Inno Setup: $innoPath"
    } else {
        if (-not $SkipInnoSetup) {
            Write-Error "Inno Setup not found. Download from https://jrsoftware.org/isdl.php"
            $allGood = $false
        } else {
            Write-Info "Inno Setup not found (skipped)"
        }
    }
    
    # Check spec file
    if (Test-Path $SpecFile) {
        Write-Success "Spec file: $SpecFile"
    } else {
        Write-Error "Spec file not found: $SpecFile"
        $allGood = $false
    }
    
    # Check required files
    $requiredFiles = @(
        "flow_local_dictation.py",
        "first_run_wizard.py",
        "whisper-cli.exe",
        "Whisper.ico"
    )
    
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $ScriptDir $file
        if (Test-Path $filePath) {
            Write-Success "Found: $file"
        } else {
            Write-Error "Missing: $file"
            $allGood = $false
        }
    }
    
    # Check models
    $modelsDir = Join-Path $ScriptDir "models"
    $models = @("ggml-base.en.bin", "ggml-medium.en.bin", "ggml-large-v3.bin")
    $modelsFound = 0
    foreach ($model in $models) {
        $modelPath = Join-Path $modelsDir $model
        if (Test-Path $modelPath) {
            $size = (Get-Item $modelPath).Length / 1MB
            Write-Success "Model: $model ({0:N0} MB)" -f $size
            $modelsFound++
        } else {
            Write-Info "Model not found: $model (optional)"
        }
    }
    
    if ($modelsFound -eq 0) {
        Write-Error "No AI models found in models\ directory"
        $allGood = $false
    }
    
    # Check DLLs
    $dlls = @("ggml-base.dll", "ggml-cpu.dll", "ggml-cuda.dll", "ggml.dll", "whisper.dll")
    foreach ($dll in $dlls) {
        $dllPath = Join-Path $ScriptDir $dll
        if (Test-Path $dllPath) {
            Write-Success "DLL: $dll"
        } else {
            Write-Info "DLL not found: $dll (may be optional)"
        }
    }
    
    return $allGood
}

# ============================================================================
# Clean Build
# ============================================================================
function Invoke-Clean {
    Write-Header "Cleaning Previous Build"
    
    $foldersToClean = @(
        (Join-Path $ScriptDir "build"),
        (Join-Path $ScriptDir "dist"),
        $BuildDir
    )
    
    foreach ($folder in $foldersToClean) {
        if (Test-Path $folder) {
            Write-Step "Removing: $folder"
            Remove-Item -Path $folder -Recurse -Force
            Write-Success "Removed: $folder"
        }
    }
    
    # Clean .pyc files
    Get-ChildItem -Path $ScriptDir -Filter "*.pyc" -Recurse | Remove-Item -Force
    Get-ChildItem -Path $ScriptDir -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force
    
    Write-Success "Clean complete"
}

# ============================================================================
# PyInstaller Build
# ============================================================================
function Invoke-PyInstallerBuild {
    Write-Header "Building with PyInstaller"
    
    Set-Location $ScriptDir
    
    Write-Step "Running PyInstaller..."
    Write-Info "This may take several minutes for the first build..."
    
    $pyInstallerArgs = @(
        "--clean",
        "--noconfirm",
        $SpecFile
    )
    
    if ($Verbose) {
        $pyInstallerArgs += "--log-level=DEBUG"
    }
    
    $process = Start-Process -FilePath "python" -ArgumentList (@("-m", "PyInstaller") + $pyInstallerArgs) -NoNewWindow -Wait -PassThru
    
    if ($process.ExitCode -ne 0) {
        Write-Error "PyInstaller build failed with exit code $($process.ExitCode)"
        return $false
    }
    
    # Verify output
    $exePath = Join-Path $DistDir "$AppName\$AppName.exe"
    if (Test-Path $exePath) {
        $exeSize = (Get-Item $exePath).Length / 1MB
        Write-Success "Built: $exePath ({0:N1} MB)" -f $exeSize
    } else {
        Write-Error "Expected output not found: $exePath"
        return $false
    }
    
    # Calculate total distribution size
    $distFolder = Join-Path $DistDir $AppName
    $totalSize = (Get-ChildItem -Path $distFolder -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Success "Total distribution size: {0:N2} GB" -f $totalSize
    
    return $true
}

# ============================================================================
# Inno Setup Build
# ============================================================================
function Invoke-InnoSetupBuild {
    Write-Header "Building Installer with Inno Setup"
    
    $innoPath = Get-InnoSetupPath
    if (-not $innoPath) {
        Write-Error "Inno Setup not found"
        return $false
    }
    
    if (-not (Test-Path $IssFile)) {
        Write-Error "Installer script not found: $IssFile"
        return $false
    }
    
    Write-Step "Running Inno Setup Compiler..."
    
    $process = Start-Process -FilePath $innoPath -ArgumentList @(
        "/Q",  # Quiet mode
        $IssFile
    ) -NoNewWindow -Wait -PassThru
    
    if ($process.ExitCode -ne 0) {
        Write-Error "Inno Setup build failed with exit code $($process.ExitCode)"
        return $false
    }
    
    # Find the output installer
    $installerPattern = Join-Path $DistDir "$AppName-Setup-*.exe"
    $installer = Get-ChildItem -Path $installerPattern | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    if ($installer) {
        $installerSize = $installer.Length / 1GB
        $installerHash = Get-FileHash256 $installer.FullName
        
        Write-Success "Installer created: $($installer.Name)"
        Write-Success "Size: {0:N2} GB" -f $installerSize
        Write-Success "SHA256: $installerHash"
        
        # Save hash to file
        $hashFile = Join-Path $DistDir "$($installer.BaseName).sha256"
        "$installerHash *$($installer.Name)" | Out-File -FilePath $hashFile -Encoding ascii
        Write-Success "Hash saved to: $hashFile"
    } else {
        Write-Error "Installer not found in $DistDir"
        return $false
    }
    
    return $true
}

# ============================================================================
# Main Build Process
# ============================================================================
function Invoke-Build {
    $startTime = Get-Date
    
    Write-Header "$AppName Build Script v$AppVersion"
    Write-Info "Build started at: $startTime"
    Write-Info "Working directory: $ScriptDir"
    
    # Clean if requested
    if ($Clean) {
        Invoke-Clean
    }
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Write-Error "Prerequisites check failed. Please install missing dependencies."
        exit 1
    }
    
    # PyInstaller build
    if (-not $SkipPyInstaller) {
        if (-not (Invoke-PyInstallerBuild)) {
            Write-Error "PyInstaller build failed"
            exit 1
        }
    } else {
        Write-Info "Skipping PyInstaller build (--SkipPyInstaller)"
    }
    
    # Inno Setup build
    if (-not $SkipInnoSetup) {
        if (-not (Invoke-InnoSetupBuild)) {
            Write-Error "Inno Setup build failed"
            exit 1
        }
    } else {
        Write-Info "Skipping Inno Setup build (--SkipInnoSetup)"
    }
    
    # Summary
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Header "Build Complete!"
    Write-Success "Duration: {0:N0} minutes {1:N0} seconds" -f $duration.TotalMinutes, ($duration.Seconds)
    
    if (-not $SkipInnoSetup) {
        $installerPattern = Join-Path $DistDir "$AppName-Setup-*.exe"
        $installer = Get-ChildItem -Path $installerPattern | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($installer) {
            Write-Host ""
            Write-Host "  Installer ready for distribution:" -ForegroundColor Green
            Write-Host "  $($installer.FullName)" -ForegroundColor White
            Write-Host ""
        }
    }
}

# ============================================================================
# Run Build
# ============================================================================
try {
    Invoke-Build
    Write-Output "__CURSOR_DONE__"
} catch {
    Write-Error "Build failed: $_"
    Write-Output "__CURSOR_DONE__"
    exit 1
}

