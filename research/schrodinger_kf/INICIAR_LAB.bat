@echo off
setlocal
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo Instale Python 3.12 ou superior em python.org e execute novamente.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import numpy,scipy" >nul 2>&1
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo A instalacao das dependencias falhou. Verifique a conexao.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m schrodinger_lab.server
pause
