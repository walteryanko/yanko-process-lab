# Windows validation — ProcessLab Studio 0.2.0

Built code: `3acc74b525cfd9e8bcfd00ce860e2478bea8a451`.

[Windows workflow](https://github.com/walteryanko/yanko-process-lab/actions/runs/38439420645)
completed successfully, as did the independent Verify workflow (38439420728).

- 35 Python tests and 11 TypeScript tests passed on the Windows runner.
- All five scientific scenarios ran in the frozen executable.
- The frozen laboratory completed comparison and tuning jobs (including holdout validation).
- The actual NSIS installer completed a silent per-user installation.
- The installed native WebView2 interface rendered, opened Laboratory and displayed F1 Help.
- 18 separate browser checks passed locally, including cancellation, CSV export,
  comparison, PID recommendation/application, searchable help and tutorial navigation.

Installer: `YCS-ProcessLab-Studio-0.2.0-Setup.exe`, 41,146,924 bytes.

SHA-256:
`33720fcde46ef9018e7a5452896760a75dcb6b1684d79438ba38236ae0c4ed28`

Original evidence is preserved in `studio/evidence/windows-ci-0.2.0`, including
Windows host/dependencies, test output, frozen/native smoke reports, bundled DLL
hashes, build commit and installer hash. Earlier 0.1.0 evidence remains in its
original directory. Later evidence/documentation commits do not change this binary.

The runner was Windows Server 2022. This does not measure performance on the user's
Windows 10 / Core i5-7200U / 8 GB machine. WebView2/.NET remain prerequisites, and the
installer has no commercial code-signing certificate.
