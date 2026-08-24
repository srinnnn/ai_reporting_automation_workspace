param(
    [string]$BaseUrl = "http://127.0.0.1:8785",
    [string]$ExpectedSha = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-JsonEndpoint {
    param([Parameter(Mandatory = $true)][string]$Url)
    $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 10
    if ($null -eq $response) {
        throw "Empty response from $Url"
    }
    return $response
}

$health = Invoke-JsonEndpoint -Url "$BaseUrl/api/v1/health"
if ($health.status -ne "ok") {
    throw "Health endpoint failed."
}

$ready = Invoke-JsonEndpoint -Url "$BaseUrl/api/v1/ready"
if ($ready.status -ne "ok") {
    throw "Ready endpoint failed."
}

$version = Invoke-JsonEndpoint -Url "$BaseUrl/api/v1/version"
if ($ExpectedSha -and $version.commit_sha -ne $ExpectedSha) {
    throw "Version SHA mismatch. expected=$ExpectedSha actual=$($version.commit_sha)"
}

[pscustomobject]@{
    health = $health.status
    ready = $ready.status
    commit_sha = $version.commit_sha
    base_url = $BaseUrl
} | ConvertTo-Json
