# ============================================================================
# Impulse Build Script
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
    [switch]$SkipBootstrap,
    [switch]$Clean,
    [switch]$Verbose,
    [string]$BootstrapBaseUrl = $env:WHISPER_BOOTSTRAP_BASE_URL
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Configuration
# ============================================================================
$AppName = "Impulse"
$AppVersion = "1.0.0-beta.1"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\\..")
$BuildDir = Join-Path $ProjectRoot "build_output"
$DistDir = Join-Path $ProjectRoot "dist"
$SpecFile = Join-Path $ScriptDir "build_config.spec"
$IssFile = Join-Path $ScriptDir "installer.iss"
$BootstrapIssFile = Join-Path $ScriptDir "bootstrap_installer.iss"
$BootstrapManifestScript = Join-Path $ScriptDir "generate_bootstrap_payload.ps1"
$MinimumFreeSpaceBytes = 10GB

function Get-AppVersion {
    $configPath = Join-Path $ProjectRoot "src\whisper_local\config.py"
    if (Test-Path $configPath) {
        $match = Select-String -Path $configPath -Pattern 'APP_VERSION\s*=\s*"([^"]+)"' -AllMatches | Select-Object -First 1
        if ($match -and $match.Matches.Count -gt 0) {
            return $match.Matches[0].Groups[1].Value
        }
    }
    return $AppVersion
}

$AppVersion = Get-AppVersion

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
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
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

function Sync-InstallerVersion {
    $installerScripts = @($IssFile, $BootstrapIssFile)
    foreach ($scriptPath in $installerScripts) {
        if (-not (Test-Path $scriptPath)) {
            continue
        }

        $content = Get-Content $scriptPath -Raw
        $updated = $content -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$AppVersion`""
        if ($updated -ne $content) {
            Set-Content -Path $scriptPath -Value $updated -Encoding ASCII
        }
    }
}

function Test-FreeSpace {
    param(
        [string]$Path,
        [Int64]$RequiredBytes
    )

    $resolved = Resolve-Path $Path
    $item = Get-Item $resolved
    $root = [System.IO.Path]::GetPathRoot($item.FullName)
    $drive = Get-PSDrive -Name $root.TrimEnd('\').TrimEnd(':') -ErrorAction Stop
    return $drive.Free -ge $RequiredBytes
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

    # Check required Python packages used by the packaged app.
    try {
        python -c "import requests, packaging" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Core updater deps: requests, packaging"
        } else {
            Write-Error "Missing runtime deps. Run: pip install -r requirements.txt"
            $allGood = $false
        }
    } catch {
        Write-Error "Missing runtime deps. Run: pip install -r requirements.txt"
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
        "main.py",
        "src\\whisper_local\\ui\\first_run_wizard.py",
        "runtime\\bin\\whisper-cli.exe",
        "src\\whisper_local\\Whisper.ico"
    )
    
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $ProjectRoot $file
        if (Test-Path $filePath) {
            Write-Success "Found: $file"
        } else {
            Write-Error "Missing: $file"
            $allGood = $false
        }
    }
    
    # Check models
    $modelsDir = Join-Path $ProjectRoot "runtime\\models"
    $models = @("ggml-base.en.bin", "ggml-medium.en.bin", "ggml-large-v3.bin")
    $modelsFound = 0
    foreach ($model in $models) {
        $modelPath = Join-Path $modelsDir $model
        if (Test-Path $modelPath) {
            $size = (Get-Item $modelPath).Length / 1MB
            Write-Success (("Model: {0} ({1:N0} MB)" -f $model, $size))
            $modelsFound++
        } else {
            Write-Info "Model not found: $model (optional)"
        }
    }
    
    if ($modelsFound -eq 0) {
        Write-Error "No AI models found in runtime\\models directory"
        $allGood = $false
    }

    if (Test-FreeSpace -Path $ProjectRoot -RequiredBytes $MinimumFreeSpaceBytes) {
        $freeGb = [math]::Round(((Get-PSDrive -Name ([System.IO.Path]::GetPathRoot($ProjectRoot.Path).TrimEnd('\').TrimEnd(':'))).Free / 1GB), 2)
        Write-Success "Free disk space check passed ($freeGb GB available)"
    } else {
        $driveName = [System.IO.Path]::GetPathRoot($ProjectRoot.Path).TrimEnd('\').TrimEnd(':')
        $drive = Get-PSDrive -Name $driveName
        $freeGb = [math]::Round($drive.Free / 1GB, 2)
        $requiredGb = [math]::Round($MinimumFreeSpaceBytes / 1GB, 2)
        Write-Error "Insufficient free disk space on $driveName drive ($freeGb GB free, need at least $requiredGb GB)"
        $allGood = $false
    }
    
    # Check DLLs
    $dlls = @("ggml-base.dll", "ggml-cpu.dll", "ggml-cuda.dll", "ggml.dll", "whisper.dll")
    foreach ($dll in $dlls) {
        $dllPath = Join-Path $ProjectRoot ("runtime\\bin\\" + $dll)
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
    
    Set-Location $ProjectRoot
    
    Write-Step "Running PyInstaller..."
    Write-Info "This may take several minutes for the first build..."
    
    $pyInstallerArgs = @(
        "--clean",
        "--noconfirm",
        "--distpath",
        $DistDir,
        "--workpath",
        (Join-Path $ProjectRoot "build"),
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
        Write-Success (("Built: {0} ({1:N1} MB)" -f $exePath, $exeSize))
    } else {
        Write-Error "Expected output not found: $exePath"
        return $false
    }
    
    # Calculate total distribution size
    $distFolder = Join-Path $DistDir $AppName
    $totalSize = (Get-ChildItem -Path $distFolder -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Success (("Total distribution size: {0:N2} GB" -f $totalSize))
    
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
        Write-Success (("Size: {0:N2} GB" -f $installerSize))
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

function Invoke-BootstrapPayloadGeneration {
    if ([string]::IsNullOrWhiteSpace($BootstrapBaseUrl)) {
        Write-Info "Bootstrap installer skipped (set WHISPER_BOOTSTRAP_BASE_URL to enable it)"
        return $false
    }

    if (-not (Test-Path $BootstrapManifestScript)) {
        Write-Error "Bootstrap manifest generator not found: $BootstrapManifestScript"
        return $false
    }

    Write-Header "Generating Bootstrap Payload Manifest"
    Write-Step "Preparing hosted payload manifest..."

    $process = Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $BootstrapManifestScript,
        "-BaseUrl", $BootstrapBaseUrl,
        "-Version", $AppVersion
    ) -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Error "Bootstrap payload manifest generation failed with exit code $($process.ExitCode)"
        return $false
    }

    return $true
}

function Invoke-BootstrapInstallerBuild {
    Write-Header "Building Bootstrap Installer with Inno Setup"

    $innoPath = Get-InnoSetupPath
    if (-not $innoPath) {
        Write-Error "Inno Setup not found"
        return $false
    }

    if (-not (Test-Path $BootstrapIssFile)) {
        Write-Error "Bootstrap installer script not found: $BootstrapIssFile"
        return $false
    }

    Write-Step "Running Inno Setup Compiler for bootstrap installer..."

    $process = Start-Process -FilePath $innoPath -ArgumentList @(
        "/Q",
        $BootstrapIssFile
    ) -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        Write-Error "Bootstrap installer build failed with exit code $($process.ExitCode)"
        return $false
    }

    $installerPattern = Join-Path $DistDir "$AppName-Bootstrap-Setup-*.exe"
    $installer = Get-ChildItem -Path $installerPattern | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if ($installer) {
        $installerSize = $installer.Length / 1MB
        $installerHash = Get-FileHash256 $installer.FullName
        $hashFile = Join-Path $DistDir "$($installer.BaseName).sha256"
        "$installerHash *$($installer.Name)" | Out-File -FilePath $hashFile -Encoding ascii

        Write-Success "Bootstrap installer created: $($installer.Name)"
        Write-Success (("Size: {0:N1} MB" -f $installerSize))
        Write-Success "SHA256: $installerHash"
        Write-Success "Hash saved to: $hashFile"
        return $true
    }

    Write-Error "Bootstrap installer not found in $DistDir"
    return $false
}

# ============================================================================
# Main Build Process
# ============================================================================
function Invoke-Build {
    $startTime = Get-Date
    
    Write-Header "$AppName Build Script v$AppVersion"
    Write-Info "Build started at: $startTime"
    Write-Info "Working directory: $ScriptDir"
    Sync-InstallerVersion
    
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

    if (-not $SkipInnoSetup -and -not $SkipBootstrap) {
        if (Invoke-BootstrapPayloadGeneration) {
            if (-not (Invoke-BootstrapInstallerBuild)) {
                Write-Error "Bootstrap installer build failed"
                exit 1
            }
        }
    } elseif ($SkipBootstrap) {
        Write-Info "Skipping bootstrap installer build (--SkipBootstrap)"
    }
    
    # Summary
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Header "Build Complete!"
    Write-Success (("Duration: {0:N0} minutes {1:N0} seconds" -f $duration.TotalMinutes, ($duration.Seconds)))
    
    if (-not $SkipInnoSetup) {
        $installerPattern = Join-Path $DistDir "$AppName-Setup-*.exe"
        $installer = Get-ChildItem -Path $installerPattern | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($installer) {
            Write-Host ""
            Write-Host "  Installer ready for distribution:" -ForegroundColor Green
            Write-Host "  $($installer.FullName)" -ForegroundColor White
            Write-Host ""
        }

        $bootstrapPattern = Join-Path $DistDir "$AppName-Bootstrap-Setup-*.exe"
        $bootstrapInstaller = Get-ChildItem -Path $bootstrapPattern -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($bootstrapInstaller) {
            Write-Host "  Bootstrap installer ready for distribution:" -ForegroundColor Green
            Write-Host "  $($bootstrapInstaller.FullName)" -ForegroundColor White
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
