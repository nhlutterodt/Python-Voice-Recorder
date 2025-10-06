<#
Local environment setup for Voice Recorder Pro
Creates required directories, optionally writes .env.template, installs requirements into venv, and initializes the DB.
Run from repository root in PowerShell (with execution policy that allows running local scripts):

    .\Python - Voice Recorder\scripts\setup_local_env.ps1

#>
param(
    [switch]$InstallRequirements = $true,
    [switch]$CreateEnvTemplate = $false,
    [string]$VenvPath = ".\venv",
    [string]$ProjectSubdir = ".\Python - Voice Recorder"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Get-Location
$projectRoot = Join-Path $root $ProjectSubdir
Write-Host "Project root: $projectRoot"

# Create standard directories
$dirs = @('db', 'recordings/raw', 'recordings/edited', 'logs', 'config')
foreach ($d in $dirs) {
    $full = Join-Path $projectRoot $d
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full | Out-Null
        Write-Host "Created: $full"
    } else {
        Write-Host "Exists: $full"
    }
}

# Optionally create a .env.template
if ($CreateEnvTemplate) {
    $envTemplate = Join-Path $projectRoot '.env.template'
    if (-not (Test-Path $envTemplate)) {
        @"
# .env.template - local overrides for Voice Recorder Pro
APP_NAME=Voice Recorder Pro
APP_VERSION=2.0.0-beta
APP_DEBUG=false
APP_ENVIRONMENT=development
RECORDINGS_RAW_PATH=recordings/raw
RECORDINGS_EDITED_PATH=recordings/edited
DATABASE_URL=sqlite:///db/app.db
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=logs/app.log
# CLOUD_FEATURES_ENABLED=true
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
"@ | Out-File -FilePath $envTemplate -Encoding UTF8
        Write-Host "Created template: $envTemplate"
    } else {
        Write-Host ".env.template already exists"
    }
}

# Install requirements into venv if requested
if ($InstallRequirements) {
    $venvPython = Join-Path $root "$VenvPath\Scripts\python.exe"
    if (-Not (Test-Path $venvPython)) {
        Write-Host "Virtual environment not found at $venvPython - creating one"
        python -m venv $VenvPath
    }

    $requirementsFile = Join-Path $projectRoot 'requirements.txt'
    if (Test-Path $requirementsFile) {
        & $venvPython -m pip install --upgrade pip
        & $venvPython -m pip install -r $requirementsFile
    } else {
        Write-Host "requirements.txt not found at $requirementsFile"
    }
}

# Initialize the database (run init_db.py)
$initScript = Join-Path $projectRoot 'init_db.py'
if (Test-Path $initScript) {
    Write-Host "Initializing database via $initScript"
    & $venvPython $initScript
} else {
    Write-Host "init_db.py not found at $initScript"
}

Write-Host ""
Write-Host "🎉 Setup complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 To launch Voice Recorder Pro:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1 - Quick Launch (Recommended):" -ForegroundColor Cyan
Write-Host "  cd \"$ProjectSubdir\"" -ForegroundColor White
Write-Host "  .\Launch_VoiceRecorderPro.ps1 -Dev" -ForegroundColor White
Write-Host ""
Write-Host "Option 2 - Manual Launch:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  cd \"$ProjectSubdir\"" -ForegroundColor White
Write-Host '  $env:PYTHONPATH = "."' -ForegroundColor White
Write-Host "  python src\enhanced_main.py" -ForegroundColor White
Write-Host ""
Write-Host "Option 3 - Batch File (Windows):" -ForegroundColor Cyan
Write-Host "  cd \"$ProjectSubdir\"" -ForegroundColor White
Write-Host "  .\Launch_VoiceRecorderPro.bat -dev" -ForegroundColor White
Write-Host ""
Write-Host "💡 The key is setting PYTHONPATH=. and running from the project directory!" -ForegroundColor Yellow
