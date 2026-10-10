import json,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def native(o):
 if isinstance(o,np.ndarray):return o.tolist()
 if isinstance(o,(np.floating,np.integer,np.bool_)):return o.item()
 if isinstance(o,complex):return dict(real=o.real,imag=o.imag)
 if isinstance(o,Path):return str(o)
 raise TypeError(type(o))
def save(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,default=native,indent=2,ensure_ascii=False))
