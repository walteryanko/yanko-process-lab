"""Follow-up isolating operating region while preserving EXACT quality target.

Introduced after discovering that arbitrary region comparisons change the target.
Uses fresh seeds 70000..70011, not the preceding holdout. Feed and production
changes are measured, never counted as free gains.
"""
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from beyond.models import get_model
from beyond.closedloop import simulate
from beyond.common import RESULTS,dump,paired_ci

def point(m,T):
    candidates=[]
    for f in np.linspace(.65,1.35,121):
        try:x,u=m.operating_point(f,T)
        except ValueError:continue
        if m.feasible(x,u):candidates.append((f,float(m.quality(x))-m.q0))
    roots=[]
    for (a,va),(b,vb) in zip(candidates[:-1],candidates[1:]):
        if va*vb<=0:
            fr=brentq(lambda r:float(m.quality(m.operating_point(r,T)[0]))-m.q0,a,b,xtol=1e-12)
            roots.append(fr)
    if not roots:raise ValueError('No target-preserving point found')
    return m.operating_point(min(roots,key=lambda r:abs(r-1)),T)

def run():
    rows=[];points={}
    for kind in ['PG','EB']:
        m=get_model(kind);reg={'iso_nominal':dict(x=m.x0,u=m.u0,name='iso_nominal')}
        for T in [337.,340.] if kind=='PG' else [158.,162.]:
            x,u=point(m,T);name=f'isoref_{int(T)}';reg[name]=dict(x=x,u=u,name=name)
        points[kind]=reg
        for name,pt in reg.items():
            for case in ['kinetic','combined','ood']:
                for seed in range(70000,70012):
                    r=simulate(kind,pt,'direct',seed,case,1. if kind=='PG' else .5,save=True)
                    r.update(region=name,quality_target=float(m.quality(pt['x'])),feed_ratio=pt['u'][0]/m.u0[0]);rows.append(r)
            print(kind,name,'same-quality followup complete',flush=True)
            pd.DataFrame(rows).to_csv(RESULTS/'same_quality.csv',index=False)
    dump(RESULTS/'same_quality_points.json',points);contrasts=[]
    data=pd.DataFrame(rows)
    for kind,a in data.groupby('kind'):
        for metric in ['normalized_IAE','production_mean','feed_mean','heat_mean','violation_steps']:
            p=a.groupby(['seed','region'])[metric].mean().unstack()
            for name in p.columns.drop('iso_nominal'):contrasts.append(dict(kind=kind,region=name,metric=metric,**paired_ci(p[name],p.iso_nominal)))
    pd.DataFrame(contrasts).to_csv(RESULTS/'same_quality_contrasts.csv',index=False)
if __name__=='__main__':run()
