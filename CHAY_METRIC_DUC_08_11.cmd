@echo off
rem Compatibility shortcut; the archived 08/11 results are never overwritten.
call "%~dp0CHAY_METRIC_DUC.cmd" %*
exit /b %errorlevel%
