#!/usr/bin/env pwsh
# LOCAL-LAB-AI - copy the prepared distribution onto a USB drive (Windows).
# Never formats a drive, never deletes existing files. Requires interactive confirmation.
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:LOCAL_LAB_AI_ROOT = $ScriptDir
Set-Location $ScriptDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }

if (-not $python) {
    Write-Error "[LOCAL-LAB-AI] No Python interpreter found on PATH."
    exit 1
}

& $python.Source (Join-Path $ScriptDir "scripts\deploy_usb_main.py") @args
exit $LASTEXITCODE
