"""Collect installed license text; fail if the scientific dependency metadata is missing."""
import importlib.metadata as md
from pathlib import Path
import json,shutil

root=Path(__file__).resolve().parents[1]
out=root/'build'/'THIRD_PARTY_LICENSES';out.mkdir(parents=True,exist_ok=True)
inventory=[]
for name in ['numpy','scipy','pint','casadi','pywebview','pythonnet','clr-loader','bottle','proxy-tools','flexcache','flexparser','platformdirs','typing_extensions','cffi','pycparser']:
    dist=md.distribution(name);files=[]
    for entry in dist.files or []:
        if any(s in str(entry).lower() for s in ['license','copying','notice']):
            src=Path(dist.locate_file(entry))
            if src.is_file():
                dest=out/name/str(entry);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest);files.append(str(dest.relative_to(out)))
    inventory.append({'name':name,'version':dist.version,'license':str(dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'see package'),'license_files':files})
for license in (root/'ui'/'node_modules').rglob('*'):
    if license.is_file() and license.name.lower().startswith(('license','copying','notice')):
        dest=out/'npm'/license.relative_to(root/'ui'/'node_modules');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(license,dest)
(out/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
shutil.copyfile(root.parent/'LICENSE',out/'PROCESSLAB_LICENSE.txt')
print(f'Collected {len(inventory)} Python dependency license records plus npm notices')
