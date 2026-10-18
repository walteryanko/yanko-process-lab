"""Build a self-contained source/data release; exclude caches and local environments."""
from pathlib import Path
import argparse,hashlib,json,zipfile,subprocess

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.venv','__pycache__','.pytest_cache','results_reproduced','reports_results_reproduced','node_modules'}

def files():
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if not p.is_file() or set(rel.parts)&EXCLUDED:continue
        if any(s.startswith('pilot') for s in rel.parts):continue
        if p.suffix in {'.pyc','.nbc','.nbi','.tmp','.zip'}:continue
        if p.name in {'MANIFEST.sha256','tests_initial.log'}:continue
        yield p

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    paths=list(files());manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in paths)
    (ROOT/'MANIFEST.sha256').write_text(manifest,encoding='utf-8')
    out=Path(args.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except (OSError,subprocess.SubprocessError):commit=None
    prefix='YCS_Premonition_MPC_Lab_v1.0/'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in paths+[ROOT/'MANIFEST.sha256']:z.write(p,prefix+p.relative_to(ROOT).as_posix())
        z.writestr(prefix+'RELEASE.json',json.dumps({'version':'1.0.0','source_commit':commit,'source_branch':'research/premonition-mpc-v1-20261018','files':len(paths),'simulation_only':True},indent=2))
    with zipfile.ZipFile(out) as z:
        error=z.testzip()
        if error:raise RuntimeError('Archive CRC failure: '+error)
        for line in manifest.splitlines():
            digest,name=line.split('  ',1)
            if hashlib.sha256(z.read(prefix+name)).hexdigest()!=digest:raise RuntimeError('Manifest mismatch: '+name)
    print(json.dumps({'zip':str(out),'bytes':out.stat().st_size,'files':len(paths)+2,'manifest_verified':True,'source_commit':commit}))

if __name__=='__main__':main()
