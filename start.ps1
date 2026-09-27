#!/usr/bin/env pwsh
# LOCAL-LAB-AI - fully offline startup (Windows PowerShell / PowerShell 7+).
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:LOCAL_LAB_AI_ROOT = $ScriptDir
Set-Location $ScriptDir

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }

if (-not $python) {
    Write-Error "[LOCAL-LAB-AI] No Python interpreter found on PATH. Python 3.10+ must be installed once."
    exit 1
}

& $python.Source (Join-Path $ScriptDir "scripts\start_main.py") @args
exit $LASTEXITCODE
