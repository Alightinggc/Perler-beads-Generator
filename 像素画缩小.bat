@echo off
cd /d "%~dp0"

REM ==================== default extra args (edit here) ====================
REM Shrink Pixel Art - auto downscale big-pixel pixel art images.
REM Common extras (see shrink_pixel_art.py header for all options):
REM   set EXTRA=--autocrop
REM   set EXTRA=--quantize 12
REM   set EXTRA=--out-dir "output_"
REM Full list: python shrink_pixel_art.py --help
set EXTRA=
REM ========================================================================

if "%~1"=="" goto usage

:loop
if "%~1"=="" goto done
echo.
echo ========================================
echo  Shrink Pixel Art - Processing: %~nx1
echo ========================================
python shrink_pixel_art.py "%~1" %EXTRA%
shift
goto loop

:done
echo.
echo All done! Results are saved into the "output_" folder
echo (or the folder given by --out-dir in EXTRA).
echo.
echo Press any key to close...
pause >nul
exit /b

:usage
echo.
echo  Usage: drag image(s) or a folder onto this .bat file,
echo  and it will auto-detect the pixel-grid size and downscale
echo  the image back to single-pixel pixel art.
echo.
echo  Or run from command line:  python shrink_pixel_art.py image.png
echo.
echo Press any key to close...
pause >nul
