@echo off
cd /d "%~dp0.."
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if "%PY%"=="" set "PY=python"

echo Installing PyInstaller ...
"%PY%" -m pip install --disable-pip-version-check --quiet pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

echo.
echo Building exe files ...
"%PY%" packaging\build_exe.py
pause
