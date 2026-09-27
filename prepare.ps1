#!/usr/bin/env pwsh
# LOCAL-LAB-AI - one-time preparation (Windows PowerShell / PowerShell 7+). Requires internet access.
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:LOCAL_LAB_AI_ROOT = $ScriptDir
Set-Location $ScriptDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }

if (-not $python) {
    Write-Error "[LOCAL-LAB-AI] No Python interpreter found on PATH. Install Python 3.10+ from python.org first."
    exit 1
}

& $python.Source (Join-Path $ScriptDir "scripts\prepare_main.py") @args
exit $LASTEXITCODE
