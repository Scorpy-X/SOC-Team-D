$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Starting the frontend demo."
Write-Host "This demo currently uses mock data, so it does not require the Python backend."

& (Join-Path $projectRoot "scripts\start_frontend.ps1") -OpenBrowser
