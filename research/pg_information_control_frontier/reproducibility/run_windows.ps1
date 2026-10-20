$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r reproducibility\document_requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
New-Item -ItemType Directory -Force -Path results | Out-Null
$ErrorActionPreference = "Continue"
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath results\tests.log
$testExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($testExit -ne 0) { throw "Scientific tests failed; inspect results\tests.log" }
& .\.venv\Scripts\python.exe src\experiments.py
if ($LASTEXITCODE -ne 0) { throw "Scientific execution failed" }
if (!(Get-Command pandoc -ErrorAction SilentlyContinue) -or !(Get-Command pdflatex -ErrorAction SilentlyContinue)) {
    Write-Warning "Simulation data saved. Install Pandoc and MiKTeX before compiling manuscripts."
    exit 0
}
& .\.venv\Scripts\python.exe src\reporting.py
if ($LASTEXITCODE -ne 0) { throw "Document audit/build failed" }
