#!/usr/bin/env pwsh
<#
.SYNOPSIS
Launch Voice Recorder Pro application with proper Python path configuration
#>

param(
    [switch]$Dev = $false
)

# Get the script's directory
$scriptDir = Split-Path -Parent (Get-Item $MyInvocation.MyCommand.Path).FullName

# Set PYTHONPATH to include the project root
$env:PYTHONPATH = $scriptDir

# Launch the application
if ($Dev) {
    Write-Host "Launching Voice Recorder Pro in development mode..."
    python src/entrypoint.py
} else {
    Write-Host "Launching Voice Recorder Pro..."
    python src/entrypoint.py
}
