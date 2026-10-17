@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0CONFIGURAR_WINDOWS.ps1"
  if errorlevel 1 goto erro
)
".venv\Scripts\python.exe" -m darwin.dashboard --open
goto fim
:erro
echo Falha na configuracao. Consulte o README.
:fim
pause
