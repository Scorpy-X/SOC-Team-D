param(
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendPath = Join-Path $projectRoot "frontend"
$nodeModulesPath = Join-Path $frontendPath "node_modules"
$demoHost = "127.0.0.1"
$demoPort = 5173
$demoUrl = "http://${demoHost}:${demoPort}"

function Get-NpmCommand {
    foreach ($candidate in @("npm.cmd", "npm")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }

    return $null
}

if (-not (Test-Path $frontendPath)) {
    Write-Host "Frontend folder was not found."
    exit 1
}

$npmCommand = Get-NpmCommand
if (-not $npmCommand) {
    Write-Host "npm was not found."
    Write-Host "Run: Setup Demo.cmd"
    exit 1
}

if (-not (Test-Path $nodeModulesPath)) {
    Write-Host "Frontend dependencies are not installed."
    Write-Host "Run: Setup Demo.cmd"
    exit 1
}

if ($OpenBrowser) {
    Start-Job -ScriptBlock {
        param($url)
        Start-Sleep -Seconds 4
        Start-Process $url | Out-Null
    } -ArgumentList $demoUrl | Out-Null
}

Push-Location $frontendPath
try {
    Write-Host "Starting frontend dev server..."
    Write-Host "If the browser does not open automatically, go to $demoUrl"
    & $npmCommand run dev -- --host $demoHost --port $demoPort --strictPort
    if ($LASTEXITCODE -ne 0) {
        Write-Host "The frontend dev server could not start on $demoUrl."
        Write-Host "If another process is using port $demoPort, stop it first and rerun Run Demo.cmd."
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
