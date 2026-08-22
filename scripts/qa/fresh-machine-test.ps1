# ============================================================================
# Impulse fresh-machine QA
# Run on any Windows PC to test the full stranger install path in one shot:
#   irm https://raw.githubusercontent.com/Izayauh/Impulse/main/scripts/qa/fresh-machine-test.ps1 | iex
# No admin needed (the installer is per-user). Leaves a report at
# %TEMP%\impulse-qa\report.txt to send back if anything fails.
# ============================================================================

$ErrorActionPreference = 'Stop'
# Always test the newest release (prereleases included) so a re-run after a
# fix automatically picks up the new build.
$rel   = @(Invoke-RestMethod 'https://api.github.com/repos/Izayauh/Impulse/releases?per_page=5')[0]
$tag   = $rel.tag_name
$setupAsset = $rel.assets | Where-Object { $_.name -like '*-Setup-*.exe' } | Select-Object -First 1
if (-not $setupAsset) { throw "release $tag has no setup exe asset" }
$setup = $setupAsset.name -replace '\.exe$', ''
$assetNames = @($rel.assets | Where-Object { $_.name -like "$setup*" } | ForEach-Object { $_.name })
$base  = "https://github.com/Izayauh/Impulse/releases/download/$tag"
$work  = Join-Path $env:TEMP 'impulse-qa'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$log   = Join-Path $work 'report.txt'

function Step($msg) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $msg
  Write-Host $line -ForegroundColor Cyan
  Add-Content -Path $log -Value $line
}
function Fail($msg) {
  Step "FAIL: $msg"
  Write-Host "`nReport saved to $log - send its contents back." -ForegroundColor Yellow
  exit 1
}

Step "Impulse fresh-machine QA starting ($tag) on $env:COMPUTERNAME"

# --- 1. Download release assets (curl.exe ships with Windows 10+) -----------
foreach ($name in $assetNames) {
  $dest = Join-Path $work $name
  if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 0)) {
    Step "Already downloaded: $name"
    continue
  }
  Step "Downloading $name ..."
  & curl.exe -L --fail --retry 3 -o $dest "$base/$name"
  if ($LASTEXITCODE -ne 0) { Fail "download of $name failed" }
  Step ("  {0} = {1:N0} MB" -f $name, ((Get-Item $dest).Length / 1MB))
}

# --- 2. Verify installer checksum -------------------------------------------
$expected = ((Get-Content (Join-Path $work "$setup.sha256")) -split '\s+')[0].Trim().ToLower()
$actual   = (Get-FileHash (Join-Path $work "$setup.exe") -Algorithm SHA256).Hash.ToLower()
if ($expected -ne $actual) { Fail "checksum mismatch: expected $expected got $actual" }
Step "Checksum OK ($actual)"

# --- 3. Silent install -------------------------------------------------------
Step "Installing silently (per-user, no admin prompt expected)..."
$p = Start-Process -FilePath (Join-Path $work "$setup.exe") `
  -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
if ($p.ExitCode -ne 0) { Fail "installer exit code $($p.ExitCode)" }

$appDir = @(
  "$env:LOCALAPPDATA\Programs\WhisperLocal",
  "$env:ProgramFiles\WhisperLocal",
  "${env:ProgramFiles(x86)}\WhisperLocal"
) | Where-Object { Test-Path (Join-Path $_ 'WhisperLocal.exe') } | Select-Object -First 1
if (-not $appDir) { Fail "WhisperLocal.exe not found after install" }
Step "Installed at: $appDir"

# --- 4. Get a license key from the public signup API ------------------------
Step "Requesting a license key from the beta signup API..."
try {
  $resp = Invoke-RestMethod -Method Post `
    -Uri 'https://impulse-eight-lake.vercel.app/api/beta-signup' `
    -ContentType 'application/json' `
    -Body (@{ email = "isaiahwashington48+qa-$env:COMPUTERNAME@gmail.com"; source = 'fresh-machine-test' } | ConvertTo-Json)
  $key = $resp.licenseKey
  if (-not $key) { Fail "signup succeeded but returned no licenseKey" }
  Step "License key issued: $key"
} catch {
  Fail "beta-signup request failed: $_"
}

# --- 5. Launch the app -------------------------------------------------------
Step "Launching WhisperLocal for first run..."
Start-Process -FilePath (Join-Path $appDir 'WhisperLocal.exe') -WorkingDirectory $appDir

@"

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
"@ | Tee-Object -Append -FilePath $log
