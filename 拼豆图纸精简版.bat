@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM ================== 在这里修改默认参数 ==================
REM 色板: perler(95色) / artkal(30色) / hama(28色) / mard(MARD 291色)
set PALETTE=mard
REM 色号标注: brand(品牌色号，如H5/F11) / letter(A,B,C) / number(1,2,3)
set LABEL=brand
REM 最多用色（0=不限）
set MAXCOLORS=24
REM 每格像素大小（越大色号越清晰，brand 建议 >=28）
set CELL=30
REM 额外参数，如 --coords(坐标) / --title "我的图纸" / --bg-hex "#FFFFFF"
set EXTRA=--coords
REM ========================================================

:loop
if "%~1"=="" goto done
echo.
echo ========================================
echo  拼豆图纸转换器 - 正在处理: %~nx1
echo ========================================
echo.
python main.py "%~1" --palette %PALETTE% --label-style %LABEL% --max-colors %MAXCOLORS% --cell %CELL% --out-dir "output\%~n1_%PALETTE%_%MAXCOLORS%" %EXTRA% --no-colors-csv --no-grid-csv
shift
goto loop

:done
echo.
echo 全部完成！结果已保存到 output 下对应的文件名子文件夹。
echo 按任意键关闭...
pause >nul
