"""Rebuild missing large demonstration data from the source-only Git branch."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from eblab.experiments import generate,run,write_json
from eblab.filters import FilterConfig,METHODS
from build_dashboard import build

if __name__=='__main__':
    out=ROOT/'results/primary';out.mkdir(parents=True,exist_ok=True)
    for sc in ['gaussian','weak_thermal']:
        ep=generate(2000,sc,60)
        for m in METHODS:
            file=out/f'demo_{sc}_{m}.json'
            if not file.exists():
                r,t=run(ep,m,FilterConfig(),True);write_json(file,dict(episode=ep,result=r,trace=t));print(sc,m,flush=True)
    from eblab import studies
    study=ROOT/'results/studies';study.mkdir(parents=True,exist_ok=True)
    for name,file in [('observability','observability.json'),('synthetic','synthetic_distributions.json'),('reference','posterior_reference.json')]:
        if not (study/file).exists():getattr(studies,name)(study)
    build()
