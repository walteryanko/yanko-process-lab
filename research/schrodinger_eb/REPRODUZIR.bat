@echo off
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
if not exist .venv\Scripts\python.exe goto setup
.venv\Scripts\python.exe scripts\reproduce.py
pause
exit /b
:setup
echo Execute INICIAR_LAB.bat primeiro.
pause
