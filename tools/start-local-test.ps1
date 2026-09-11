$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$logRoot = Join-Path $projectRoot 'logs/local-test'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

docker compose -f (Join-Path $PSScriptRoot 'compose.local-test.yml') up -d --wait --wait-timeout 120
if ($LASTEXITCODE -ne 0) { throw 'Local MySQL/Redis failed to start.' }

$env:APP_ENV = 'development'
$env:MYSQL_HOST = '127.0.0.1'
$env:MYSQL_PORT = '13306'
$env:MYSQL_USER = 'excellent'
$env:MYSQL_PASSWORD = 'excellentlocal2026'
$env:MYSQL_DB = 'excellent_local_test'
$env:REDIS_HOST = '127.0.0.1'
$env:REDIS_PORT = '16379'
$env:REDIS_PASSWORD = ''
$env:REDIS_DB = '0'
$env:CELERY_BROKER_URL = 'redis://127.0.0.1:16379/1'
$env:CELERY_RESULT_BACKEND = 'redis://127.0.0.1:16379/2'
$env:PAYMENT_MOCK_EXTERNAL_PAYMENT = 'true'
$env:ALIPAY_ENABLED = 'false'
$env:WECHAT_PAY_ENABLED = 'false'
$env:TENCENT_COS_ENABLED = 'false'
$env:SMS_ENABLED = 'false'
$env:DYNPNS_ENABLED = 'false'
$env:CORS_ORIGINS = 'http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174'

function Start-LocalService($Name, $Port, $Executable, $Arguments, $Directory) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Host "$Name already has a listener on port $Port; leaving it running."
        return
    }
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $Directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logRoot "$Name.stdout.log") -RedirectStandardError (Join-Path $logRoot "$Name.stderr.log")
    Write-Host "$Name started: PID $($process.Id), port $Port"
}

$pythonExe = (Get-Command python).Source
$nodeExe = (Get-Command node).Source
Start-LocalService 'server' 8000 $pythonExe @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') (Join-Path $projectRoot 'server')
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
$env:VITE_PUBLIC_BASE = '/'
Start-LocalService 'admin-web' 5173 $nodeExe @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort') (Join-Path $projectRoot 'admin-web')
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/'
$env:VITE_APP_ENV = 'local'
$env:VITE_INVITE_WEB_BASE_URL = 'http://127.0.0.1:5174'
Start-LocalService 'mobile-h5' 5174 $nodeExe @('scripts/run-uni.mjs', '--host', '127.0.0.1', '--port', '5174', '--strictPort') (Join-Path $projectRoot 'mobile-uniNew2')
Write-Host "Logs: $logRoot"
