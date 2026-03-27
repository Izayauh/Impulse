$ErrorActionPreference = 'Stop'
$exe = 'C:\Users\isaia\AppData\Local\Temp\impulse-live-v104-test-77f5d63e-1356-4711-9067-bd018ff3c43c\app\WhisperLocal.exe'
$p = Start-Process -FilePath $exe -PassThru
Start-Sleep -Seconds 12
$alive = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
Write-Host ('PID=' + $p.Id)
if ($alive) {
  Write-Host 'STATUS=running'
  Stop-Process -Id $p.Id -Force
  Write-Host 'STOPPED=yes'
} else {
  Write-Host 'STATUS=exited'
}
