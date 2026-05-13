$projectRoot = Split-Path -Parent $PSScriptRoot
$healthUrl = "http://127.0.0.1:5000/health"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Test-BackendHealth {
    try {
        Invoke-WebRequest -UseBasicParsing $healthUrl -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

Write-Host "Starting the full advisory demo."
Write-Host "This demo uses the React frontend with the backend recommendation flow."

if (-not (Test-BackendHealth)) {
    if (-not (Test-Path $venvPython)) {
        Write-Host "The backend virtual environment is missing."
        Write-Host "Run: Setup Demo.cmd"
        exit 1
    }

    Write-Host "Backend is not running. Starting it in the background..."
    Start-Process powershell -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $projectRoot "scripts\start_backend.ps1"),
        "-OpenDocs:`$false"
    ) -WorkingDirectory $projectRoot | Out-Null

    $backendReady = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-BackendHealth) {
            $backendReady = $true
            break
        }
    }

    if (-not $backendReady) {
        Write-Host "The backend did not become ready on $healthUrl."
        Write-Host "Try: Run API.cmd"
        exit 1
    }
}

& (Join-Path $projectRoot "scripts\start_frontend.ps1") -OpenBrowser
