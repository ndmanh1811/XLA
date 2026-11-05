@echo off
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Can tao moi truong .venv theo README_DUC_05_11.md truoc.
  pause
  popd
  exit /b 1
)
".venv\Scripts\python.exe" -B -m src.eval.annotate_cells
set taskResult=%errorlevel%
if not "%taskResult%"=="0" goto taskFinish
".venv\Scripts\python.exe" -B -m src.eval.prepare_ground_truth
set taskResult=%errorlevel%
:taskFinish
pause
popd
exit /b %taskResult%
