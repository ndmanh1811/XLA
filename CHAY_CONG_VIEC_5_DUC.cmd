@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B -X utf8 -u -m src.eval.analyze_task5
) else (
    py -3 -B -X utf8 -u -m src.eval.analyze_task5
)
if errorlevel 1 goto failed
echo.
echo COMPLETE. Open MO_BIEU_DO_DUC.cmd to view charts.
pause
exit /b 0
:failed
echo.
echo ERROR. Check the message above and analysis_manifest.json.
echo If requested, rerun with --remeasure-runtime as described in README_DUC_CONG_VIEC_5.md.
pause
exit /b 1
