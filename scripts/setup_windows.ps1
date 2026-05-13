param(
    [switch]$SkipPython,
    [switch]$SkipFrontend,
    [switch]$InstallMissingTools = $true
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envExamplePath = Join-Path $projectRoot ".env.example"
$envPath = Join-Path $projectRoot ".env"
$frontendPath = Join-Path $projectRoot "frontend"

function Write-Step {
    param([string]$Message)

    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Invoke-NativeCommand {
    param(
        [string]$Command,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $projectRoot
    )

    $printableArgs = $Arguments -join " "
    Write-Host "[run] $Command $printableArgs"

    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $Command $printableArgs"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-WingetCommand {
    return Get-Command "winget" -ErrorAction SilentlyContinue
}

function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$Label,
        [switch]$UseUpgrade
    )

    $winget = Get-WingetCommand
    if (-not $winget) {
        throw "winget is not available. Install the missing tool manually and rerun this script."
    }

    Write-Step "Installing $Label"

    $arguments = @()
    if ($UseUpgrade) {
        $arguments += "upgrade"
    }
    else {
        $arguments += "install"
    }

    $arguments += @(
        "--exact",
        "--id", $PackageId,
        "--accept-package-agreements",
        "--accept-source-agreements"
    )

    Invoke-NativeCommand -Command $winget.Source -Arguments $arguments
}

function Test-PythonVersion {
    param([string]$VersionText)

    try {
        $version = [version]$VersionText
    }
    catch {
        return $false
    }

    return ($version.Major -gt 3) -or ($version.Major -eq 3 -and $version.Minor -ge 12)
}

function Get-PythonInfo {
    $py = Get-Command "py" -ErrorAction SilentlyContinue
    if ($py) {
        foreach ($arguments in @(@("-3.12"), @("-3"))) {
            try {
                $versionText = (& $py.Source @arguments -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null).Trim()
                if ($LASTEXITCODE -eq 0 -and (Test-PythonVersion -VersionText $versionText)) {
                    return [pscustomobject]@{
                        Command   = $py.Source
                        Arguments = $arguments
                        Version   = $versionText
                    }
                }
            }
            catch {
            }
        }
    }

    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if ($python) {
        try {
            $versionText = (& $python.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null).Trim()
            if ($LASTEXITCODE -eq 0 -and (Test-PythonVersion -VersionText $versionText)) {
                return [pscustomobject]@{
                    Command   = $python.Source
                    Arguments = @()
                    Version   = $versionText
                }
            }
        }
        catch {
        }
    }

    return $null
}

function Ensure-Python {
    $pythonInfo = Get-PythonInfo
    if ($pythonInfo) {
        Write-Host "Using Python $($pythonInfo.Version)"
        return $pythonInfo
    }

    if (-not $InstallMissingTools) {
        throw "Python 3.12+ was not found."
    }

    Install-WingetPackage -PackageId "Python.Python.3.12" -Label "Python 3.12"
    $pythonInfo = Get-PythonInfo
    if (-not $pythonInfo) {
        throw "Python 3.12+ is still not available after installation."
    }

    Write-Host "Using Python $($pythonInfo.Version)"
    return $pythonInfo
}

function Get-NpmCommand {
    foreach ($candidate in @("npm.cmd", "npm")) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            return $candidate
        }
    }

    return $null
}

function Test-NodeVersion {
    param([string]$VersionText)

    try {
        $version = [version]($VersionText.Trim().TrimStart("v"))
    }
    catch {
        return $false
    }

    if ($version.Major -eq 20) {
        return $version.Minor -ge 19
    }

    return $version.Major -ge 22
}

function Get-NodeInfo {
    $node = Get-Command "node" -ErrorAction SilentlyContinue
    $npm = Get-NpmCommand
    if (-not $node -or -not $npm) {
        return $null
    }

    try {
        $versionText = (& $node.Source --version 2>$null).Trim()
        if (-not $versionText) {
            return $null
        }
    }
    catch {
        return $null
    }

    return [pscustomobject]@{
        NodeCommand = $node.Source
        NpmCommand  = $npm
        Version     = $versionText
        IsSupported = (Test-NodeVersion -VersionText $versionText)
    }
}

function Ensure-Node {
    $nodeInfo = Get-NodeInfo
    if ($nodeInfo -and $nodeInfo.IsSupported) {
        Write-Host "Using Node $($nodeInfo.Version)"
        return $nodeInfo
    }

    if ($nodeInfo -and -not $nodeInfo.IsSupported) {
        $winget = Get-WingetCommand
        if ($InstallMissingTools -and $winget) {
            Install-WingetPackage -PackageId "OpenJS.NodeJS.LTS" -Label "Node.js LTS" -UseUpgrade
            $nodeInfo = Get-NodeInfo
            if (-not $nodeInfo -or -not $nodeInfo.IsSupported) {
                throw "Node.js is still missing or below the supported version after installation."
            }

            Write-Host "Using Node $($nodeInfo.Version)"
            return $nodeInfo
        }

        Write-Host "Warning: Node $($nodeInfo.Version) is below the preferred frontend version."
        Write-Host "The script will continue, but npm install may still fail."
        Write-Host "Preferred versions are Node 22.12+ or Node 20.19+."
        return $nodeInfo
    }

    if (-not $InstallMissingTools) {
        throw "Node.js was not found."
    }

    Install-WingetPackage -PackageId "OpenJS.NodeJS.LTS" -Label "Node.js LTS"
    $nodeInfo = Get-NodeInfo
    if (-not $nodeInfo -or -not $nodeInfo.IsSupported) {
        throw "Node.js is still missing or below the supported version after installation."
    }

    Write-Host "Using Node $($nodeInfo.Version)"
    return $nodeInfo
}

function Ensure-EnvFile {
    if (Test-Path $envPath) {
        Write-Host "Using existing .env file."
        return
    }

    if (-not (Test-Path $envExamplePath)) {
        Write-Host ".env.example was not found. Skipping .env creation."
        return
    }

    Copy-Item $envExamplePath $envPath
    Write-Host "Created .env from .env.example."
}

function Install-FrontendDependencies {
    param([string]$NpmCommand)

    if (-not (Test-Path $frontendPath)) {
        Write-Host "Frontend folder not found. Skipping frontend dependency install."
        return
    }

    $arguments = @()
    if (Test-Path (Join-Path $frontendPath "package-lock.json")) {
        $arguments = @("ci", "--no-audit", "--no-fund")
    }
    else {
        $arguments = @("install", "--no-audit", "--no-fund")
    }

    Invoke-NativeCommand -Command $NpmCommand -Arguments $arguments -WorkingDirectory $frontendPath
}

if ($SkipPython -and $SkipFrontend) {
    Write-Host "Nothing to do because both Python and frontend setup were skipped."
    exit 0
}

if ($SkipPython) {
    Write-Step "Frontend demo setup"
    $nodeInfo = Ensure-Node
    Install-FrontendDependencies -NpmCommand $nodeInfo.NpmCommand
    Write-Host ""
    Write-Host "Demo setup complete."
    Write-Host "Next step: double-click Run Demo.cmd"
    exit 0
}

Write-Step "Developer setup"
$pythonInfo = Ensure-Python

if (-not $SkipFrontend) {
    $null = Ensure-Node
}

Ensure-EnvFile

$bootstrapArguments = @("scripts/bootstrap_env.py")
if ($SkipFrontend) {
    $bootstrapArguments += "--skip-frontend"
}

Invoke-NativeCommand -Command $pythonInfo.Command -Arguments ($pythonInfo.Arguments + $bootstrapArguments)

Write-Host ""
Write-Host "Developer setup complete."
Write-Host "Next step: double-click Run Demo.cmd"
if (Test-Path (Join-Path $projectRoot "Run API.cmd")) {
    Write-Host "Optional: double-click Run API.cmd to start the exploratory backend."
}
if (Test-Path (Join-Path $projectRoot "Run Chainlit Experiment.cmd")) {
    Write-Host "Optional: double-click Run Chainlit Experiment.cmd to start the chat experiment."
}
