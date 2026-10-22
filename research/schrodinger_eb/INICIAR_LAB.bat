@echo off
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist web\data.js .venv\Scripts\python.exe scripts\bootstrap_demo.py
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m eblab.server
goto end
:fail
echo Falha. Verifique Python 3.11+ x64, conexao inicial e mensagens acima.
pause
:end
