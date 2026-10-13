# Dependency and redistribution inventory

First-party code: MIT, copyright Walter Yanko / Yanko Creative Studio, as scoped by
the repository's LICENSE and LICENSE_SCOPE.md. No DWSIM, Aspen, MATLAB or other
proprietary simulator source was copied. The AIRE scientific archive is not included.
UI graphics are code-authored SVGs and Lucide icons, not proprietary simulator assets.

| Dependency | Version pin | License / distribution notes |
|---|---|---|
| React / React DOM | 19.2.0 | MIT |
| React Flow | 12.10.0 | MIT; attribution retained |
| Lucide React | 0.468.0 | ISC |
| TypeScript / Vite / React plugin | lockfile | Apache-2.0 / MIT; build tools |
| Python | 3.12 | PSF; bundled interpreter, not a separately required installation |
| NumPy | 2.3.5 | BSD-3-Clause, bundled BLAS licenses retained |
| SciPy | 1.17.0 | BSD-3-Clause, bundled numerical-library licenses retained |
| Pint | 0.25 | BSD-3-Clause |
| CasADi | 3.7.2 | LGPL-3.0-or-later; dynamically loaded, unmodified symbolic core |
| pywebview | 6.1 | BSD-3-Clause |
| pythonnet / clr-loader | 3.0.5 / 0.2.7.post0 | MIT |
| bottle / proxy-tools | 0.13.4 / 0.1.0 | MIT / BSD |
| PyInstaller | 6.16.0 | GPL-2.0-or-later with bootloader distribution exception; build tool |
| NSIS | runner tool | zlib/libpng-style license; installer generator |
| Playwright | 1.56.1 | Apache-2.0; development tests only |
| WebView2 | system prerequisite | Microsoft runtime; not redistributed by this installer |

LGPL review: ProcessLab does not modify, statically link, or relicense CasADi.
The application is distributed as an unpacked directory containing replaceable
shared libraries inside `_internal/casadi`. The source and license for the exact
CasADi release are https://github.com/casadi/casadi/tree/3.7.2 and its LICENSE.txt.
Users retain the LGPL rights to replace that library and reverse engineer changes
for debugging such replacements. The complete first-party application source and
build instructions accompany the artifact. CasADi's own notices are collected.

The custom PyInstaller hook includes the symbolic core and required compiler runtime
DLLs only. Optional solver plugins (including proprietary solver interfaces) are
excluded. No GPLv3 simulator is incorporated. Windows binary dependency resolution
still requires verification by the Windows workflow before redistribution is complete.

Build scripts generate `THIRD_PARTY_LICENSES` from actual installed metadata and
the npm dependency tree. Dependency versions are recorded in the Windows artifact.
Version pins are reproducible constraints, not claims that every package is latest.
