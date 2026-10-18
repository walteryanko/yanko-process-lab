@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto falha
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto falha
".venv\Scripts\python.exe" -m darwin.thesis_experiments --stage fit
if errorlevel 1 goto falha
".venv\Scripts\python.exe" -m darwin.thesis_experiments --stage run --n 20 --workers 4
if errorlevel 1 goto falha
".venv\Scripts\python.exe" -m darwin.thesis_reporting --stage all
if errorlevel 1 goto falha
start "" "reports\thesis\Graficos_Darwin_Dissertacao.html"
echo Concluido. Resultados em reports\thesis.
pause
exit /b 0
:falha
echo A reproducao falhou. Leia a mensagem acima.
pause
exit /b 1
