@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "LOCAL_LAB_AI_ROOT=%SCRIPT_DIR%"
cd /d "%SCRIPT_DIR%"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%SCRIPT_DIR%\scripts\offline_check_main.py" %*
    goto :eof
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%SCRIPT_DIR%\scripts\offline_check_main.py" %*
    goto :eof
)

echo [LOCAL-LAB-AI] ERROR: no Python interpreter found on PATH.
exit /b 1
