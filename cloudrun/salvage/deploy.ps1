# Deploy salvage engine to CloudBase CloudRun (build context = ming-salvage-sim-main/).
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Salvage = Join-Path $Root 'ming-salvage-sim-main'

if (-not (Get-Command tcb -ErrorAction SilentlyContinue)) {
    throw 'tcb CLI not found. Install: npm install -g @cloudbase/cli'
}

$Dockerfile = Join-Path $PSScriptRoot 'Dockerfile'
$Requirements = Join-Path $PSScriptRoot 'requirements.txt'
$SalvageDockerfile = Join-Path $Salvage 'Dockerfile'
$SalvageRequirements = Join-Path $Salvage 'requirements.txt'
$SalvageRequirementsBak = Join-Path $Salvage 'requirements.txt.bak'

$SalvageDockerignore = Join-Path $Salvage '.dockerignore'
$SalvageDockerignoreBak = Join-Path $Salvage '.dockerignore.bak'

Copy-Item -Force $Dockerfile $SalvageDockerfile
if (Test-Path $SalvageDockerignore) {
    Copy-Item -Force $SalvageDockerignore $SalvageDockerignoreBak
}
Copy-Item -Force (Join-Path $PSScriptRoot '.dockerignore') $SalvageDockerignore
Copy-Item -Force $SalvageRequirements $SalvageRequirementsBak
Copy-Item -Force $Requirements $SalvageRequirements
$Tcb = @('tcb')
if ($env:TCB_ENV_ID) {
    $Tcb = @('tcb', '-e', $env:TCB_ENV_ID)
}

try {
    Set-Location $Salvage
    Write-Host "Deploying ai-assistant-salvage from $Salvage (port 8080)..."
    & @Tcb cloudrun deploy -s ai-assistant-salvage --source . --port 8080 @args
}
finally {
    Remove-Item -Force $SalvageDockerfile -ErrorAction SilentlyContinue
    if (Test-Path $SalvageRequirementsBak) {
        Move-Item -Force $SalvageRequirementsBak $SalvageRequirements
    }
    if (Test-Path $SalvageDockerignoreBak) {
        Move-Item -Force $SalvageDockerignoreBak $SalvageDockerignore
    } else {
        Remove-Item -Force $SalvageDockerignore -ErrorAction SilentlyContinue
    }
}
