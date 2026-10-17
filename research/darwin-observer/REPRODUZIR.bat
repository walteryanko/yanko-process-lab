@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto fim
".venv\Scripts\python.exe" -m darwin.experiments --stage all --n 100 --workers 4
if errorlevel 1 goto fim
".venv\Scripts\python.exe" -m darwin.ablations
".venv\Scripts\python.exe" -m darwin.reporting
:fim
pause
