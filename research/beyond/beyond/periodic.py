"""Resource-accounted periodic operation, compared with stationary grid optimum.

All candidates start from the nominal equilibrium. Final cycles test a limit
cycle, while the complete startup path is audited separately. Stationary
comparators use no MORE average feed, coolant flow and removed heat. Flow
RMS (pump proxy) and actuator total variation are separately reported.
"""
import time
import numpy as np
import pandas as pd
from beyond.models import get_model
from beyond.common import RESULTS,dump,metrics,slew_limit
from beyond.spectra import waveform,information

def stationary_candidates(m):
    rows=[]
    for fr in np.linspace(.65,1.35,55):
        for T in np.linspace(315,m.tmax-.01,65) if m.kind=='PG' else np.linspace(141,164.99,65):
            try:x,u=m.operating_point(fr,T)
            except ValueError:continue
            if not m.feasible(x,u):continue
            if max(np.linalg.eigvals(np.array(m.fx(x,u,m.p0))).real)>=0:continue
            prod=m.production(x,u);by=0 if m.kind=='PG' else sum(u[:3])*x[3]
            rows.append(dict(feed=u[0],cool=u[m.cidx],heat=m.duty(x,u),production=prod,
                byproduct=by,temperature=T,quality=float(m.quality(x)),selectivity=1 if m.kind=='PG' else prod/(prod+by)))
    # Include exact nominal, avoiding grid bias against the known baseline.
    rows.append(dict(feed=m.u0[0],cool=m.u0[m.cidx],heat=m.duty0,production=m.prod0,
       byproduct=0 if m.kind=='PG' else sum(m.u0[:3])*m.x0[3],temperature=m.x0[4],quality=m.q0,
       selectivity=1 if m.kind=='PG' else m.prod0/(m.prod0+sum(m.u0[:3])*m.x0[3])))
    return pd.DataFrame(rows)

def run():
    rows=[];start=time.perf_counter()
    for kind in ['PG','EB']:
        m=get_model(kind);ss=stationary_candidates(m);ss.to_csv(RESULTS/f'stationary_{kind}.csv',index=False)
        cases=[]
        for per in [.5,1,2,4,8]:
            for amp in [.025,.05,.10]:
                for phase in [0,np.pi/2,np.pi,3*np.pi/2]:cases.append(('sin',per,amp,phase,.5))
        for per in [1,2,4]:
            for duty in [.25,.5,.75]:cases.append(('square',per,.05,np.pi/2,duty))
        for per in [1,2,4]:cases.append(('multisine',per,.05,np.pi/2,.5))
        for j,(wave,pertau,amp,phase,duty) in enumerate(cases):
            nper=max(8,round(pertau*m.tau/m.dt));period=nper*m.dt;nburn=max(4,int(np.ceil(8*m.tau/period)))
            n=(nburn+4)*nper;t=np.arange(n)*m.dt
            w=waveform(t,wave,period);w2=waveform(t,wave,period,phase=phase)
            if wave=='square' and duty!=.5:
                w=np.tanh(6*(np.cos(2*np.pi*t/period)-np.cos(np.pi*duty)));w-=w.mean();w/=np.sqrt(np.mean(w*w))
            U=np.tile(m.u0,(n,1));U[:,0]*=1+amp*w;U[:,m.cidx]*=1+amp*w2
            U=slew_limit(m,U)
            cycle=U[-nper:].copy()
            # Actuator slew clipping can shift the signal's mean. Recenter the
            # admissible cycle, then reapply startup slew. Resource parity is
            # tested on ACTUAL inputs, never inferred from sine coefficients.
            cycle[:,m.controls]+=m.u0[m.controls]-cycle[:,m.controls].mean(axis=0)
            U=slew_limit(m,np.tile(cycle,(nburn+4,1)));X=m.rollout(m.x0,U)
            if not np.all(np.isfinite(X)):
                rows.append(dict(kind=kind,index=j,wave=wave,period_tau=pertau,amp=amp,phase=phase,valid=False,reason='nonfinite'));continue
            b=nburn*nper;met=metrics(m,X[b:],U[b:]);metall=metrics(m,X,U)
            periodic_error=float(np.max(np.abs(X[-1]-X[-1-nper])/np.maximum(abs(m.x0),1.)))
            mean_error=float(max(abs(U[b:,m.controls].mean(axis=0)/m.u0[m.controls]-1)))
            valid=metall['violation_steps']==0 and metall['min_concentration']>=-1e-8 and periodic_error<1e-5 and mean_error<1e-5
            resource_tol=1e-5
            feasible_ss=ss[(ss.feed<=met['feed_mean']*(1+resource_tol)) &
               (ss.cool<=met['cooling_mean']*(1+resource_tol)) & (ss.heat<=met['heat_mean']*(1+resource_tol))]
            best=float(feasible_ss.production.max()) if len(feasible_ss) else np.nan
            row=dict(kind=kind,index=j,wave=wave,period_tau=pertau,period=period,amp=amp,phase=phase,duty_cycle=duty,
                valid=valid,periodic_residual=periodic_error,resource_mean_error=mean_error,burn_hours=b*m.dt,evaluated_hours=(n-b)*m.dt,
                full_Tmax=metall['Tmax'],full_Tmin=metall['Tmin'],full_violations=metall['violation_steps'],
                gain_vs_nominal_percent=100*(met['production_mean']/m.prod0-1),best_stationary_resource_matched=best,
                gain_vs_stationary_percent=100*(met['production_mean']/best-1) if np.isfinite(best) else np.nan,
                heat_change_vs_nominal_percent=100*(met['heat_mean']/m.duty0-1),
                feed_change_vs_nominal_percent=100*(met['feed_mean']/m.u0[0]-1),
                cooling_change_vs_nominal_percent=100*(met['cooling_mean']/m.u0[m.cidx]-1))
            row.update(met);rows.append(row)
            np.savez_compressed(RESULTS/f'periodic_{kind}_{j}.npz',X=X,U=U,burn=b,nper=nper)
        print(kind,'periodic',len(cases),'cases',flush=True)
    pd.DataFrame(rows).to_csv(RESULTS/'periodic.csv',index=False)
    dump(RESULTS/'periodic_runtime.json',{'seconds':time.perf_counter()-start})
if __name__=='__main__':run()
