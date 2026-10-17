import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'MANIFEST_SHA256.json').read_text(encoding='utf-8'))
errors=[]
for rel,expected in manifest['files'].items():
 p=root/rel
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:errors.append(rel)
print(f"Checked {len(manifest['files'])} files; mismatches: {len(errors)}")
if errors:print('\n'.join(errors));raise SystemExit(1)
