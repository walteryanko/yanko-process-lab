"""Operating-region intervention with frozen causal policies and paired seeds."""
import json,time,argparse
import numpy as np
import pandas as pd
from beyond.models import get_model
from beyond.control import EKF,FixedPolicy
from beyond.common import RESULTS,dump,metrics,paired_ci

def scenario(m,seed,case):
    rng=np.random.default_rng(seed);p=np.zeros(m.np)
    if case in ['kinetic','combined','ood']:
        if m.kind=='PG':p[0]=rng.uniform(-.25,.25);p[1]=rng.uniform(-1,1)
        else:p[:3]=rng.uniform(-.25,.25,3);p[3:6]=rng.uniform(-1,1,3)
    if case in ['thermal','combined','ood']:
        if m.kind=='PG':p[2]=rng.uniform(-.2,.2);p[3]=rng.uniform(-.08,.08)
        else:p[6]=rng.uniform(-.08,.08);p[7]=rng.uniform(-.025,.025)
    if case=='ood':p*=1.6
    return p,rng

def simulate(kind,point,mode,seed,case,gain=1.,horizon=None,save=False,transition=False):
    m=get_model(kind);xop=np.array(point['x']);uop=np.array(point['u']);p,rng=scenario(m,seed,case)
    horizon=(3.0 if kind=='PG' else 8.) if horizon is None else horizon;n=round(horizon/m.dt)
    # Same relative inventory uncertainty and exactly paired sensor innovations.
    initial=rng.normal(0,.12,4);noise=rng.normal(size=(n,len(m.yidx)))*m.noise
    x=(m.x0 if transition else xop).copy();x[:4]*=np.exp(initial)
    if case=='ood':x[:4]*=np.exp(initial)
    prior=(m.x0 if transition else xop).copy();est=EKF(m,prior)
    ctl=FixedPolicy(m,prior,m.u0 if transition else uop,mode,gain)
    U=[];X=[x.copy()];E=[prior.copy()];Y=[];refs=[];elapsed=[];previous_y=prior[m.yidx]
    for i in range(n):
        frac=min(1.,i*m.dt/(4*m.tau)) if transition else 1.
        opu=m.u0+frac*(uop-m.u0);Tref=m.x0[4]+frac*(xop[4]-m.x0[4]);ref=m.q0+frac*(float(m.quality(xop))-m.q0)
        y=x[m.yidx]+noise[i]
        if case=='sensor' and i>n//3:y+=m.noise*.7
        if case=='ood' and n//3<i<n//2:y=previous_y.copy()
        if case=='ood' and i%19==0:y[:]=np.nan
        timer=time.perf_counter()
        if i:estimate=est.cycle(U[-1],y)
        else:estimate=est.x.copy()
        if mode=='oracle':estimate=x.copy()
        u=ctl.act(y,estimate,est.P,reference=ref,thermal_target=Tref,uop=opu)
        elapsed.append(time.perf_counter()-timer)
        actual=u.copy()
        # Physical cooling effectiveness is a parameter, never leaked to policy.
        x=np.array(m.step(x,actual,p)).ravel()
        if not np.all(np.isfinite(x)) or min(x[:4])<-1e-5 or x[4]>m.tmax+100:raise RuntimeError('integrator domain failure')
        U.append(actual);X.append(x.copy());E.append(estimate.copy());Y.append(y);refs.append(ref)
        if np.all(np.isfinite(y)):previous_y=y.copy()
    X=np.array(X);U=np.array(U);E=np.array(E);q=m.quality(X[1:]);eref=m.quality(E[1:])-m.quality(X[:-1])
    met=metrics(m,X,U,np.array(refs),plant_parameters=p);met.update(kind=kind,mode=mode,seed=seed,case=case,transition=transition,
        estimation_RMSE=float(np.sqrt(np.mean(eref**2))),normalized_IAE=met['IAE']/(m.q0*horizon),
        on_spec_fraction=float(np.mean(np.abs(q-np.array(refs))<=.02*m.q0)),
        average_ms=1000*np.mean(elapsed),p99_ms=1000*np.quantile(elapsed,.99),shield_hits=ctl.shield_hits)
    if save:np.savez_compressed(RESULTS/f'closed_{kind}_{point.get("name","region")}_{mode}_{case}_{seed}.npz',X=X,U=U,E=E,Y=Y,reference=refs,p=p,timing=elapsed)
    return met

def regions(kind):
    m=get_model(kind);sel=json.loads((RESULTS/'selected_regions.json').read_text())[kind]
    points=json.loads((RESULTS/'operating_points.json').read_text());out={}
    for name,idx in sel.items():out[name]={**points[f'{kind}_{idx}'],'name':name}
    # Causal isolation: nominal feed and temperatures selected on a development grid.
    if kind=='PG':
        for T in [337.,340.]:
            x,u=m.operating_point(1.,T);out[f'fixed_feed_{int(T)}K']={'x':x,'u':u,'name':f'fixed_feed_{int(T)}K'}
    else:
        for fr,T in [(1.,158.),(1.,162.),(.9,160.)]:
            x,u=m.operating_point(fr,T);name=f'feed{fr:.1f}_T{T:.0f}';out[name]={'x':x,'u':u,'name':name}
    return out

def run(kinds=('PG','EB')):
    rows=[];selection={};validation=[]
    for kind in kinds:
        reg=regions(kind)
        # Tune ONE gain on the nominal training cases, then freeze across regions.
        tuning=[]
        for gain in [.5,1.,2.]:
            for mode in ['direct','inferential']:
                a=[simulate(kind,reg['nominal'],mode,61000+s,'combined',gain) for s in range(3)]
                score=np.mean([v['normalized_IAE']+v['violation_steps']*.02 for v in a]);tuning.append(dict(kind=kind,gain=gain,mode=mode,score=score))
        gains={mode:min([r for r in tuning if r['mode']==mode],key=lambda r:r['score'])['gain'] for mode in ['direct','inferential']}
        # Validate regions by actual control/production cost, not Fisher determinant.
        for name,point in reg.items():
            a=[simulate(kind,point,'direct',62000+s,'combined',gains['direct']) for s in range(4)]
            score=np.mean([v['normalized_IAE']+.5*max(0,1-v['production_mean']/get_model(kind).prod0)+.001*v['violation_steps'] for v in a])
            validation.append(dict(kind=kind,region=name,score=score,violating_runs=sum(v['violation_steps']>0 for v in a),worst_temperature=max(v['Tmax'] for v in a)))
        selection[kind]=dict(gains=gains,tuning=tuning,
             validation_selected=min([v for v in validation if v['kind']==kind],key=lambda r:r['score'])['region'])
        # All four required operating policies remain in the holdout, including losers.
        for name,point in reg.items():
            for mode in ['direct','inferential']:
                for case in ['kinetic','thermal','combined','sensor','ood']:
                    for s in range(12):
                        met=simulate(kind,point,mode,63000+s,case,gains[mode],save=True)
                        met['region']=name;rows.append(met)
            print(kind,name,'holdout completed',flush=True)
            pd.DataFrame([v for v in rows if v['kind']==kind]).to_csv(RESULTS/f'closedloop_{kind}.csv',index=False)
        # Waiting/inaction and state-oracle comparisons only at nominal and selected.
        for name in dict.fromkeys(['nominal',selection[kind]['validation_selected']]):
            for mode in ['deadband','wait','gated','oracle']:
                for case in ['combined','ood']:
                    for s in range(12):
                        met=simulate(kind,reg[name],mode,63000+s,case,gains['inferential'],save=True)
                        met['region']=name;rows.append(met)
        # Actual transition, same initial state and horizon for each alternative.
        for name in reg:
            for s in range(8):
                met=simulate(kind,reg[name],'direct',64000+s,'combined',gains['direct'],transition=True,save=True)
                met['region']=name;rows.append(met)
        pd.DataFrame([v for v in rows if v['kind']==kind]).to_csv(RESULTS/f'closedloop_{kind}.csv',index=False)
        pd.DataFrame([v for v in validation if v['kind']==kind]).to_csv(RESULTS/f'region_validation_{kind}.csv',index=False)
        dump(RESULTS/f'policy_selection_{kind}.json',selection[kind])
    if len(kinds)==2:
        pd.DataFrame(rows).to_csv(RESULTS/'closedloop.csv',index=False)
        pd.DataFrame(validation).to_csv(RESULTS/'region_validation.csv',index=False);dump(RESULTS/'policy_selection.json',selection)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--kind',choices=['PG','EB']);args=ap.parse_args();run((args.kind,) if args.kind else ('PG','EB'))
