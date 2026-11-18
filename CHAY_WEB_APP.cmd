@echo off
setlocal
title BTL XLA - Web App Demo
cd /d "%~dp0"

echo =====================================================================
echo   BTL XU LY ANH SO - HE THONG DEMO TRUC QUAN & THUYET TRINH
echo   De tai: Phat hien dac trung anh da ty le bang dao ham Gaussian
echo   Nen tang: Python Core (Zero-Dependency) vs FeatureJ Reference
echo =====================================================================
echo.
echo Dang khoi dong Web Server tai http://127.0.0.1:5000 ...
echo Trinh duyet web se tu dong duoc mo sau 1 giay.
echo (De mo cua so Desktop App rieng: chay lenh "CHAY_WEB_APP.cmd --desktop")
echo Nhan Ctrl+C de dung server khi ket thuc buoi bao cao.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -B -X utf8 -m src.web.app %*
) else (
    python -B -X utf8 -m src.web.app %*
)

if errorlevel 1 (
    echo.
    echo [LOI] Khong the khoi dong Web Server. Vui long kiem tra Python va thu vien.
    pause
)
