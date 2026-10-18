@echo off
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
.venv\Scripts\python.exe -m pytest -q
pause
