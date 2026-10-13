$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo
New-Item -ItemType Directory -Force studio/release | Out-Null
$commit = git rev-parse HEAD
# Python accepts the BOM only with utf-8-sig; write UTF-8 without a BOM for parity.
$buildInfo = @{commit=$commit; built_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $repo 'studio/build-info.json'), $buildInfo, [System.Text.UTF8Encoding]::new($false))
python studio/scripts/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
# Data source paths are resolved relative to the generated spec, not the shell.
# Absolute sources keep --specpath studio/build independent of the working directory.
$bundleArgs = @(
  '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
  '--name', 'YCSProcessLab', '--distpath', (Join-Path $repo 'studio/dist'),
  '--workpath', (Join-Path $repo 'studio/build'), '--specpath', (Join-Path $repo 'studio/build'),
  '--paths', (Join-Path $repo 'studio'), '--collect-all', 'webview',
  '--additional-hooks-dir', (Join-Path $repo 'studio/hooks'),
  '--hidden-import', 'scipy.special._cdflib', '--hidden-import', 'casadi',
  '--copy-metadata', 'numpy', '--copy-metadata', 'scipy', '--copy-metadata', 'pint'
)
$dataFiles = @(
  @('studio/ui/dist', 'studio/ui/dist'),
  @('studio/build-info.json', 'studio'),
  @('studio/processlab/*.py', 'studio/processlab'),
  @('research/beyond/vendor/pg_reference.py', 'research/beyond/vendor'),
  @('research/beyond/vendor/eb_reference.py', 'research/beyond/vendor'),
  @('LICENSE', '.'),
  @('studio/build/THIRD_PARTY_LICENSES', 'THIRD_PARTY_LICENSES'),
  @('studio/docs', 'studio/docs')
)
foreach ($item in $dataFiles) {
  $bundleArgs += @('--add-data', "$(Join-Path $repo $item[0]);$($item[1])")
}
$bundleArgs += (Join-Path $repo 'studio/desktop.py')
& python @bundleArgs
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
$nsis = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
if (!(Test-Path $nsis)) { throw 'NSIS is required for the installer' }
& $nsis /V3 studio/installer.nsi
if ($LASTEXITCODE -ne 0) { throw 'NSIS failed' }
Get-ChildItem studio/release/*.exe | ForEach-Object { "$((Get-FileHash $_ -Algorithm SHA256).Hash.ToLower())  $($_.Name)" } | Set-Content -Encoding ascii studio/release/SHA256SUMS.txt
Copy-Item studio/build-info.json studio/release/build-info.json
