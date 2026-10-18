@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Execute CONFIGURAR_WINDOWS.bat primeiro. & pause & exit /b 1)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
.venv\Scripts\python.exe -m premonition all --out results_reproduced --n 100
if errorlevel 1 (pause & exit /b 1)
echo Resultados novos em results_reproduced. Os resultados entregues foram preservados.
pause
