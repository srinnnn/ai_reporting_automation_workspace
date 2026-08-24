param(
    [string]$TargetSha = "",
    [string]$DeployRoot = "C:\MiddlePlatformDeploy",
    [string]$DataRoot = "C:\MiddlePlatformData"
)

. "$PSScriptRoot\common.ps1"

Initialize-DeployRoot -DeployRoot $DeployRoot -DataRoot $DataRoot
if (-not $TargetSha) {
    $statePath = Join-Path $DeployRoot "deployment-state.json"
    if (-not (Test-Path -LiteralPath $statePath)) {
        throw "No deployment-state.json exists and TargetSha was not provided."
    }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if (-not $state.previous_successful_sha) {
        throw "deployment-state.json does not contain previous_successful_sha."
    }
    $TargetSha = $state.previous_successful_sha
}

$releasePath = Get-ReleasePath -DeployRoot $DeployRoot -ReleaseSha $TargetSha
Assert-ReleaseReady -ReleasePath $releasePath | Out-Null
Write-DeploymentLog -DeployRoot $DeployRoot -FileName "rollback.log" -Message "Rollback requested to $TargetSha."

& "$PSScriptRoot\stop-current.ps1" -DeployRoot $DeployRoot
Set-Content -LiteralPath (Join-Path $DeployRoot "current-release.txt") -Value $TargetSha -Encoding ascii
& "$PSScriptRoot\start-current.ps1" -DeployRoot $DeployRoot -DataRoot $DataRoot
Start-Sleep -Seconds 3
& "$PSScriptRoot\health-check.ps1" -ExpectedSha $TargetSha | Out-Null

@{
    status = "ROLLED_BACK"
    current_sha = $TargetSha
    updated_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $DeployRoot "deployment-state.json") -Encoding utf8
Write-DeploymentLog -DeployRoot $DeployRoot -FileName "rollback.log" -Message "Rollback succeeded to $TargetSha."
