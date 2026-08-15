@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM ---- 优先使用本目录虚拟环境中的 Python（没装过环境时退回系统 Python）----
set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo 未检测到 Python 运行环境，请先双击运行「一键安装环境.bat」。
    pause
    exit /b 1
)

"%PY%" "%~dp0interactive.py" %*
if errorlevel 1 (
    echo.
    echo Failed to start. Please make sure Python and dependencies are installed.
    pause
)
