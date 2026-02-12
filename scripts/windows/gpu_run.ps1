param(
  [string]$Model = "",
  [string]$Input = ""
)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
if (-not $Model) { $Model = Join-Path $root "runtime\\models\\ggml-medium.en.bin" }
if (-not $Input) { $Input = Join-Path $root "output\\audio\\flow_input.wav" }
$bin = Join-Path $root "runtime\\bin\\whisper-cli.exe"
$logPath = Join-Path $root "output\\logs\\gpu_last.log"
$env:GGML_CUDA_ENABLE="1"
$env:GGML_VERBOSE="1"
$env:WHISPER_PRINT_TIMINGS="1"
& $bin -m $Model $Input 2>&1 | Tee-Object $logPath
if ($LASTEXITCODE -ne 0) { Write-Error "CUDA run failed. See $logPath"; exit 1 }
$log = Get-Content $logPath -Raw
if ($log -notmatch 'ggml_cuda_init: found\s+\d+\s+CUDA devices' -or $log -match 'ggml_cuda_init: found\s+0\s+CUDA devices') {
  Write-Error "GPU not used (no CUDA init detected). See $logPath"; exit 1
}
