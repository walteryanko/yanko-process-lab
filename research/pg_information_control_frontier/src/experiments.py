import os,json,time,sys,platform,hashlib,traceback
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp
from model import *
from estimation import Filter,MHE,R,SIGMA
from control import decide,costs,candidates,select
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
(OUT/'trajectories').mkdir(exist_ok=True)
PROTOCOL=json.loads((ROOT/'configs/protocol.json').read_text())
METHODS=['B0_PI','B1_ukf','B1_continuous','B2_estimator','B2_both','B3_assumed_inventory',
         'B3_known_inventory','B4_mhe','B5_true_state','P1_expected','P2_regret',
         'P3_adaptive_regret','P4_hybrid','P5_initial','P5_periodic','P5_event','P5_delayed','P5_noisy','P5_frequent']
SCENARIOS=['nominal','servo','kinetic','heat_transfer','inventory_plus','inventory_minus',
           'feed','properties','correlated_noise','dropout','saturation','combined','outside_prior','unreachable']
def dump(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x)))
def scenario(name):
    p=np.zeros(3);v=0;delta=0.;qmax=3.
    if name=='kinetic':p[0]=np.log(.88)
    if name=='heat_transfer':p[1]=np.log(1.12)
    if name=='properties':p[2]=np.log(1.07)
    if name=='inventory_plus':delta=.4
    if name=='inventory_minus':delta=-.4
    if name=='combined':p[:2]=np.log([.88,1.12]);delta=.25
    if name=='outside_prior':p[0]=np.log(.82);delta=.8
    if name=='saturation':qmax=1.3
    return p,v,delta,qmax

def episode(name,method,seed,steps=60,save=False,grid=5):
    start=time.perf_counter();rng=np.random.default_rng(seed)
    xn=equilibrium();p,variant,delta,qmax=scenario(name);x=twin(xn,delta)
    noise=rng.normal(size=(steps+1,2))*SIGMA
    if name=='correlated_noise':
        for k in range(1,len(noise)):noise[k]=.85*noise[k-1]+np.sqrt(1-.85**2)*noise[k]
    chemnoise=rng.normal(size=steps+1)
    # A sensor layer, independent of controllers, creates/delivers measurements.
    adaptive=method in ['B2_estimator','B2_both','P3_adaptive_regret','P4_hybrid']
    red=method.startswith('B3')
    est=MHE(xn) if method=='B4_mhe' else Filter(xn,'adaptive' if adaptive else ('reduced' if red else 'ukf'),
        known_inventory=inventory(x) if method=='B3_known_inventory' else inventory(xn))
    us=[];xs=[];hats=[];covs=[];refs=[];measurements=[];infos=[];times=[];nis=[];samplelog=[]
    qprev=1.;integral=0.;cumD=0.;last_conflict=0.;last_sample=-100;requests=0;pending=[]
    u_previous=U0.copy();checkpoint_est={}
    for k in range(steps+1):
        t=k*DT;u=U0.copy()
        if name in ['feed','combined'] and k>=26:u[0]*=1.12
        if name=='combined' and k>=38:u[5]+=3.
        ref=xn[2]
        if name in ['servo','combined'] and k>=15:ref=xn[2]+.12
        if name in ['servo','combined'] and k>=40:ref=xn[2]-.12
        if name=='unreachable':ref=xn[2]*1.45
        y=x[4:6]+noise[k]
        if name=='dropout' and 15<=k<30:y[1]=np.nan
        chemical=None
        if method.startswith('P5'):
            regular=(k%15==0 and k<60)
            if method=='P5_initial':request=k==0
            elif method=='P5_event':request=requests<4 and k-last_sample>=8 and (k==0 or last_conflict>=.2 or .4*np.exp(-cumD)>.15)
            elif method=='P5_frequent':request=(k%7==0 and requests<8)
            else:request=regular
            if request and k<steps:
                delay=3 if method=='P5_delayed' else 0;sd=.15 if method=='P5_noisy' else .03
                pending.append((k+delay,k,float(x[2]+sd*chemnoise[k]),sd,est.state()[2],cumD))
                requests+=1;last_sample=k;samplelog.append([k,k+delay,sd])
            arrived=[a for a in pending if a[0]==k]
            if arrived:
                _,sample_k,val,sd,oldhat,oldD=arrived[-1]
                if sample_k<k:
                    decay=np.exp(-(cumD-oldD))
                    # Approximate delayed innovation transport; no retroactive control.
                    val=est.state()[2]+decay*(val-oldhat);sd=np.sqrt(sd**2*decay**2+.03**2)
                chemical=(val,sd**2)
        tic=time.perf_counter()
        hat=est.update(u_previous,y,advance=k>0,chemical=chemical)
        cov=est.covariance()
        if method=='B5_true_state':hat=x.copy() # explicitly diagnostic, not used by other methods
        est_seconds=time.perf_counter()-tic
        xs.append(x.copy());hats.append(hat.copy());covs.append(np.diag(cov));refs.append(ref);measurements.append(y)
        if k==steps:break
        pp=est.params() if method in ['B2_both','P3_adaptive_regret','P4_hybrid'] else np.zeros(3)
        width=.4*np.exp(-cumD)
        mode='nominal'
        if method=='P1_expected':mode='expected'
        if method in ['P2_regret','P3_adaptive_regret','P4_hybrid']:mode='regret'
        if method=='B1_continuous':mode='continuous'
        tic=time.perf_counter()
        if method=='B0_PI':
            e=hat[2]-ref;candidate=1+4*e+2*integral
            q=np.clip(candidate,max(.05,qprev-.4),min(qmax,qprev+.4))
            if abs(q-candidate)<1e-10:integral+=e*DT
            info=dict(fallback=False,solver_success=True,regret=np.nan,conflict=0.,predicted_violation=np.nan,candidates=0)
        else:
            q,info=decide(hat,u,pp,ref,qprev,mode,width,qmax,ngrid=grid)
            if method=='P4_hybrid' and info['conflict']<.2:
                q,info=decide(hat,u,pp,ref,qprev,'nominal',width,qmax,ngrid=grid)
        times.append([est_seconds,time.perf_counter()-tic]);infos.append(info);last_conflict=info['conflict']
        # Event sampler may inspect disagreement even under nominal control; no truth.
        if method=='P5_event':
            _,d=decide(hat,u,np.zeros(3),ref,qprev,'regret',width,qmax)
            last_conflict=d['conflict']
        u[3]=q*U0[3];us.append(u.copy());x=step(x,u,p,variant,12)
        if not np.all(np.isfinite(x)) or min(x[:4])<-1e-8 or min(x[4:])<250 or max(x[4:])>410:
            raise FloatingPointError('plant domain')
        cumD+=dilution(u)*DT;u_previous=u;qprev=q
    xs=np.array(xs);hats=np.array(hats);covs=np.array(covs);refs=np.array(refs);us=np.array(us)
    ts=np.arange(steps+1)*DT;err=xs[:,2]-refs;esterr=hats-xs;over=np.maximum(xs[:,4]-TLIMIT,0)
    iae=float(np.trapezoid(abs(err),ts));q=us[:,3]/U0[3]
    metrics=dict(scenario=name,method=method,seed=seed,IAE=iae,ISE=float(np.trapezoid(err**2,ts)),
        ITAE=float(np.trapezoid(ts*abs(err),ts)),max_error=float(max(abs(err))),
        RMSE_CC=float(np.sqrt(np.mean(esterr[:,2]**2))),bias_CC=float(np.mean(esterr[:,2])),
        coverage_CC=float(np.mean(abs(esterr[:,2])<=1.96*np.sqrt(np.maximum(covs[:,2],0)))),
        Tmax=float(max(xs[:,4])),violations=int(np.sum(over>1e-6)),duration_violations=float(np.sum(over[:-1]>1e-6)*DT),
        max_exceedance=float(max(over)),thermal_severity=float(np.trapezoid(over,ts)),
        cooling_effort=float(np.sum(q**2)*DT),total_variation=float(np.sum(abs(np.diff(np.r_[1.,q])))),
        saturation=float(np.mean((q>=qmax-1e-8)|(q<=.05+1e-8))),
        solver_failure=float(np.mean([not d['solver_success'] for d in infos])),
        fallback=float(np.mean([d['fallback'] for d in infos])),
        decision_ms=float(np.mean(np.array(times)[:,1])*1000),decision_p95_ms=float(np.percentile(np.array(times)[:,1],95)*1000),
        estimator_ms=float(np.mean(np.array(times)[:,0])*1000),
        samples=requests,mhe_failures=est.mhe_failures,repairs=est.repairs,
        mean_NIS=float(np.nanmean(est.nis)),production_kmol=float(np.sum((us[:,0]/RHO[0]+us[:,1]/RHO[1]+us[:,2]/RHO[2])*xs[:-1,2])*DT),
        mean_regret=float(np.nanmean([d['regret'] for d in infos])) if method!='B0_PI' else np.nan,
        mean_conflict=float(np.mean([d['conflict'] for d in infos])),
        seconds=time.perf_counter()-start)
    for j,label in enumerate(['CA','CB','CC','CM','T','Tt']):metrics['RMSE_'+label]=float(np.sqrt(np.mean(esterr[:,j]**2)))
    # Settling requires one unchanging reference through the remaining episode.
    settled=np.nan
    last_change=0 if name not in ['servo','combined'] else 40
    for k in range(last_change,len(ts)):
        if np.all(abs(err[k:])<=.02*abs(refs[k:])):settled=float(ts[k]-ts[last_change]);break
    metrics['settling_h']=settled
    if save:
        np.savez_compressed(OUT/'trajectories'/f'{name}__{method}__{seed}.npz',
            t=ts,x=xs,estimate=hats,cov_diag=covs,reference=refs,u=us,y=np.array(measurements),
            times=np.array(times),samples=np.array(samplelog),info_json=json.dumps(infos))
    return metrics

def structural():
    t0=time.perf_counter();rows=[];x0=equilibrium();inputs=np.tile(U0,(60,1))
    for k in range(60):
        inputs[k,3]*=1+.25*np.sin(k*.3);inputs[k,0]*=1+.04*np.cos(k*.17)
    for variant in range(5):
        # Same initial conditions isolate the altered physical equations.
        a=rollout(x0,inputs,np.zeros(3),variant,12)
        b=rollout(twin(x0,.4),inputs,np.zeros(3),variant,12)
        expected=.4*np.exp(-np.r_[0,np.cumsum([dilution(u)*DT for u in inputs])])
        diff=float(np.max(abs(a[:,4:]-b[:,4:])))
        rows.append(dict(variant=VARIANTS[variant],max_thermal_difference_K=diff,
                         max_product_decay_error=float(max(abs(b[:,2]-a[:,2]-expected)))))
        np.savez_compressed(OUT/'trajectories'/f'twins_{variant}.npz',t=np.arange(61)*DT,a=a,b=b,inputs=inputs)
    pd.DataFrame(rows).to_csv(OUT/'twins.csv',index=False)
    # Observable sensitivity is a finite-horizon experiment, not a structural proof.
    obs=[];spectra=[]
    for variant in [0,2,3,4]:
        for temp in [315.,325.,332.33361802,340.,348.]:
            for excited in [False,True]:
                xx=x0.copy();xx[4]=temp
                U=inputs[:30].copy() if excited else np.tile(U0,(30,1))
                for eps in [1e-3,1e-4,1e-5]:
                    cols=[]
                    for j in range(6):
                        d=np.eye(6)[j]*SCALE[j]*eps
                        yp=rollout(xx+d,U,np.zeros(3),variant,12)[:,4:]/SIGMA
                        ym=rollout(xx-d,U,np.zeros(3),variant,12)[:,4:]/SIGMA
                        cols.append(((yp-ym)/(2*eps)).ravel())
                    A=np.column_stack(cols);s=np.linalg.svd(A,compute_uv=False)
                    row=dict(variant=VARIANTS[variant],T_initial=temp,excited=excited,epsilon=eps,
                            rank_1e6=int(np.sum(s>s[0]*1e-6)),rank_1e8=int(np.sum(s>s[0]*1e-8)),
                            smin=float(s[-1]),smax=float(s[0]),condition=float(s[0]/max(s[-1],1e-30)))
                    obs.append(row)
                    spectra.append(dict(**row,**{f's{j+1}':float(s[j]) for j in range(6)}))
    pd.DataFrame(obs).to_csv(OUT/'observability.csv',index=False)
    pd.DataFrame(spectra).to_csv(OUT/'singular_values.csv',index=False)
    # Independent integration comparison.
    independent_rows=[]
    for variant in range(5):
        z=x0.copy();w=x0.copy();maxerr=0.
        for u in inputs[:20]:
            z=step(z,u,np.zeros(3),variant,12);w=independent(w,u,np.zeros(3),variant)
            maxerr=max(maxerr,float(np.max(abs(z-w))))
        independent_rows.append(dict(variant=VARIANTS[variant],max_abs_error=maxerr))
    pd.DataFrame(independent_rows).to_csv(OUT/'integration.csv',index=False)
    # Conflict and exact finite-grid regret, multiple horizons and widths.
    decisions=[]
    for width in [0.,.1,.2,.4,.6]:
        states=np.array([twin(x0,-width),twin(x0,width)])
        for h in [4,14,28,57]:
            for ref in [2.1,2.295764605,2.5,3.328858677]:
                plans=candidates(1.,3.,21);J,V=costs(states,plans,U0,np.zeros(3),ref,1.,h)
                z,fall,rr=select(J,V,'regret')
                feasible=V<=1e-8
                opt=np.argmin(np.where(feasible,J,np.inf),axis=1)
                decisions.append(dict(width=width,horizon=h,reference=ref,action_low=plans[opt[0],0],
                    action_high=plans[opt[1],0],robust_action=plans[z,0],regret=rr,fallback=fall,
                    feasible_common=int(np.sum(np.all(feasible,axis=0)))))
    pd.DataFrame(decisions).to_csv(OUT/'decisions.csv',index=False)
    # Open-loop estimator test: both worlds produce the exact same measured stream in M0.
    erows=[]
    for seed in PROTOCOL['test_seeds']:
        rng=np.random.default_rng(seed);a=rollout(twin(x0,-.4),inputs,np.zeros(3),0,12)
        b=rollout(twin(x0,.4),inputs,np.zeros(3),0,12)
        Y=a[:,4:]+rng.normal(size=(61,2))*SIGMA
        for kind in ['ukf','adaptive','reduced','mhe']:
            e=MHE(x0) if kind=='mhe' else Filter(x0,kind,inventory(x0))
            hats=[]
            for k in range(61):hats.append(e.update(inputs[max(0,k-1)],Y[k],advance=k>0))
            hats=np.array(hats)
            erows.append(dict(seed=seed,estimator=kind,RMSE_low=float(np.sqrt(np.mean((hats[:,2]-a[:,2])**2))),
                RMSE_high=float(np.sqrt(np.mean((hats[:,2]-b[:,2])**2))),
                bound_max_abs_violation=float(np.min(np.maximum(abs(hats[:,2]-a[:,2]),abs(hats[:,2]-b[:,2]))-abs(a[:,2]-b[:,2])/2))))
            if seed==PROTOCOL['test_seeds'][0]:
                np.savez_compressed(OUT/'trajectories'/f'estimation_{kind}.npz',t=np.arange(61)*DT,
                    a=a,b=b,estimate=hats,lower=abs(a[:,2]-b[:,2])/2)
    pd.DataFrame(erows).to_csv(OUT/'estimation.csv',index=False)
    dump('structural_execution.json',dict(seconds=time.perf_counter()-t0,completed=True,
        independent_integration_pass=all(r['max_abs_error']<2e-5 for r in independent_rows)))

def statistics(frame,prefix=''):
    numeric=frame.select_dtypes(include=np.number).columns.tolist()
    frame.groupby(['scenario','method'])[numeric].agg(['mean','median','std','min','max']).to_csv(OUT/f'{prefix}summary.csv')
    comparisons=[]
    rng=np.random.default_rng(3333)
    for scenario in list(frame.scenario.unique())+['FINITE_SUITE']:
        subset=frame if scenario=='FINITE_SUITE' else frame[frame.scenario==scenario]
        a=subset.groupby(['seed','method']).IAE.mean().unstack()
        for candidate,baseline in PROTOCOL['primary_contrasts']+[(m,'B1_ukf') for m in frame.method.unique() if m not in ['B1_ukf','P2_regret']]:
            if candidate not in a or baseline not in a:continue
            x=(a[baseline]-a[candidate]).dropna().values;n=len(x)
            boot=np.mean(x[rng.integers(n,size=(5000,n))],axis=1)
            se=np.std(x,ddof=1)
            test=ttest_1samp(x,0).pvalue if se>1e-15 else (1. if max(abs(x))<1e-15 else 0.)
            comparisons.append(dict(scenario=scenario,candidate=candidate,baseline=baseline,n=n,
                mean_improvement=float(np.mean(x)),median_improvement=float(np.median(x)),std_difference=float(se),
                percent_improvement=float(100*np.mean(x)/a[baseline].mean()),
                ci95_low=float(np.quantile(boot,.025)),ci95_high=float(np.quantile(boot,.975)),
                paired_dz=float(np.mean(x)/se) if se>1e-15 else np.nan,p_raw=float(test),
                worst_difference=float(min(x)),wins=int(np.sum(x>0))))
    c=pd.DataFrame(comparisons)
    c['p_holm_primary']=np.nan
    for scenario in c.scenario.unique():
        ix=c.index[(c.scenario==scenario)&c.apply(lambda r:[r.candidate,r.baseline] in PROTOCOL['primary_contrasts'],axis=1)]
        ix=sorted(ix,key=lambda i:c.loc[i,'p_raw']);running=0.
        for j,i in enumerate(ix):
            running=max(running,min(1.,(len(ix)-j)*c.loc[i,'p_raw']));c.loc[i,'p_holm_primary']=running
    c.to_csv(OUT/f'{prefix}contrasts.csv',index=False)
    return c

def main():
    import argparse
    pa=argparse.ArgumentParser();pa.add_argument('--stage',default='all');args=pa.parse_args()
    if args.stage in ['all','core']:structural()
    if args.stage=='core':return
    # Pilot uses distinct seeds, measures runtime, does not tune on test outcomes.
    tic=time.perf_counter()
    pilot=[episode('inventory_plus',m,11,steps=8) for m in ['B1_ukf','P2_regret','B4_mhe','B1_continuous']]
    pd.DataFrame(pilot).to_csv(OUT/'pilot.csv',index=False)
    dump('runtime_environment.json',dict(python=sys.version,platform=platform.platform(),
        protocol_sha256=hashlib.sha256((ROOT/'configs/protocol.json').read_bytes()).hexdigest(),
        pilot_seconds=time.perf_counter()-tic,OMP_NUM_THREADS=os.environ.get('OMP_NUM_THREADS')))
    rows=[];failures=[];tic=time.perf_counter()
    # Full planned matrix, write progress after each scenario. No early favorable stopping.
    for s in SCENARIOS:
        for m in METHODS:
            for seed in PROTOCOL['test_seeds']:
                try:rows.append(episode(s,m,seed,save=True))
                except Exception as e:failures.append(dict(scenario=s,method=m,seed=seed,error=repr(e),traceback=traceback.format_exc()))
            print(json.dumps(dict(scenario=s,method=m,completed=len(rows),failed=len(failures),seconds=time.perf_counter()-tic)),flush=True)
        pd.DataFrame(rows).to_csv(OUT/'episodes.csv',index=False);dump('failures.json',failures)
    frame=pd.DataFrame(rows);statistics(frame)
    # Independent confirmation of the three predeclared contrasts in conflict and mismatch regimes.
    confirm=[]
    for s in ['inventory_plus','inventory_minus','combined','kinetic']:
        for m in ['B1_ukf','B2_estimator','B2_both','P2_regret','P3_adaptive_regret']:
            for seed in PROTOCOL['confirmation_seeds']:
                try:confirm.append(episode(s,m,seed,save=True))
                except Exception as e:failures.append(dict(scenario=s,method=m,seed=seed,error=repr(e)))
    cf=pd.DataFrame(confirm);cf.to_csv(OUT/'confirmation.csv',index=False);statistics(cf,'confirmation_')
    sensitivity=[]
    for s in ['nominal','inventory_plus','combined']:
        for m in ['B1_ukf','P2_regret']:
            for seed in PROTOCOL['validation_seeds']:
                sensitivity.append(episode(s,m,seed,grid=9))
    pd.DataFrame(sensitivity).to_csv(OUT/'grid_sensitivity.csv',index=False)
    dump('failures.json',failures)
    dump('execution.json',dict(status='executed',episodes=len(rows),confirmation=len(confirm),
         grid_sensitivity=len(sensitivity),planned_main=len(SCENARIOS)*len(METHODS)*len(PROTOCOL['test_seeds']),
         failed=len(failures),seconds=time.perf_counter()-tic,
         limitation='finite candidate two-block NMPC; MHE window six; no industrial calibration or full historical ICAC replay'))
    print('EXECUTION_COMPLETE',flush=True)

if __name__=='__main__':main()
