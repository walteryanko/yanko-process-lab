@echo off
setlocal
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
if not exist ".venv\Scripts\python.exe" (
  echo Execute primeiro INICIAR_LAB.bat para preparar o ambiente Python.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\reproduce.py
pause
