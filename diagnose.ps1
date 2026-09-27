#!/usr/bin/env pwsh
# LOCAL-LAB-AI - diagnostic report (Windows PowerShell / PowerShell 7+).
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

& $python.Source (Join-Path $ScriptDir "scripts\diagnose_main.py") @args
exit $LASTEXITCODE
