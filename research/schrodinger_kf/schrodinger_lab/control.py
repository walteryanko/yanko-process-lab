"""Finite-candidate nonlinear MPC, adapted and audited from Multiverse v0.1.
Same plant, candidate schedules, actuator limits, stage cost and thermal limit.
Control effects are separated by holding M4 fixed for nominal/risk/regret.
"""
import itertools,argparse,time
from dataclasses import replace
from pathlib import Path
import numpy as np
from .model import *
from .filters import FilterConfig,make_filter
from .experiments import initial,write_json,serial
from .probability import weighted_quantile

LEVELS=np.array([250.,453.6,900.,1200.])
SCHEDULES=np.array(list(itertools.product(LEVELS,repeat=3)))
HORIZON=9

def stage(x,mw,prev):
    return ((x[...,4]-(BASE[4]-1))**2+4*(BASE[2]-x[...,2])**2
            +.018*((mw-U0[3])/450)**2+.05*((mw-prev)/450)**2+100*np.maximum(x[...,4]-STUDY_T,0)**2)

def evaluate(states,u,prev):
    xx=np.broadcast_to(states,(len(SCHEDULES),len(states),6)).copy()
    costs=np.zeros(xx.shape[:2]);peaks=xx[...,4].copy();last=np.full(xx.shape[:2],prev)
    for k in range(HORIZON):
        mw=np.broadcast_to(SCHEDULES[:,k//3,None],xx.shape[:2])
        uu=np.broadcast_to(u,xx.shape).copy();uu[...,3]=mw
        xx=step(xx,uu,max_step=.0025);peaks=np.maximum(peaks,xx[...,4])
        costs+=stage(xx,mw,last);last=mw
    return costs,peaks

def select_scenarios(particles,weights,n=9):
    # Deterministic CC-quantile stratification. Approximation, not the entire posterior.
    order=np.argsort(particles[:,2]);cdf=np.cumsum(weights[order]);q=(np.arange(n)+.5)/n
    idx=order[np.minimum(np.searchsorted(cdf,q),len(order)-1)]
    return particles[idx,:6]

def choose(mean,particles,weights,u,prev,policy='nominal'):
    fallback=0
    try:
        if policy=='nominal':states=mean[None,:6]
        else:states=select_scenarios(particles,weights)
        loss,peak=evaluate(states,u,prev)
        feasible=np.all(peak<=STUDY_T,axis=1)
        if policy=='nominal':score=loss[:,0]
        elif policy=='risk':
            # Upper third scenario loss (discrete CVaR approximation).
            score=np.sort(loss,axis=1)[:,-3:].mean(1)
        elif policy=='regret':score=np.max(loss-loss.min(axis=0),axis=1)
        else:raise ValueError('Unknown policy')
        if not np.any(feasible):raise ArithmeticError('No scenario-feasible schedule')
        i=int(np.argmin(np.where(feasible,score,np.inf)))
    except (ValueError,ArithmeticError,FloatingPointError):
        # Nominal policy verified on a finite grid, with thermal priority.
        fallback=1;loss,peak=evaluate(mean[None,:6],u,prev)
        feasible=peak[:,0]<=STUDY_T
        if np.any(feasible):i=int(np.argmin(np.where(feasible,loss[:,0],np.inf)))
        else:i=int(np.lexsort((loss[:,0],peak[:,0]))[0])
    return float(SCHEDULES[i,0]),dict(index=i,fallback=fallback,predicted_peak=float(np.max(peak[i])))

def experiment(trials=20,steps=32,out='results/control',bridge_steps=64):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[];traces=[]
    for seed in range(3000,3000+trials):
        rng=np.random.default_rng(seed);mean,cov=initial('ambiguous')
        x0=rng.multivariate_normal(mean,cov);noise=rng.normal(0,.35,(steps,2));process=rng.normal(size=(steps,6))*np.sqrt(Q_PUBLISHED)
        for method,policy in [('M0','nominal'),('M1','nominal'),('M4','nominal'),('M4','risk'),('M4','regret')]:
            cfg=FilterConfig(particles=128,bridge_steps=bridge_steps);f=make_filter(method,mean,cov,np.eye(2)*.35**2,cfg,seed+987654)
            x=x0.copy();m=mean.copy();prev=U0[3];hist=[];failure=None
            for k in range(steps):
                try:
                    particles,w,_=f.posterior(seed=seed+k)
                    u=U0.copy();u[4]+=3. # known feed-temperature perturbation for every controller
                    start=time.perf_counter();mw,diag=choose(m,particles,w,u,prev,policy);latency=time.perf_counter()-start
                    u[3]=mw;x=step(x,u)+process[k];check(x)
                    y=x[4:]+noise[k];m,p=f.advance(u,y)
                    hist.append(dict(k=k,x=x.tolist(),estimate=m.tolist(),y=y.tolist(),mw=mw,cost=float(stage(x,mw,prev)),
                                     thermal_violation=max(float(x[4]-STUDY_T),0),control_ms=1000*latency,**diag))
                    prev=mw
                    if x[4]>STOP_T:raise ArithmeticError('Thermal simulation stop')
                except Exception as exc:failure=dict(step=k,message=str(exc));break
            rows.append(dict(seed=seed,method=method,policy=policy,failure=failure,steps=len(hist),
                loss=sum(r['cost'] for r in hist),peak=max([r['x'][4] for r in hist],default=float('nan')),
                rmse_cc=float(np.sqrt(np.mean([(r['x'][2]-r['estimate'][2])**2 for r in hist]))) if hist else None,
                violations=sum(r['thermal_violation']>0 for r in hist),fallbacks=sum(r['fallback'] for r in hist),
                coolant_kmol=sum(r['mw']*DT for r in hist),control_ms=float(np.mean([r['control_ms'] for r in hist])) if hist else None))
            if seed==3000:traces.append(dict(method=method,policy=policy,seed=seed,history=hist))
        print('control',seed,flush=True)
    groups={};rng=np.random.default_rng(19)
    refs={r['seed']:r['loss'] for r in rows if r['method']=='M0' and r['policy']=='nominal' and not r['failure']}
    m4refs={r['seed']:r['loss'] for r in rows if r['method']=='M4' and r['policy']=='nominal' and not r['failure']}
    for method,policy in [(r['method'],r['policy']) for r in rows[:5]]:
        rs=[r for r in rows if r['method']==method and r['policy']==policy and not r['failure']]
        z={k:float(np.mean([r[k] for r in rs])) for k in ['loss','peak','rmse_cc','violations','fallbacks','coolant_kmol','control_ms']}
        z['n']=len(rs)
        for name,reference in [('vs_UKF_nominal',refs),('vs_M4_nominal',m4refs)]:
            d=np.array([r['loss']-reference[r['seed']] for r in rs if r['seed'] in reference])
            z[name]=dict(mean_delta=float(d.mean()),ci95=np.quantile(rng.choice(d,(2000,len(d))).mean(1),[.025,.975]).tolist())
        groups[method+'_'+policy]=z
    write_json(out/'control.json',dict(rows=rows,summary=groups,traces=traces,horizon=HORIZON,
              schedules=SCHEDULES,steps=steps,paired='Identical initial state and sensor/process noise; policy-dependent closed-loop plant trajectories',
              limitation='Finite candidate NMPC, 9-step horizon; no global optimum, no hardware; 9 CC-quantile scenarios.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trials',type=int,default=20);p.add_argument('--steps',type=int,default=32)
    p.add_argument('--out',default='results/control');p.add_argument('--bridge-steps',type=int,default=64);a=p.parse_args()
    experiment(a.trials,a.steps,a.out,a.bridge_steps)
