"""Add the Figure 28 steady-state case, preserving the initial protocol audit."""
import sys,json,csv,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from darwin.thesis_experiments import *

if __name__=='__main__':
    protocol=json.loads((OUT/'protocol.json').read_text())
    if any(s['key']=='OL_STEADY' for s in protocol['scenarios']):
        raise SystemExit('Steady-state scenario is already present; no duplicate run.')
    savejson(OUT/'protocol_initial_18_cases.json',protocol)
    s=BY_KEY['OL_STEADY'];n=protocol['n'];i=SCENARIOS.index(s)
    savejson(OUT/'protocol_addendum.json',dict(created_before_added_runs=True,scenario=s.as_dict(),n=n,
        reason='Figure 28 steady-state observer experiment explicitly added after checking the page; no tuning changed.',
        seeds=[410000+i*1000+j for j in range(n)]))
    d=json.loads((OUT/'discovery.json').read_text());start=time.perf_counter()
    added=[rollout(s.key,m,False,410000+i*1000+j,d) for m in METHODS for j in range(n)]
    rows=list(csv.DictReader((OUT/'metrics.csv').open()))+added
    rows.sort(key=lambda r:(r['scenario'],r['thermal'],r['method'],int(r['seed'])))
    savecsv(OUT/'metrics.csv',rows)
    protocol['scenarios'].append(s.as_dict());protocol['addendum']='protocol_addendum.json'
    savejson(OUT/'protocol.json',protocol)
    ex=json.loads((OUT/'execution.json').read_text());ex['tasks']+=len(added);ex['completed']+=len(added)
    ex['addendum_seconds']=time.perf_counter()-start;savejson(OUT/'execution.json',ex)
    summarize();print(json.dumps(ex))
