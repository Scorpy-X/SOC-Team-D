$projectRoot = Split-Path -Parent $PSScriptRoot
$activatePath = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $activatePath)) {
    Write-Host "Virtual environment not found."
    Write-Host "Run: Setup Dev.cmd"
    Write-Host "Or run: python scripts/bootstrap_env.py --skip-frontend"
    exit 1
}

. $activatePath
Write-Host "Virtual environment activated."
