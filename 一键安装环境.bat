@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title 拼豆图纸转换器 - 一键安装运行环境

echo ================================================
echo   拼豆图纸转换器 - 一键安装运行环境
echo ================================================
echo.
echo 本脚本会自动完成以下事情：
echo   1. 检测 Python（没有则尝试自动安装 / 打开官网下载页）
echo   2. 在本目录创建虚拟环境 .venv（不影响系统 Python）
echo   3. 安装全部依赖（numpy + Pillow，国内自动换清华镜像重试）
echo.
echo 若之前安装失败，可先手动删除本目录的 .venv 文件夹再重试。
echo.

rem ==================== 1. 查找 Python ====================
echo [1/3] 检测 Python ...
set "PY="

py -3 -c "import sys; print(sys.executable)" >nul 2>&1
if errorlevel 1 goto try_python
for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)"') do set "PY=%%i"
goto python_found

:try_python
python -c "import sys; print(sys.executable)" >nul 2>&1
if errorlevel 1 goto no_python
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)"') do set "PY=%%i"
goto python_found

:no_python
echo.
echo [提示] 未检测到 Python，尝试用 winget 自动安装 ...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements >nul 2>&1
if errorlevel 1 (
    echo 自动安装失败，正在打开 Python 官网下载页 ...
    start "" https://www.python.org/downloads/
    echo.
    echo 请手动下载安装 Python 3.9 或更高版本，安装时务必勾选：
    echo    "Add python.exe to PATH"
    echo 装好后重新双击运行本脚本即可。
    echo.
    pause
    exit /b 1
)
echo Python 已安装成功。
echo 请关闭本窗口，然后重新双击运行本脚本（让新装的 Python 生效）。
echo.
pause
exit /b 0

:python_found
echo   已找到 Python："%PY%"
"%PY%" --version

rem ---------- 版本检查（需要 3.9+） ----------
"%PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [错误] 本工具需要 Python 3.9 或更高版本，当前版本过低。
    echo 请到 https://www.python.org/downloads/ 安装新版 Python 后重试。
    pause
    exit /b 1
)

rem ==================== 2. 创建虚拟环境 ====================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo [2/3] 检测到 .venv 不可用（可能是从别的电脑复制来的），正在重建 ...
        rmdir /s /q ".venv"
    ) else (
        echo [2/3] 已存在可用的虚拟环境 .venv，跳过创建。
        goto venv_ready
    )
)
echo [2/3] 正在创建虚拟环境 .venv ...
"%PY%" -m venv .venv
if errorlevel 1 (
    echo.
    echo [错误] 虚拟环境创建失败！
    pause
    exit /b 1
)

:venv_ready
set "VENVPY=%~dp0.venv\Scripts\python.exe"

rem ==================== 3. 安装依赖 ====================
echo.
echo [3/3] 正在安装依赖（numpy + Pillow），需要联网，请稍候 ...
"%VENVPY%" -m pip install --upgrade pip --quiet
"%VENVPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo 默认源安装失败，正在尝试清华镜像源 ...
    "%VENVPY%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败！请检查网络后重试。
        pause
        exit /b 1
    )
)

rem ==================== 4. 验证 ====================
echo.
echo 正在验证依赖是否可用 ...
"%VENVPY%" -c "import numpy, PIL; print('  numpy  ', numpy.__version__); print('  Pillow ', PIL.__version__)"
if errorlevel 1 (
    echo.
    echo [错误] 依赖验证失败！
    pause
    exit /b 1
)

"%VENVPY%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo [警告] 未检测到 tkinter（文件选择框不可用，拖拽/命令行功能不受影响）。
)

echo.
echo ================================================
echo   环境安装完成！现在可以正常使用了：
echo.
echo     1. 拼豆图纸精简版.bat    拖图片即转
echo     2. 拼豆图纸参数自选.bat  菜单调参
echo     3. 拼豆图纸网页版.bat    网页界面
echo     4. 像素画缩小.bat        大图先缩小
echo ================================================
echo.
pause
