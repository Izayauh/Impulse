# ============================================================================
# Impulse fresh-machine QA
# Run on any Windows PC to test the full stranger install path in one shot:
#   irm https://raw.githubusercontent.com/Izayauh/Impulse/main/scripts/qa/fresh-machine-test.ps1 | iex
# No admin needed (the installer is per-user). Never closes your window;
# leaves a report at %TEMP%\impulse-qa\report.txt to send back if anything
# fails.
# ============================================================================

$ErrorActionPreference = 'Stop'
$script:failed = $false

# Windows PowerShell 5.1 defaults to old TLS; GitHub requires TLS 1.2+.
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}

$work = Join-Path $env:TEMP 'impulse-qa'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$log  = Join-Path $work 'report.txt'

function Step($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
  Write-Host $line -ForegroundColor Cyan
  Add-Content -Path $log -Value $line -Encoding UTF8
}

try {
  # --- 0. Find the newest release (prereleases included) --------------------
  $rel = $null
  try {
    # Pipe to Select-Object: Windows PowerShell 5.1 returns the whole JSON
    # array as ONE object, so @(...)[0] yields the array, not the first item.
    $rel = Invoke-RestMethod 'https://api.github.com/repos/Izayauh/Impulse/releases?per_page=5' `
             -Headers @{ 'User-Agent' = 'impulse-qa' } -TimeoutSec 30 | Select-Object -First 1
  } catch {
    Step "Releases API failed ($($_.Exception.Message)); falling back to /releases/latest"
    $rel = Invoke-RestMethod 'https://api.github.com/repos/Izayauh/Impulse/releases/latest' `
           -Headers @{ 'User-Agent' = 'impulse-qa' } -TimeoutSec 30
  }
  $tag = $rel.tag_name
  $setupAsset = $rel.assets | Where-Object { $_.name -like '*-Setup-*.exe' } | Select-Object -First 1
  if (-not $setupAsset) { throw "release $tag has no setup exe asset (build may still be uploading - try again in a few minutes)" }
  $setup = $setupAsset.name -replace '\.exe$', ''
  $assetNames = @($rel.assets | Where-Object { $_.name -like "$setup*" } | ForEach-Object { $_.name })
  $base = "https://github.com/Izayauh/Impulse/releases/download/$tag"

  Step "Impulse fresh-machine QA starting ($tag) on $env:COMPUTERNAME"

  # --- 1. Download release assets (curl.exe ships with Windows 10+) ---------
  foreach ($name in $assetNames) {
    $dest = Join-Path $work $name
    if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 0)) {
      Step "Already downloaded: $name"
      continue
    }
    Step "Downloading $name ..."
    & curl.exe -L --fail --retry 3 -o $dest "$base/$name"
    if ($LASTEXITCODE -ne 0) { throw "download of $name failed (curl exit $LASTEXITCODE)" }
    Step ("  {0} = {1:N0} MB" -f $name, ((Get-Item $dest).Length / 1MB))
  }

  # --- 2. Verify installer checksum ------------------------------------------
  $shaFile = Join-Path $work "$setup.sha256"
  if (Test-Path $shaFile) {
    $expected = ((Get-Content $shaFile) -split '\s+')[0].Trim().ToLower()
    $actual   = (Get-FileHash (Join-Path $work "$setup.exe") -Algorithm SHA256).Hash.ToLower()
    if ($expected -ne $actual) { throw "checksum mismatch: expected $expected got $actual" }
    Step "Checksum OK ($actual)"
  } else {
    Step "No sha256 asset; skipping checksum"
  }

  # --- 3. Silent install ------------------------------------------------------
  # A previous test run may have left the app running; the installer cannot
  # overwrite files that are in use (exit code 5).
  $running = Get-Process -Name 'Impulse' -ErrorAction SilentlyContinue
  if ($running) {
    Step "Stopping running Impulse instance from a previous test..."
    $running | Stop-Process -Force
    Start-Sleep -Seconds 2
  }

  Step "Installing silently (per-user, no admin prompt expected)..."
  $p = Start-Process -FilePath (Join-Path $work "$setup.exe") `
    -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/FORCECLOSEAPPLICATIONS' -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "installer exit code $($p.ExitCode)" }

  $appDir = @(
    "$env:LOCALAPPDATA\Programs\Impulse",
    "$env:ProgramFiles\Impulse",
    "${env:ProgramFiles(x86)}\Impulse"
  ) | Where-Object { Test-Path (Join-Path $_ 'Impulse.exe') } | Select-Object -First 1
  if (-not $appDir) { throw "Impulse.exe not found after install" }
  Step "Installed at: $appDir"

  # --- 4. Get a license key from the public signup API ------------------------
  Step "Requesting a license key from the beta signup API..."
  $resp = Invoke-RestMethod -Method Post `
    -Uri 'https://impulse-eight-lake.vercel.app/api/beta-signup' `
    -ContentType 'application/json' -TimeoutSec 30 `
    -Body (@{ email = "qa+$env:COMPUTERNAME@impulsedictation.com"; source = 'fresh-machine-test' } | ConvertTo-Json)
  $key = $resp.licenseKey
  if (-not $key) { throw "signup succeeded but returned no licenseKey" }
  Step "License key issued: $key"

  # --- 4b. Ensure the WebView2 runtime (dashboard/activation needs it) --------
  $wv2 = $false
  foreach ($hive in 'HKLM:\SOFTWARE\WOW6432Node', 'HKCU:\SOFTWARE') {
    try {
      $pv = (Get-ItemProperty "$hive\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -ErrorAction Stop).pv
      if ($pv -and $pv -ne '0.0.0.0') { $wv2 = $true; break }
    } catch {}
  }
  if (-not $wv2) {
    Step "WebView2 runtime missing - installing (approve the prompt if one appears)..."
    $wv2exe = Join-Path $work 'MicrosoftEdgeWebview2Setup.exe'
    & curl.exe -L --fail --retry 3 -o $wv2exe 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'
    if ($LASTEXITCODE -ne 0) { throw "WebView2 bootstrapper download failed" }
    $wp = Start-Process -FilePath $wv2exe -ArgumentList '/install' -Wait -PassThru
    Step "WebView2 installer finished (exit $($wp.ExitCode))"
  } else {
    Step "WebView2 runtime present"
  }

  # --- 5. Launch the app -------------------------------------------------------
  Step "Launching Impulse for first run..."
  Start-Process -FilePath (Join-Path $appDir 'Impulse.exe') -WorkingDirectory $appDir

  $checklist = @"

============================= YOUR 60-SECOND PART =============================
 1. If a first-run wizard appears: pick your microphone, click through it.
 2. When asked for a license key, paste:   $key
 3. First transcription downloads the AI model (~1.5 GB) - give it time on
    slower internet. The app should stay responsive while it downloads.
 4. Press  WIN+CTRL  and speak a sentence. It should appear as typed text.
 5. Open the dashboard from the tray icon - does it look right?

 If ANYTHING fails or looks broken, send back the contents of:
   $log
===============================================================================
"@
  Write-Host $checklist -ForegroundColor Green
  Add-Content -Path $log -Value $checklist -Encoding UTF8

} catch {
  $script:failed = $true
  $err = "FAIL: $($_.Exception.Message)"
  Write-Host $err -ForegroundColor Red
  Add-Content -Path $log -Value $err -Encoding UTF8
  Write-Host "Report saved to $log - send its contents back." -ForegroundColor Yellow
}

# Keep the window open no matter what so the key/checklist/error stays visible.
Read-Host "`nDone. Press Enter to close this window"
