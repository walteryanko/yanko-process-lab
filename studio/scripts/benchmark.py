"""A small matched-seed functional benchmark, not algorithm superiority research."""
import copy,json,statistics,time,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from processlab.scenarios import scenarios
from processlab.simulation import Simulation
from processlab.storage import atomic_json


def main():
    samples=[];base=scenarios()
    for controller in ['manual','pid']:
        for seed in [101,102,103,104,105]:
            p=copy.deepcopy(base[1]);p['experiment'].update(controller=controller,seed=seed)
            s=Simulation(p);r=s.run();samples.append({'scenario':'tank','controller':controller,'seed':seed,'status':r['status'],**r['metrics']})
    for i in [2,3]:
        for observer in ['ekf','ukf']:
            for seed in [201,202,203]:
                p=copy.deepcopy(base[i]);p['experiment'].update(observer=observer,seed=seed)
                r=Simulation(p).run();samples.append({'scenario':p['id'],'observer':observer,'seed':seed,'status':r['status'],**r['metrics']})
    nmpc=copy.deepcopy(base[4]);nmpc['experiment'].update(duration=200)
    r=Simulation(nmpc).run();samples.append({'scenario':'tank-nmpc','seed':nmpc['experiment']['seed'],'status':r['status'],**r['metrics'],'optimizer':r['controller']})
    summaries=[]
    for key in sorted({(r['scenario'],r.get('controller',r.get('observer','nmpc'))) for r in samples}):
        a=[r for r in samples if (r['scenario'],r.get('controller',r.get('observer','nmpc')))==key]
        summaries.append({'scenario':key[0],'method':key[1],'n':len(a),'failures':sum(r['status']!='completed' for r in a),'iae_mean':statistics.mean(r['iae'] for r in a),'quality_rmse_mean':statistics.mean(r['quality_rmse'] for r in a),'wall_seconds_mean':statistics.mean(r['wall_seconds'] for r in a),'temperature_violation_max':max(r['max_temperature_violation'] for r in a)})
    result={'protocol':'Matched definitions, same seeds across methods; 23 short validation trajectories. No training, tuning, or superiority claim. Runtime host != target laptop.','source_manifest':r['manifest'],'samples':samples,'summary':summaries}
    out=Path(__file__).resolve().parents[1]/'evidence'/'benchmark.json';atomic_json(out,result)
    print(json.dumps(summaries,indent=2))
    if any(r['status']!='completed' for r in samples):raise SystemExit('A scenario did not complete; inspect benchmark.json')


if __name__=='__main__':main()
