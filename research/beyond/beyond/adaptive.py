"""Slow causal region supervision and periodic/output-control combination.

Candidate, not a viability certificate. Triggers depend on temperature and
innovation history. Failed transitions and added resources are retained.
"""
import json
import numpy as np
import pandas as pd
from beyond.models import get_model
from beyond.control import EKF,FixedPolicy
from beyond.closedloop import scenario
from beyond.common import RESULTS,metrics,dump

def run():
    rows=[]
    for kind in ['PG','EB']:
        m=get_model(kind);n=round((4.5 if kind=='PG' else 10.)/m.dt)
        altx,altu=m.operating_point(1.,337.) if kind=='PG' else m.operating_point(.9,160.)
        period=(4 if kind=='PG' else 1)*m.tau
        for seed in range(69000,69012):
            p,rng=scenario(m,seed,'combined');p*=1.25;initial=m.x0.copy();initial[:4]*=np.exp(rng.normal(0,.12,4));noise=rng.normal(size=(n,len(m.yidx)))*m.noise
            for mode in ['nominal','fixed_alternative','adaptive','periodic_nominal','periodic_alternative']:
                x=initial.copy();est=EKF(m,m.x0);ctl=FixedPolicy(m,m.x0,m.u0,'direct',1 if kind=='PG' else .5)
                X=[x.copy()];U=[];Y=[];refs=[];target=[];alphas=[];nis=[];alpha=0.;goal=1. if 'alternative' in mode else 0.;quiet=0.;switches=0
                for j in range(n):
                    # Same scheduled perturbation, NOT observed by the controller.
                    pp=np.zeros_like(p) if j<n//4 or j>3*n//4 else p
                    y=x[m.yidx]+noise[j]
                    if j:est.cycle(U[-1],y)
                    nis.append(est.nis)
                    if mode=='adaptive':
                        score=np.mean(nis[-max(3,round(m.tau/m.dt)):])
                        new=goal
                        if score>4 or y[0]>m.tmax-3:new=1.
                        if score<1.5:quiet+=m.dt
                        else:quiet=0.
                        if quiet>2*m.tau and y[0]<m.tmax-5:new=0.
                        if new!=goal:switches+=1
                        goal=new
                    alpha+=np.clip(goal-alpha,-m.dt/(4*m.tau),m.dt/(4*m.tau))
                    uop=m.u0+alpha*(altu-m.u0);Tref=m.x0[4]+alpha*(altx[4]-m.x0[4]);qref=m.q0+alpha*(float(m.quality(altx))-m.q0)
                    if mode.startswith('periodic'):
                        uop[0]*=1+.025*np.sqrt(2)*np.sin(2*np.pi*j*m.dt/period)
                    u=ctl.act(y,est.x,est.P,reference=qref,thermal_target=Tref,uop=uop)
                    x=np.array(m.step(x,u,pp)).ravel();X.append(x.copy());U.append(u.copy());Y.append(y);refs.append(qref);target.append(Tref);alphas.append(alpha)
                X=np.array(X);U=np.array(U)
                Pactual=np.array([np.zeros_like(p) if j<n//4 or j>3*n//4 else p for j in range(n)])
                met=metrics(m,X,U,np.array(refs),plant_parameters=Pactual);met.update(kind=kind,strategy=mode,seed=seed,
                    normalized_IAE=met['IAE']/(n*m.dt*m.q0),switches=switches,alternative_time_fraction=float(np.mean(alphas)))
                rows.append(met);np.savez_compressed(RESULTS/f'adaptive_{kind}_{mode}_{seed}.npz',X=X,U=U,Y=Y,reference=refs,alpha=alphas,nis=nis,p=p)
            print(kind,seed,'supervision and combination complete',flush=True)
            pd.DataFrame(rows).to_csv(RESULTS/'adaptive.csv',index=False)
    dump(RESULTS/'adaptive_scope.json',dict(policy='fixed thermal PI; innovation-threshold supervisor with 4 residence-time ramps and hysteresis',
        tuning='Thresholds fixed before running these 12 paired scenarios; no tuning on test outcome',
        caveat='Costed, constrained transition evidence is local. Nominal and alternative references differ; resource and production tradeoffs must be reported.'))
if __name__=='__main__':run()
