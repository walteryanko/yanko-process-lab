@echo off
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
if not exist .venv\Scripts\python.exe goto setup
.venv\Scripts\python.exe -m unittest discover -s tests -v
pause
exit /b
:setup
echo Execute INICIAR_LAB.bat primeiro.
pause
