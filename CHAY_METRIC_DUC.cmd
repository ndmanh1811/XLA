@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B -X utf8 -u -m src.eval.run_metrics %*
) else (
    py -3 -B -X utf8 -u -m src.eval.run_metrics %*
)
if errorlevel 1 goto failed
echo COMPLETE. Open outputs\metrics\duc_10_11\KET_QUA_METRIC.md
echo Next: CHAY_CONG_VIEC_5_DUC.cmd
if not "%DUC_NO_PAUSE%"=="1" pause
exit /b 0
:failed
echo ERROR. Read outputs\metrics\duc_10_11\run_manifest.json
if not "%DUC_NO_PAUSE%"=="1" pause
exit /b 1
