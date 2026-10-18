@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Instale Python 3.11 ou superior pelo python.org, com o Python Launcher.
 pause
 exit /b 1
)
py -3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ necessario'"
if errorlevel 1 (pause & exit /b 1)
py -3 -m venv .venv
if errorlevel 1 (pause & exit /b 1)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
echo Configuracao concluida. Abra INICIAR_LAB.bat.
pause
