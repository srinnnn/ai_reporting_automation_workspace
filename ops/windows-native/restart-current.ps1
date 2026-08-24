param(
    [string]$DeployRoot = "C:\MiddlePlatformDeploy",
    [string]$DataRoot = "C:\MiddlePlatformData",
    [int]$Port = 8785
)

& "$PSScriptRoot\stop-current.ps1" -DeployRoot $DeployRoot
& "$PSScriptRoot\start-current.ps1" -DeployRoot $DeployRoot -DataRoot $DataRoot -Port $Port
