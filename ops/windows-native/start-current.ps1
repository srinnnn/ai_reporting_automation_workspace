param(
    [string]$DeployRoot = "C:\MiddlePlatformDeploy",
    [string]$DataRoot = "C:\MiddlePlatformData",
    [int]$Port = 8785
)

. "$PSScriptRoot\common.ps1"

Initialize-DeployRoot -DeployRoot $DeployRoot -DataRoot $DataRoot
$sha = Get-CurrentReleaseSha -DeployRoot $DeployRoot
$releasePath = Get-ReleasePath -DeployRoot $DeployRoot -ReleaseSha $sha
$python = Assert-ReleaseReady -ReleasePath $releasePath
Set-PlatformEnvironment -DeployRoot $DeployRoot -DataRoot $DataRoot -ReleaseSha $sha

$existing = Read-RuntimeState -DeployRoot $DeployRoot
if ($null -ne $existing -and $existing.status -eq "running" -and $existing.pid) {
    $process = Get-Process -Id ([int]$existing.pid) -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        throw "Middle Platform is already running with PID $($existing.pid)."
    }
}

$logDir = Join-Path $DeployRoot "logs"
New-PlatformDirectory -Path $logDir
$outLog = Join-Path $logDir "application.log"
$errLog = Join-Path $logDir "application-error.log"
$arguments = @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "$Port")
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $releasePath -PassThru -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog

Write-RuntimeState -DeployRoot $DeployRoot -State @{
    pid = $process.Id
    release_sha = $sha
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    port = $Port
    status = "running"
}
Write-DeploymentLog -DeployRoot $DeployRoot -Message "Started release $sha on PID $($process.Id)."
