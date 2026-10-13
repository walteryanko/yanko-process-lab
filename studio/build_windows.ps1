$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
New-Item -ItemType Directory -Force studio/release | Out-Null
$commit = git rev-parse HEAD
@{commit=$commit; built_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -Encoding utf8 studio/build-info.json
# Python accepts the BOM only with utf-8-sig; write UTF-8 without a BOM for parity.
$buildInfo = @{commit=$commit; built_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $repo 'studio/build-info.json'), $buildInfo, [System.Text.UTF8Encoding]::new($false))
python studio/scripts/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name YCSProcessLab --distpath studio/dist --workpath studio/build --specpath studio/build --paths studio --collect-all webview --additional-hooks-dir studio/hooks --hidden-import scipy.special._cdflib --add-data 'studio/ui/dist;studio/ui/dist' --add-data 'studio/build-info.json;studio' --add-data 'research/beyond/vendor/pg_reference.py;research/beyond/vendor' --add-data 'research/beyond/vendor/eb_reference.py;research/beyond/vendor' --add-data 'LICENSE;.' --add-data 'studio/build/THIRD_PARTY_LICENSES;THIRD_PARTY_LICENSES' --add-data 'studio/docs;studio/docs' studio/desktop.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$nsis = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
if (!(Test-Path $nsis)) { throw 'NSIS is required for the installer' }
& $nsis /V3 studio/installer.nsi
if ($LASTEXITCODE -ne 0) { throw 'NSIS failed' }
Get-ChildItem studio/release/*.exe | ForEach-Object { "$((Get-FileHash $_ -Algorithm SHA256).Hash.ToLower())  $($_.Name)" } | Set-Content -Encoding ascii studio/release/SHA256SUMS.txt
Copy-Item studio/build-info.json studio/release/build-info.json
