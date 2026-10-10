"""Independent continuous integration of saved applied-input trajectories."""
import argparse
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from beyond.models import get_model
from beyond.common import RESULTS,dump

def validate_file(path,kind):
    m=get_model(kind);raw=np.load(path);X=raw['X'];U=raw['U'];p=raw['p'] if 'p' in raw else m.p0
    state=X[0].copy();fine=[state.copy()];end=[state.copy()]
    for u in U:
        sol=solve_ivp(lambda t,x:np.array(m.f(x,u,p)).ravel(),[0,m.dt],state,method='DOP853',rtol=2e-10,atol=2e-11,dense_output=True)
        if not sol.success:raise RuntimeError(sol.message)
        fine.extend(sol.sol(np.linspace(0,m.dt,5)[1:]).T);state=sol.y[:,-1];end.append(state.copy())
    fine=np.array(fine);end=np.array(end);error=np.abs(end-X)
    return dict(file=path.name,kind=kind,method='DOP853, independent of the RK4 plant integrator',
        temperature_max_difference=float(error[:,4].max()),quality_max_difference=float(abs(m.quality(end)-m.quality(X)).max()),
        recorded_Tmax=float(X[:,4].max()),fine_Tmax=float(fine[:,4].max()),fine_Tmin=float(fine[:,4].min()),
        fine_violation=bool(np.any((fine[:,4]>m.tmax+1e-7)|(fine[:,4]<m.tmin-1e-7))),samples=len(U),
        max_scaled_state_error=float(np.max(error/np.maximum(abs(m.x0),1))))

def run():
    rows=[]
    for kind in ['PG','EB']:
        df=pd.read_csv(RESULTS/f'closedloop_{kind}.csv')
        subset=df[(df['mode']=='direct')&(~df.transition)]
        for region in ['nominal','fixed_feed_340K'] if kind=='PG' else ['nominal','O2_robust']:
            a=subset[subset.region==region]
            for _,r in a.nlargest(2,'Tmax').iterrows():
                path=RESULTS/f'closed_{kind}_{region}_direct_{r["case"]}_{int(r.seed)}.npz'
                rows.append(validate_file(path,kind))
        periodic=pd.read_csv(RESULTS/'periodic.csv');a=periodic[(periodic.kind==kind)&periodic.valid]
        for _,r in a.nlargest(1,'gain_vs_stationary_percent').iterrows():rows.append(validate_file(RESULTS/f'periodic_{kind}_{int(r["index"])}.npz',kind))
    pd.DataFrame(rows).to_csv(RESULTS/'independent_integration.csv',index=False)
    dump(RESULTS/'independent_integration_verdict.json',dict(files=len(rows),
        maximum_temperature_discrepancy=max(r['temperature_max_difference'] for r in rows),
        maximum_scaled_state_error=max(r['max_scaled_state_error'] for r in rows),
        scope='Selected worst-case saved input trajectories and best periodic candidates; no online controller rerun and no proof for unsampled time extrema'))
if __name__=='__main__':run()
