"""Only the CasADi symbolic core is needed by the archived EB equations.

Do not bundle unrelated/proprietary solver interfaces or their plugin libraries.
"""
from pathlib import Path
from PyInstaller.utils.hooks import collect_dynamic_libs,collect_data_files,copy_metadata

core={"libcasadi.dll","libgcc_s_seh-1.dll","libstdc++-6.dll","libwinpthread-1.dll"}
binaries=[(src,dst) for src,dst in collect_dynamic_libs("casadi") if Path(src).name in core]
datas=collect_data_files("casadi",includes=["include/licenses/casadi/**/*"])+copy_metadata("casadi")
hiddenimports=["casadi._casadi"]
