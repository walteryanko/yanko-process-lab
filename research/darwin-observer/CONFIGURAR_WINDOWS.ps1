$env:PYTHONUTF8 = "1"
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (!(Test-Path ".venv\Scripts\python.exe")) {
    py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Instale Python 3.11 ou superior e tente novamente." }
}
& ".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ necessario'"
if ($LASTEXITCODE -ne 0) { throw "Versao de Python incompatível." }
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias. Confira a conexao e tente novamente." }
Write-Host "Pronto. Abra INICIAR_LAB.bat. O primeiro uso compila os kernels de CPU."
