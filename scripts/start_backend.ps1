param(
    [switch]$OpenDocs = $true
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$apiScript = Join-Path $projectRoot "scripts\run_advisor_api.py"
$envPath = Join-Path $projectRoot ".env"
$port = 8000

if (-not (Test-Path $apiScript)) {
    Write-Host "This repo does not include the exploratory API runner."
    exit 1
}

if (-not (Test-Path $venvPython)) {
    Write-Host "The Python virtual environment is missing."
    Write-Host "Run: Setup Dev.cmd"
    exit 1
}

if (Test-Path $envPath) {
    $portLine = Get-Content $envPath | Where-Object { $_ -match '^PORT=' } | Select-Object -First 1
    if ($portLine) {
        $resolvedPort = ($portLine -split '=', 2)[1].Trim()
        if ($resolvedPort) {
            $port = $resolvedPort
        }
    }
}

if ($OpenDocs) {
    Start-Job -ScriptBlock {
        param($url)
        Start-Sleep -Seconds 4
        Start-Process $url | Out-Null
    } -ArgumentList "http://127.0.0.1:$port/docs" | Out-Null
}

& $venvPython $apiScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
