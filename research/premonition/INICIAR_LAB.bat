@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Execute CONFIGURAR_WINDOWS.bat primeiro. Para apenas explorar, abra PREMONITION_LAB.html.
 pause
 exit /b 1
)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
.venv\Scripts\python.exe -m premonition serve
pause
