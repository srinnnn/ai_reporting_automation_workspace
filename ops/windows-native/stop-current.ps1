param(
    [string]$DeployRoot = "C:\MiddlePlatformDeploy",
    [int]$TimeoutSeconds = 20
)

. "$PSScriptRoot\common.ps1"

$state = Read-RuntimeState -DeployRoot $DeployRoot
if ($null -eq $state -or -not $state.pid) {
    Write-DeploymentLog -DeployRoot $DeployRoot -Message "No runtime state found; nothing to stop."
    exit 0
}

$pidToStop = [int]$state.pid
$process = Get-Process -Id $pidToStop -ErrorAction SilentlyContinue
if ($null -eq $process) {
    Write-RuntimeState -DeployRoot $DeployRoot -State @{
        pid = $pidToStop
        release_sha = $state.release_sha
        stopped_at = (Get-Date).ToUniversalTime().ToString("o")
        port = $state.port
        status = "stopped"
    }
    Write-DeploymentLog -DeployRoot $DeployRoot -Message "Runtime PID $pidToStop was not running."
    exit 0
}

$process.CloseMainWindow() | Out-Null
$process.WaitForExit($TimeoutSeconds * 1000)
if (-not $process.HasExited) {
    Stop-Process -Id $pidToStop -Force
}

Write-RuntimeState -DeployRoot $DeployRoot -State @{
    pid = $pidToStop
    release_sha = $state.release_sha
    stopped_at = (Get-Date).ToUniversalTime().ToString("o")
    port = $state.port
    status = "stopped"
}
Write-DeploymentLog -DeployRoot $DeployRoot -Message "Stopped release $($state.release_sha) from PID $pidToStop."
