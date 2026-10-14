# Deploy main API to CloudBase CloudRun (build context = repo root).
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

if (-not (Get-Command tcb -ErrorAction SilentlyContinue)) {
    throw 'tcb CLI not found. Install: npm install -g @cloudbase/cli'
}

Copy-Item -Force (Join-Path $PSScriptRoot 'Dockerfile') (Join-Path $Root 'Dockerfile')
$Tcb = @('tcb')
if ($env:TCB_ENV_ID) {
    $Tcb = @('tcb', '-e', $env:TCB_ENV_ID)
}

try {
    Write-Host "Deploying ai-assistant-api from $Root (port 8080)..."
    & @Tcb cloudrun deploy -s ai-assistant-api --source . --port 8080 @args
}
finally {
    Remove-Item -Force (Join-Path $Root 'Dockerfile') -ErrorAction SilentlyContinue
}
