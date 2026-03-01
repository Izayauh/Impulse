# WhisperLocal Release Package Creator
# Creates a single ZIP package containing installer EXE + disk spanning BIN parts.

param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$distDir = Join-Path $ProjectRoot "dist"

Write-Host "=" * 60
Write-Host "WhisperLocal Release Package Creator"
Write-Host "=" * 60

if (-not (Test-Path $distDir)) {
    Write-Host "ERROR: dist directory not found: $distDir" -ForegroundColor Red
    exit 1
}

# Resolve installer EXE either by explicit version or latest build
$installerExe = $null
if ($Version -and $Version.Trim().Length -gt 0) {
    $candidate = Join-Path $distDir ("WhisperLocal-Setup-" + $Version + ".exe")
    if (Test-Path $candidate) {
        $installerExe = Get-Item $candidate
    } else {
        Write-Host "ERROR: Installer not found: $candidate" -ForegroundColor Red
        Write-Host "Tip: omit -Version to auto-select latest installer." -ForegroundColor Yellow
        exit 1
    }
} else {
    $installerExe = Get-ChildItem -Path $distDir -Filter "WhisperLocal-Setup-*.exe" |
        Where-Object { $_.Name -notmatch "-Complete\.zip" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $installerExe) {
        Write-Host "ERROR: No installer exe found in $distDir" -ForegroundColor Red
        Write-Host "Please build installer first using scripts\release\build_installer.ps1" -ForegroundColor Yellow
        exit 1
    }
}

$baseName = $installerExe.BaseName
$version = $baseName -replace '^WhisperLocal-Setup-', ''

# Find all installer parts for this exact build
$installerFiles = Get-ChildItem -Path $distDir |
    Where-Object {
        $_.BaseName -like "$baseName*" -and ($_.Extension -eq ".exe" -or $_.Extension -eq ".bin")
    } |
    Sort-Object Name

if ($installerFiles.Count -eq 0) {
    Write-Host "ERROR: No installer files found for base: $baseName" -ForegroundColor Red
    exit 1
}

Write-Host "`nUsing installer build: $baseName" -ForegroundColor Cyan
Write-Host "Found $($installerFiles.Count) installer file(s):" -ForegroundColor Green
foreach ($file in $installerFiles) {
    $sizeGB = [math]::Round($file.Length / 1GB, 2)
    Write-Host "  - $($file.Name) ($sizeGB GB)"
}

$outputZip = Join-Path $distDir ($baseName + "-Complete.zip")
$checksumFile = $outputZip + ".sha256"

# Build README content dynamically
$readmeLines = @(
    "WhisperLocal Installation Instructions",
    "=======================================",
    "",
    "Thank you for downloading WhisperLocal!",
    "",
    "INSTALLATION STEPS:",
    "-------------------",
    "1. Extract all files from this ZIP to the same folder",
    "2. You should see these files:",
    "   - $($installerExe.Name)"
)

$binFiles = $installerFiles | Where-Object { $_.Extension -eq ".bin" }
foreach ($bin in $binFiles) {
    $readmeLines += "   - $($bin.Name)"
}

$readmeLines += @(
    "   - README.txt (this file)",
    "",
    "3. Double-click $($installerExe.Name) to start the installer",
    "4. The installer will automatically find and use the .bin files",
    "5. Follow the on-screen instructions to complete installation",
    "",
    "IMPORTANT NOTES:",
    "----------------",
    "- All files MUST be in the same folder for the installer to work",
    "- Do NOT delete or move the .bin files before installation completes",
    "- Installer size is large because it includes local AI runtime dependencies",
    "",
    "SYSTEM REQUIREMENTS:",
    "--------------------",
    "- Windows 10 or 11 (64-bit)",
    "- 4 GB RAM minimum (8 GB recommended)",
    "- 5 GB free disk space",
    "- NVIDIA GPU recommended for faster transcription (optional)",
    "",
    "For support and updates:",
    "https://github.com/Izayauh/whisper"
)

$instructionsFile = Join-Path $env:TEMP "WhisperLocal-README.txt"
$readmeLines -join "`r`n" | Out-File -FilePath $instructionsFile -Encoding UTF8

# Remove old outputs
if (Test-Path $outputZip) {
    Write-Host "`nRemoving old package: $outputZip" -ForegroundColor Yellow
    Remove-Item $outputZip -Force
}
if (Test-Path $checksumFile) {
    Remove-Item $checksumFile -Force
}

# Create ZIP package
Write-Host "`nCreating release package..." -ForegroundColor Cyan
try {
    $filesToZip = @($instructionsFile) + $installerFiles.FullName
    Compress-Archive -Path $filesToZip -DestinationPath $outputZip -CompressionLevel Optimal

    $zipSize = [math]::Round((Get-Item $outputZip).Length / 1GB, 2)
    Write-Host "`n✓ SUCCESS!" -ForegroundColor Green
    Write-Host "Release package created: $outputZip" -ForegroundColor Green
    Write-Host "Package size: $zipSize GB" -ForegroundColor Green
} catch {
    Write-Host "`nERROR: Failed to create ZIP package" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    if (Test-Path $instructionsFile) {
        Remove-Item $instructionsFile -Force
    }
}

# Generate SHA256 checksum
Write-Host "`nGenerating checksum..." -ForegroundColor Cyan
$hash = Get-FileHash -Path $outputZip -Algorithm SHA256
"$($hash.Hash)  $(Split-Path $outputZip -Leaf)" | Out-File -FilePath $checksumFile -Encoding ASCII
Write-Host "Checksum saved to: $checksumFile" -ForegroundColor Green

Write-Host "`n" + ("=" * 60)
Write-Host "DONE! Ready for distribution." -ForegroundColor Green
Write-Host ("=" * 60)
