@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B -X utf8 -u -m src.eval.run_metrics
) else (
    py -3 -B -X utf8 -u -m src.eval.run_metrics
)
if errorlevel 1 goto failed
echo.
echo COMPLETE. Open outputs\metrics\duc_08_11\KET_QUA_METRIC.md
echo Strict numerical FAIL results are reported as measured.
pause
exit /b 0
:failed
echo.
echo ERROR. Read the error above and outputs\metrics\duc_08_11\run_manifest.json
echo Do not use results from an ERROR or RUNNING run for delivery.
pause
exit /b 1
