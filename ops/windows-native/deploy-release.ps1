param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [Parameter(Mandatory = $true)][string]$TargetSha,
    [string]$DeployRoot = "C:\MiddlePlatformDeploy",
    [string]$DataRoot = "C:\MiddlePlatformData"
)

. "$PSScriptRoot\common.ps1"

if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw "RepositoryRoot does not exist."
}
if ($TargetSha -notmatch "^[0-9a-fA-F]{40}$") {
    throw "TargetSha must be a full commit SHA."
}

Initialize-DeployRoot -DeployRoot $DeployRoot -DataRoot $DataRoot
Write-DeploymentLog -DeployRoot $DeployRoot -Message "Deploy preflight for $TargetSha."

Push-Location $RepositoryRoot
try {
    git fetch origin main --prune
    git merge-base --is-ancestor $TargetSha origin/main
    if ($LASTEXITCODE -ne 0) {
        throw "Target SHA is not reachable from origin/main."
    }
    git checkout --detach $TargetSha
} finally {
    Pop-Location
}

$releasePath = Get-ReleasePath -DeployRoot $DeployRoot -ReleaseSha $TargetSha
if (Test-Path -LiteralPath $releasePath) {
    throw "Release already exists: $releasePath"
}
New-PlatformDirectory -Path $releasePath

Push-Location $RepositoryRoot
try {
    Push-Location "frontend"
    try {
        npm ci
        npm run build
    } finally {
        Pop-Location
    }

    foreach ($name in @("backend", "intranet_app", "tools", "ai_report_config_materials")) {
        Copy-Item -LiteralPath (Join-Path $RepositoryRoot $name) -Destination (Join-Path $releasePath $name) -Recurse
    }
    New-PlatformDirectory -Path (Join-Path $releasePath "frontend")
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot "frontend\dist") -Destination (Join-Path $releasePath "frontend\dist") -Recurse
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot "requirements-prod.txt") -Destination (Join-Path $releasePath "requirements-prod.txt")
    Copy-Item -LiteralPath (Join-Path $RepositoryRoot ".env.example") -Destination (Join-Path $releasePath ".env.example")

    $metadata = @{
        commit_sha = $TargetSha
        built_at = (Get-Date).ToUniversalTime().ToString("o")
        runtime = "windows-native-uvicorn"
    }
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $releasePath "release-metadata.json") -Encoding utf8
} finally {
    Pop-Location
}

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $pythonLauncher) {
    & py -3.12 -m venv (Join-Path $releasePath ".venv")
} else {
    & python -m venv (Join-Path $releasePath ".venv")
}
$releasePython = Join-Path $releasePath ".venv\Scripts\python.exe"
& $releasePython -m pip install --upgrade pip
& $releasePython -m pip install -r (Join-Path $releasePath "requirements-prod.txt")

Copy-Item -LiteralPath "$PSScriptRoot\start-current.ps1" -Destination (Join-Path $DeployRoot "start-current.ps1") -Force
Copy-Item -LiteralPath "$PSScriptRoot\stop-current.ps1" -Destination (Join-Path $DeployRoot "stop-current.ps1") -Force
Copy-Item -LiteralPath "$PSScriptRoot\restart-current.ps1" -Destination (Join-Path $DeployRoot "restart-current.ps1") -Force
Copy-Item -LiteralPath "$PSScriptRoot\health-check.ps1" -Destination (Join-Path $DeployRoot "health-check.ps1") -Force
Copy-Item -LiteralPath "$PSScriptRoot\register-startup-task.ps1" -Destination (Join-Path $DeployRoot "register-startup-task.ps1") -Force
Copy-Item -LiteralPath "$PSScriptRoot\common.ps1" -Destination (Join-Path $DeployRoot "common.ps1") -Force

$currentFile = Join-Path $DeployRoot "current-release.txt"
$previousSha = ""
if (Test-Path -LiteralPath $currentFile) {
    $previousSha = (Get-Content -LiteralPath $currentFile -Raw).Trim()
}

$databasePath = Join-Path (Join-Path $DataRoot "database") "intranet.sqlite3"
if (Test-Path -LiteralPath $databasePath -PathType Leaf) {
    $backupName = "$(Get-Date -Format yyyyMMddHHmmss)-$TargetSha.db"
    Copy-Item -LiteralPath $databasePath -Destination (Join-Path (Join-Path $DataRoot "backups") $backupName)
}

try {
    & "$PSScriptRoot\stop-current.ps1" -DeployRoot $DeployRoot
    Set-Content -LiteralPath $currentFile -Value $TargetSha -Encoding ascii
    & "$PSScriptRoot\start-current.ps1" -DeployRoot $DeployRoot -DataRoot $DataRoot
    Start-Sleep -Seconds 3
    & "$PSScriptRoot\health-check.ps1" -ExpectedSha $TargetSha | Out-Null
    @{
        status = "DEPLOYED"
        current_sha = $TargetSha
        previous_successful_sha = $previousSha
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $DeployRoot "deployment-state.json") -Encoding utf8
    Write-DeploymentLog -DeployRoot $DeployRoot -Message "Deploy succeeded for $TargetSha."
} catch {
    Write-DeploymentLog -DeployRoot $DeployRoot -Message "Deploy failed for ${TargetSha}: $($_.Exception.Message)"
    if ($previousSha) {
        & "$PSScriptRoot\stop-current.ps1" -DeployRoot $DeployRoot
        Set-Content -LiteralPath $currentFile -Value $previousSha -Encoding ascii
        & "$PSScriptRoot\start-current.ps1" -DeployRoot $DeployRoot -DataRoot $DataRoot
        Start-Sleep -Seconds 3
        & "$PSScriptRoot\health-check.ps1" -ExpectedSha $previousSha | Out-Null
        @{
            status = "FAILED_ROLLED_BACK"
            failed_sha = $TargetSha
            current_sha = $previousSha
            updated_at = (Get-Date).ToUniversalTime().ToString("o")
        } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $DeployRoot "deployment-state.json") -Encoding utf8
        throw "Deployment failed and rollback restored $previousSha."
    }
    @{
        status = "CRITICAL_FAILURE"
        failed_sha = $TargetSha
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $DeployRoot "deployment-state.json") -Encoding utf8
    throw
}
