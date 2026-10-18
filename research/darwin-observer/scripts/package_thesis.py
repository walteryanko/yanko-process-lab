"""Pack the executed thesis comparison with verified, per-file SHA256 hashes."""
import argparse,hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def include(path):
    parts=path.relative_to(ROOT).parts;rel='/'.join(parts)
    if any(x in {'__pycache__','.pytest_cache','.venv','.git'} for x in parts):return False
    if path.name in {'MANIFEST_SHA256.json','metrics_partial.csv','pilot_metrics.csv'}:return False
    if path.suffix in {'.zip','.pyc','.nbc','.nbi','.so','.dll'}:return False
    if path.suffix=='.log' and path.name!='all_tests.log':return False
    if rel.startswith(('artifacts/export_repair/','artifacts/thesis/compiled/','artifacts/main/datasets/')):return False
    return True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args()
    out=Path(args.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and include(p)]
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    text=json.dumps(dict(version='1.1.0-thesis',files=manifest),indent=2,ensure_ascii=False)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'Darwin_Dissertacao/'+str(p.relative_to(ROOT)))
        z.writestr('Darwin_Dissertacao/MANIFEST_SHA256.json',text)
    with zipfile.ZipFile(out) as z:
        for rel,expected in manifest.items():
            if hashlib.sha256(z.read('Darwin_Dissertacao/'+rel)).hexdigest()!=expected:raise RuntimeError('Mismatch: '+rel)
        if z.testzip() is not None:raise RuntimeError('ZIP CRC failure')
    info=dict(path=str(out),files=len(files)+1,size_bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),verification='Every archive member SHA256 and ZIP CRC verified.')
    out.with_suffix('.json').write_text(json.dumps(info,indent=2))
    print(json.dumps(info))

if __name__=='__main__':main()
