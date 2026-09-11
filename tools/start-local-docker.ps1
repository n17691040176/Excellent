param([switch]$NoBuild, [switch]$UseRegistryMirror)
$ErrorActionPreference = 'Stop'
$composeFiles = @('-f', (Join-Path $PSScriptRoot 'compose.local-test.yml'), '-f', (Join-Path $PSScriptRoot 'compose.local-app.yml'))
docker compose @composeFiles config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Local Docker configuration is invalid.' }
if ($UseRegistryMirror) {
    foreach ($baseImage in @('python:3.11-slim', 'node:20-alpine', 'nginx:1.27-alpine')) {
        docker pull "mirror.gcr.io/library/$baseImage"
        if ($LASTEXITCODE -ne 0) { throw "Could not pull cached base image $baseImage." }
        docker tag "mirror.gcr.io/library/$baseImage" $baseImage
        if ($LASTEXITCODE -ne 0) { throw "Could not tag local base image $baseImage." }
    }
}
if (-not $NoBuild) {
    docker compose @composeFiles build
    if ($LASTEXITCODE -ne 0) { throw 'Local Docker image build failed.' }
}
docker compose @composeFiles up -d --wait --wait-timeout 180
if ($LASTEXITCODE -ne 0) { throw 'Local Docker startup failed; inspect docker compose logs and check ports 8000/5173/5174.' }
docker compose @composeFiles ps
Write-Host 'Admin: http://127.0.0.1:5173/commission'
Write-Host 'Mobile: http://127.0.0.1:5174/'
Write-Host 'API: http://127.0.0.1:8000/docs'
