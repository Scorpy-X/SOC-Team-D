param(
    [switch]$OpenBrowser = $true
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$chainlitExe = Join-Path $projectRoot ".venv\Scripts\chainlit.exe"
$appPath = Join-Path $projectRoot "experiments\chainlit_chat\chat_app.py"
$port = 8010
$url = "http://localhost:$port"

# Chainlit treats DATABASE_URL as its own persistence toggle. Keep any backend
# override under the app-specific name instead of letting Chainlit claim it.
if ($env:DATABASE_URL -and -not $env:SOC_ADVISOR_DATABASE_URL) {
    $env:SOC_ADVISOR_DATABASE_URL = $env:DATABASE_URL
}
if ($env:DATABASE_URL) {
    Remove-Item Env:DATABASE_URL
}

if (-not (Test-Path $chainlitExe)) {
    Write-Host "Chainlit is not ready in this repo's virtual environment."
    Write-Host "Double-click Setup Dev.cmd first, then rerun Run Chainlit Experiment.cmd."
    exit 1
}

if (-not (Test-Path $appPath)) {
    Write-Host "The Chainlit experiment app is missing."
    exit 1
}

if ($OpenBrowser) {
    Start-Job -ScriptBlock {
        param($url)
        Start-Sleep -Seconds 4
        Start-Process $url | Out-Null
    } -ArgumentList $url | Out-Null
}

Write-Host "Starting the Chainlit chat experiment on $url"
Write-Host "This is an exploratory chat shell over the persisted questionnaire and portfolio experiment."
Write-Host "Backend DB overrides should use SOC_ADVISOR_DATABASE_URL, not DATABASE_URL."
Write-Host "If the browser does not open, visit $url"

& $chainlitExe run $appPath --port $port --headless
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
