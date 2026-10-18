from pathlib import Path
root=Path(__file__).resolve().parents[1]
files={
'CONFIGURAR_WINDOWS.bat':r'''@echo off
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
''',
'INICIAR_LAB.bat':r'''@echo off
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
''',
'REPRODUZIR.bat':r'''@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Execute CONFIGURAR_WINDOWS.bat primeiro. & pause & exit /b 1)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
.venv\Scripts\python.exe -m premonition all --out results_reproduced --n 100
if errorlevel 1 (pause & exit /b 1)
echo Resultados novos em results_reproduced. Os resultados entregues foram preservados.
pause
''',
'TESTAR.bat':r'''@echo off
cd /d "%~dp0"
set OPENBLAS_NUM_THREADS=1
.venv\Scripts\python.exe -m pytest -q
pause
''',
'ABRIR_RESULTADOS.bat':r'''@echo off
cd /d "%~dp0"
start "" "PREMONITION_LAB.html"
'''}
for name,text in files.items():
 (root/name).write_bytes(text.replace('\n','\r\n').encode('utf-8'))
