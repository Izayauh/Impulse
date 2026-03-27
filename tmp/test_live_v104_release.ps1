$ErrorActionPreference = 'Stop'
$temp = Join-Path $env:TEMP ('impulse-live-v104-test-' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $temp -Force | Out-Null
$assets = @(
  'WhisperLocal-Setup-1.0.4.exe',
  'WhisperLocal-Setup-1.0.4-1.bin',
  'WhisperLocal-Setup-1.0.4-2.bin',
  'WhisperLocal-Setup-1.0.4-3.bin',
  'WhisperLocal-Setup-1.0.4.sha256'
)
$base = 'https://github.com/Izayauh/whisper/releases/download/v1.0.4/'
Write-Host ('TEMP=' + $temp)
foreach ($name in $assets) {
  $url = $base + $name
  $out = Join-Path $temp $name
  Write-Host ('DOWNLOAD=' + $name)
  Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
  Write-Host ('SIZE=' + ((Get-Item $out).Length))
}
$targetDir = Join-Path $temp 'app'
$log = Join-Path $temp 'install.log'
$args = @('/SP-','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR=' + $targetDir),('/LOG=' + $log))
$p = Start-Process -FilePath (Join-Path $temp 'WhisperLocal-Setup-1.0.4.exe') -WorkingDirectory $temp -ArgumentList $args -PassThru
$completed = $p.WaitForExit(180000)
if (-not $completed) {
  Write-Host 'EXIT=timeout'
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
} else {
  Write-Host ('EXIT=' + $p.ExitCode)
}
if (Test-Path $log) {
  Write-Host ('LOG=' + $log)
  Get-Content $log -Tail 100
}
if (Test-Path (Join-Path $targetDir 'WhisperLocal.exe')) {
  Write-Host 'INSTALLED=WhisperLocal.exe'
}
