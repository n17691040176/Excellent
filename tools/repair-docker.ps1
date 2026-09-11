$ErrorActionPreference = 'SilentlyContinue'
$dockerExe = 'D:\software\Docker\Docker Desktop.exe'
$socket = Join-Path $env:LOCALAPPDATA 'Docker\run\sailor-ingest.sock'
$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'Docker Desktop.exe' -or $_.Name -eq 'com.docker.backend.exe' }
foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force }
Start-Sleep -Seconds 3
if (Test-Path -LiteralPath $socket) { Remove-Item -LiteralPath $socket -Force }
if (Test-Path -LiteralPath $dockerExe) { Start-Process -FilePath $dockerExe -WindowStyle Hidden }
for ($i = 0; $i -lt 24; $i++) {
  Start-Sleep -Seconds 5
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { Write-Host 'Docker Engine READY'; exit 0 }
}
Write-Error 'Docker Engine not ready'
exit 1
