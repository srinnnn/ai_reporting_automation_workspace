Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-PlatformDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Path must not be empty."
    }
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Write-DeploymentLog {
    param(
        [Parameter(Mandatory = $true)][string]$DeployRoot,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$FileName = "deployment.log"
    )
    New-PlatformDirectory -Path (Join-Path $DeployRoot "logs")
    $line = "$(Get-Date -Format o) $Message"
    Add-Content -Path (Join-Path (Join-Path $DeployRoot "logs") $FileName) -Value $line -Encoding utf8
}

function Read-EnvFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[0])) {
            throw "Invalid environment line in $Path"
        }
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $values
}

function Set-PlatformEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$DeployRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot,
        [Parameter(Mandatory = $true)][string]$ReleaseSha
    )
    $envFile = Join-Path $DeployRoot ".env"
    $values = Read-EnvFile -Path $envFile
    foreach ($key in $values.Keys) {
        [Environment]::SetEnvironmentVariable($key, $values[$key], "Process")
    }
    $env:APP_ENV = "production"
    $env:DEMO_MODE = "false"
    $env:INTRANET_HOST = "127.0.0.1"
    $env:INTRANET_PORT = "8785"
    $env:APP_COMMIT_SHA = $ReleaseSha
    if (-not $env:APP_VERSION) {
        $env:APP_VERSION = "3.0.0"
    }
    if (-not $env:APP_BUILD_TIME) {
        $env:APP_BUILD_TIME = (Get-Date).ToUniversalTime().ToString("o")
    }
    $env:RUNTIME_DIR = Join-Path $DataRoot "runtime"
    $env:UPLOAD_DIR = Join-Path $DataRoot "uploads"
    $env:RESULT_DIR = Join-Path $DataRoot "results"
    $env:LOG_DIR = Join-Path $DataRoot "logs"
    $env:SQLITE_PATH = Join-Path (Join-Path $DataRoot "database") "intranet.sqlite3"
}

function Initialize-DeployRoot {
    param(
        [Parameter(Mandatory = $true)][string]$DeployRoot,
        [Parameter(Mandatory = $true)][string]$DataRoot
    )
    foreach ($path in @(
        $DeployRoot,
        (Join-Path $DeployRoot "releases"),
        (Join-Path $DeployRoot "shared"),
        (Join-Path $DeployRoot "logs"),
        (Join-Path $DeployRoot "backups"),
        $DataRoot,
        (Join-Path $DataRoot "runtime"),
        (Join-Path $DataRoot "uploads"),
        (Join-Path $DataRoot "results"),
        (Join-Path $DataRoot "database"),
        (Join-Path $DataRoot "backups"),
        (Join-Path $DataRoot "logs")
    )) {
        New-PlatformDirectory -Path $path
    }
}

function Get-CurrentReleaseSha {
    param([Parameter(Mandatory = $true)][string]$DeployRoot)
    $path = Join-Path $DeployRoot "current-release.txt"
    if (-not (Test-Path -LiteralPath $path)) {
        throw "current-release.txt does not exist."
    }
    $sha = (Get-Content -LiteralPath $path -Raw).Trim()
    if ($sha -notmatch "^[0-9a-fA-F]{7,40}$") {
        throw "current-release.txt does not contain a valid commit SHA."
    }
    return $sha
}

function Get-ReleasePath {
    param(
        [Parameter(Mandatory = $true)][string]$DeployRoot,
        [Parameter(Mandatory = $true)][string]$ReleaseSha
    )
    if ($ReleaseSha -notmatch "^[0-9a-fA-F]{7,40}$") {
        throw "ReleaseSha must be a commit SHA."
    }
    return Join-Path (Join-Path $DeployRoot "releases") $ReleaseSha
}

function Read-RuntimeState {
    param([Parameter(Mandatory = $true)][string]$DeployRoot)
    $path = Join-Path $DeployRoot "runtime-state.json"
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }
    return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}

function Write-RuntimeState {
    param(
        [Parameter(Mandatory = $true)][string]$DeployRoot,
        [Parameter(Mandatory = $true)][hashtable]$State
    )
    $path = Join-Path $DeployRoot "runtime-state.json"
    $State | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding utf8
}

function Assert-ReleaseReady {
    param(
        [Parameter(Mandatory = $true)][string]$ReleasePath
    )
    if (-not (Test-Path -LiteralPath $ReleasePath -PathType Container)) {
        throw "Release directory does not exist: $ReleasePath"
    }
    $python = Join-Path $ReleasePath ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Release Python environment does not exist: $python"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $ReleasePath "backend\main.py") -PathType Leaf)) {
        throw "Release backend entry is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $ReleasePath "frontend\dist\index.html") -PathType Leaf)) {
        throw "Release frontend dist is missing."
    }
    return $python
}
