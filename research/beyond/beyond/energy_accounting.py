"""Recompute evaluated heat from stored true plant parameters, never for control.

This migrates early reporting that evaluated nominal duty at the true X/U.
No state, input, estimate, tracking metric, selection or seed is changed.
Fresh experiments now call metrics(..., plant_parameters=p) directly.
"""
import json,shutil
import numpy as np
import pandas as pd
from beyond.models import get_model
from beyond.common import RESULTS,dump,paired_ci

def run():
    archive=RESULTS/'pilot_v0'/'nominal_heat_reporting';archive.mkdir(parents=True,exist_ok=True)
    count=0
    for filename in ['closedloop_PG','closedloop_EB','same_quality','baselines_PG','baselines_EB','sampling_control','adaptive','identification']:
        path=RESULTS/(filename+'.csv');d=pd.read_csv(path)
        if not (archive/path.name).exists():shutil.copy2(path,archive/path.name)
        for i,r in d.iterrows():
            k=r.kind;s=int(r.seed)
            if filename.startswith('closedloop') or filename=='same_quality':name=f'closed_{k}_{r.region}_{r["mode"]}_{r["case"]}_{s}'
            elif filename.startswith('baselines'):name=f'baseline_{k}_{r.region}_{r.baseline}_{r["case"]}_{s}'
            elif filename=='sampling_control':name=f'sampling_{k}_{r.strategy}_{r.delay_tau}_{s}'
            elif filename=='adaptive':name=f'adaptive_{k}_{r.strategy}_{s}'
            else:name=f'identification_{k}_{r.wave}_{s}'
            z=np.load(RESULTS/(name+'.npz'));m=get_model(k);X=z['X'][1:];U=z['U'];p=z['p'];n=len(U)
            P=np.tile(p,(n,1))
            if filename=='adaptive':
                P[:n//4]=0;P[3*n//4+1:]=0
            heat=np.array([m.duty(x,u,pp) for x,u,pp in zip(X,U,P)])
            if filename=='identification':d.loc[i,'probe_heat']=heat.sum()*m.dt
            else:d.loc[i,'heat_mean']=heat.mean();d.loc[i,'heat_total']=heat.sum()*m.dt
            count+=1
        d.to_csv(path,index=False)
    d=pd.read_csv(RESULTS/'same_quality.csv');rows=[]
    for kind,a in d.groupby('kind'):
        for metric in ['normalized_IAE','production_mean','feed_mean','heat_mean','violation_steps']:
            p=a.groupby(['seed','region'])[metric].mean().unstack()
            for region in p.columns.drop('iso_nominal'):
                rows.append(dict(kind=kind,region=region,metric=metric,**paired_ci(p[region],p.iso_nominal)))
    pd.DataFrame(rows).to_csv(RESULTS/'same_quality_contrasts.csv',index=False)
    dump(RESULTS/'energy_accounting.json',dict(recomputed_rows=count,
        change='Heat evaluated using stored true plant parameters, including the documented supervisor parameter schedule. Early nominal-parameter heat summaries excluded.',
        invariant='All X/U/control/quality/production/violations unchanged; no true parameters exposed to any controller.'))
if __name__=='__main__':run()
