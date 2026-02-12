param(
  [string]$Model = "",
  [string]$Input = "",
  [int]$ChunkSec = 25,
  [int]$OverlapSec = 2
)
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
if (-not $Model) { $Model = Join-Path $root "runtime\\models\\ggml-medium.en.bin" }
if (-not $Input) { $Input = Join-Path $root "output\\audio\\flow_input.wav" }
$bin = Join-Path $root "runtime\\bin\\whisper-cli.exe"
$work = Join-Path $root "output\\transcripts\\gpu_chunks"
New-Item -ItemType Directory -Path $work -Force | Out-Null
Set-Location $work
$env:GGML_CUDA_ENABLE="1"; $env:GGML_VERBOSE="1"; $env:WHISPER_PRINT_TIMINGS="1"

# A) split
Remove-Item chunk_*.wav, out.txt -ErrorAction SilentlyContinue
ffmpeg -y -i $Input -f segment -segment_time $ChunkSec -af "asetpts=N/SR/TB,aresample=16000" -segment_overlap $OverlapSec -c:a pcm_s16le "chunk_%03d.wav"

# B) transcribe each
Get-ChildItem . -Filter "chunk_*.wav" | Sort-Object Name | ForEach-Object {
  & $bin -m $Model $_.FullName -otxt -of "$($_.BaseName)" 2>&1 | Tee-Object "$($_.BaseName).log"
  if ($LASTEXITCODE -ne 0) { Write-Error "CUDA failed on $($_.Name). See log."; exit 1 }
  $log = Get-Content "$($_.BaseName).log" -Raw
  if ($log -notmatch 'ggml_cuda_init: found\s+\d+\s+CUDA devices' -or $log -match 'ggml_cuda_init: found\s+0\s+CUDA devices') { Write-Error "GPU not used on $($_.Name). See $($_.BaseName).log"; exit 1 }
  Get-Content "$($_.BaseName).txt" | Add-Content out.txt
}
Write-Host "Done. Combined text in $work\\out.txt"
