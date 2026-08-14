@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
python "%~dp0webui.py" %*
if errorlevel 1 (
    echo.
    echo Failed to start. Please make sure Python and dependencies are installed.
    pause
)
