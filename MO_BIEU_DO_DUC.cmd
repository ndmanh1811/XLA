@echo off
setlocal
if not exist "%~dp0outputs\analysis\duc_task5_08_11\index.html" goto missing
start "" "%~dp0outputs\analysis\duc_task5_08_11\index.html"
exit /b 0
:missing
echo Gallery not found. Run CHAY_CONG_VIEC_5_DUC.cmd first.
pause
exit /b 1
