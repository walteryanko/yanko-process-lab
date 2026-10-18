import json,csv,hashlib
from pathlib import Path
import numpy as np

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,(np.integer,np.bool_)):return x.item()
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    if isinstance(x,complex):return {'real':x.real,'imag':x.imag}
    return x

def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(clean(data),ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def csv_write(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows([{k:json.dumps(clean(v)) if isinstance(v,(dict,list,np.ndarray)) else v for k,v in r.items()} for r in rows])

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
