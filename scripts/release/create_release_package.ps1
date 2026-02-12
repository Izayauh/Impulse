# WhisperLocal Release Package Creator
# This script creates a single ZIP file containing the multi-part installer
# for easy distribution and download.

$ErrorActionPreference = "Stop"

Write-Host "=" * 60
Write-Host "WhisperLocal Release Package Creator"
Write-Host "=" * 60

# Configuration
$version = "1.0.0-final"
$distDir = "dist"
$outputZip = "$distDir\WhisperLocal-Setup-$version-Complete.zip"

# Check if installer files exist
$installerExe = "$distDir\WhisperLocal-Setup-$version.exe"
if (-not (Test-Path $installerExe)) {
    Write-Host "ERROR: Installer not found: $installerExe" -ForegroundColor Red
    Write-Host "Please build the installer first using: build_installer.ps1" -ForegroundColor Yellow
    exit 1
}

# Find all installer parts
$installerFiles = Get-ChildItem -Path $distDir -Filter "WhisperLocal-Setup-$version*" | 
    Where-Object { $_.Extension -eq ".exe" -or $_.Extension -eq ".bin" } |
    Sort-Object Name

if ($installerFiles.Count -eq 0) {
    Write-Host "ERROR: No installer files found matching pattern: WhisperLocal-Setup-$version*" -ForegroundColor Red
    exit 1
}

Write-Host "`nFound $($installerFiles.Count) installer file(s):" -ForegroundColor Green
foreach ($file in $installerFiles) {
    $sizeGB = [math]::Round($file.Length / 1GB, 2)
    Write-Host "  - $($file.Name) ($sizeGB GB)"
}

# Create installation instructions
$instructions = @"
WhisperLocal Installation Instructions
=======================================

Thank you for downloading WhisperLocal!

INSTALLATION STEPS:
-------------------
1. Extract all files from this ZIP to the same folder
2. You should see these files:
   - WhisperLocal-Setup-$version.exe
   - WhisperLocal-Setup-$version-1.bin
   - WhisperLocal-Setup-$version-2.bin
   - WhisperLocal-Setup-$version-3.bin
   - README.txt (this file)

3. Double-click WhisperLocal-Setup-$version.exe to start the installer
4. The installer will automatically find and use the .bin files
5. Follow the on-screen instructions to complete installation

IMPORTANT NOTES:
----------------
- All files MUST be in the same folder for the installer to work
- Do NOT delete or move the .bin files before installation completes
- The installer is large because it includes AI models for offline use
- No internet connection is required after installation

SYSTEM REQUIREMENTS:
--------------------
- Windows 10 or 11 (64-bit)
- 4 GB RAM minimum (8 GB recommended)
- 5 GB free disk space
- NVIDIA GPU recommended for faster transcription (optional)

TROUBLESHOOTING:
----------------
If you see "Setup needs the next disk" error:
- Ensure all files are extracted from the ZIP
- Make sure all .bin files are in the same folder as the .exe
- Try running the installer as Administrator

For support and updates:
https://github.com/Izayauh/whisper

Privacy: WhisperLocal runs 100% offline. No data is sent to the cloud.
"@

$instructionsFile = "$env:TEMP\WhisperLocal-README.txt"
$instructions | Out-File -FilePath $instructionsFile -Encoding UTF8

# Remove old ZIP if it exists
if (Test-Path $outputZip) {
    Write-Host "`nRemoving old package: $outputZip" -ForegroundColor Yellow
    Remove-Item $outputZip -Force
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
    Write-Host "`nUsers should download this single ZIP file and extract all contents before running the installer." -ForegroundColor Cyan
} catch {
    Write-Host "`nERROR: Failed to create ZIP package" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    # Clean up temp file
    if (Test-Path $instructionsFile) {
        Remove-Item $instructionsFile -Force
    }
}

# Generate SHA256 checksum
Write-Host "`nGenerating checksum..." -ForegroundColor Cyan
$hash = Get-FileHash -Path $outputZip -Algorithm SHA256
$checksumFile = "$distDir\WhisperLocal-Setup-$version-Complete.zip.sha256"
"$($hash.Hash)  $(Split-Path $outputZip -Leaf)" | Out-File -FilePath $checksumFile -Encoding ASCII
Write-Host "Checksum saved to: $checksumFile" -ForegroundColor Green

Write-Host "`n" + ("=" * 60)
Write-Host "DONE! Ready for distribution." -ForegroundColor Green
Write-Host ("=" * 60)

