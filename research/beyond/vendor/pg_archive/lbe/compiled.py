import os,json,hashlib
import casadi as ca
from lbe.config import ROOT

def maybe_compiled(f,label):
    manifest=ROOT/'compiled/manifest.json';binary=ROOT/f'compiled/{label}.so'
    if os.environ.get('LBE_NO_COMPILED')=='1' or not manifest.exists() or not binary.exists():return f
    meta=json.loads(manifest.read_text())
    if meta.get(label)!=hashlib.sha256(f.serialize().encode()).hexdigest():return f
    return ca.external(f.name(),str(binary))
