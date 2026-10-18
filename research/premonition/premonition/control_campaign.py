from pathlib import Path
import json,time
import numpy as np
from .physics import *
from .observer import UKF,Observation
from .detectors import Detectors,load_models
from .control import NMPC
from .scenarios import specification
from .evaluation import paired_ci
from .io import save,csv_write,sha

def checkpoint_identity(models_dir,thresholds_path):
    src=Path(__file__).resolve().parent
    return dict(schema=1,source={n:sha(src/n) for n in ['physics.py','observer.py','detectors.py','ews.py','stability.py','control.py','scenarios.py']},models={p.name:sha(p) for p in sorted(Path(models_dir).glob('*.json'))},thresholds=sha(thresholds_path))

def verify_checkpoints(out,identity):
    path=Path(out)/'checkpoint_context.json'
    if path.exists():
        if json.loads(path.read_text())!=identity:raise ValueError('Checkpoint identity mismatch; use a new --out directory for changed code/models.')
    elif list((Path(out)/'episodes').glob('*.json')):
        raise ValueError('Existing episodes lack a model identity; use a new --out directory.')
    else:save(path,identity)

def rollout(seed,mode,models,thresholds,steps=120,observer_mode='historical',broken_detector=False):
    spec=specification(seed,steps);x=spec['initial'].copy();obs=UKF(mode=observer_mode);det=Detectors(models,thresholds);ctl=NMPC(mode)
    rows=[];previous=U0[3];applied=U0.copy();start=time.perf_counter();cost=0.
    for k in range(steps):
        # Measurement at t_k before choosing action on [t_k,t_{k+1}).
        y=x[4:]+spec['noise'][k]+spec['bias'][k]
        if k:xhat,Pc=obs.advance(applied,y)
        else:
            xhat=obs.x.copy();xhat[4:]=y;obs.x=xhat;Pc=obs.P.copy()
        known=spec['known'][k].copy();known[3]=previous
        packet=Observation(y,known,xhat,Pc,obs.innov,obs.nis);d=det.update(packet)
        if broken_detector:d['scores']['D5']=np.nan
        future=None
        if mode=='oracle_offline':
            ix=np.minimum(np.arange(k,k+57),steps-1);fu=spec['actual'][ix].copy();caps=np.full(57,UMAX)
            if spec['kind'] in ['cooling_loss','temporary_saturation']:caps=np.where(fu[:,3]<U0[3]-.001,fu[:,3],UMAX)
            future=(np.column_stack([fu,caps]),spec['params'][ix].copy(),x.copy())
        ctl.sp=float(spec['sp'][k]);mv,diag=ctl.action(packet,d,thresholds,future)
        plant_u=spec['actual'][k].copy();plant_u[3]=mv
        # Actuator loss/capacity schedule is plant-only until observed after the action.
        cap=UMAX
        if spec['kind'] in ['cooling_loss','temporary_saturation'] and spec['actual'][k,3]<U0[3]-.001:
            cap=float(spec['actual'][k,3]);plant_u[3]=min(mv,cap)
        applied=known.copy();applied[3]=plant_u[3]
        xnext=step(x,plant_u,spec['params'][k],n=6)
        if not physical(xnext):raise ValueError(f'Plant failed {seed}/{mode}/{k}')
        err=xnext[2]-spec['sp'][k];stage=.8*(err/spec['sp'][k])**2+.2*((plant_u[3]-previous)/U0[3])**2;cost+=stage
        rows.append(dict(k=k,t_h=(k+1)*DT,CC=xnext[2],CC_est=step(xhat,applied)[2],estimate_CC_current=xhat[2],estimate_time_h=k*DT,T=xnext[4],Tt=xnext[5],CA=xnext[0],CB=xnext[1],CM=xnext[3],
          yT=y[0],estimate_T=xhat[4],sp=spec['sp'][k],mw_command=mv,mw=plant_u[3],actuator_cap=cap,T0_actual=plant_u[4],UA_actual=spec['params'][k,13],
          ac1=d['features'][10],variance=float(np.exp(d['features'][11])),recovery=d['features'][17],alpha_full=d['features'][5],alpha_reactive=d['features'][4],innovation=obs.innov[0],uncertainty_CC=np.sqrt(Pc[2,2]),
          iae=abs(err)*DT,tracking_error=err,estimate_error=x[2]-xhat[2],production=flow(plant_u)*xnext[2]*DT,cooling=plant_u[3]*DT,cost_cumulative=cost,
          violation=max(0.,xnext[4]-344.),effort=((plant_u[3]-previous)/U0[3])**2,**diag))
        x=xnext;previous=plant_u[3]
    metric=dict(seed=seed,kind=spec['kind'],controller=mode,observer=observer_mode,IAE=sum(r['iae'] for r in rows),RMSE_CC=float(np.sqrt(np.mean([r['estimate_error']**2 for r in rows]))),tracking_RMSE=float(np.sqrt(np.mean([r['tracking_error']**2 for r in rows]))),
        production_kmol=sum(r['production'] for r in rows),cooling_kmol=sum(r['cooling'] for r in rows),effort=sum(r['effort'] for r in rows),peak_T=max(r['T'] for r in rows),violation_h=DT*sum(r['violation']>1e-7 for r in rows),violation_Kh=DT*sum(r['violation'] for r in rows),
        thermal_event=int(any(r['violation']>1e-7 for r in rows)),cost=cost,feasible_fraction=np.mean([r['feasible'] for r in rows]),fallbacks=sum(r['fallback']!='none' for r in rows),optimizer_failures=sum(r['optimizer_failed'] for r in rows),interventions=sum(r['intervention'] for r in rows),
        mean_ms=1000*np.mean([r['seconds'] for r in rows]),p95_ms=1000*np.quantile([r['seconds'] for r in rows],.95),observer_failures=obs.failures,seconds=time.perf_counter()-start)
    metric['economic_proxy']=metric['production_kmol']-.0005*metric['cooling_kmol'] # declared arbitrary kmol-equivalent proxy; not money
    return metric,rows

def campaign_EF(out,models_dir,thresholds_path,n=100,pilot=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);models=load_models(models_dir);th=json.loads(Path(thresholds_path).read_text())
    verify_checkpoints(out,checkpoint_identity(models_dir,thresholds_path))
    modes=['C0','C1','C2','C3','C4','conservative','oracle_offline','C4_noEWS'];metrics=[];start=time.perf_counter();traces=[]
    seedbase=1100 if pilot else 50000
    for i in range(n):
        pair={}
        for mode in modes:
            path=out/'episodes'/f'{seedbase+i}_{mode}.json'
            if path.exists():
                cached=json.loads(path.read_text());m=cached['metrics'];r=cached['rows']
            else:
                m,r=rollout(seedbase+i,mode,models,th);save(path,dict(metrics=m,rows=r))
            metrics.append(m);pair[mode]=(m,r)
            if i<12:traces.append(dict(**m,rows=r))
        # Potentially unnecessary actions are defined from the paired nominal potential outcome.
        nominal_event=pair['C0'][0]['thermal_event']
        for mode in modes:
            pair[mode][0]['interventions_if_nominal_no_event']=pair[mode][0]['interventions'] if not nominal_event else 0
            pair[mode][0]['paired_nominal_event']=nominal_event
        print(json.dumps(dict(stage='control_pairs',done=i+1,n=n,seconds=round(time.perf_counter()-start,1))),flush=True)
        csv_write(out/'metrics.csv',metrics)
    summary={};comparison=[]
    numeric=['IAE','RMSE_CC','tracking_RMSE','production_kmol','cooling_kmol','effort','peak_T','violation_h','violation_Kh','thermal_event','cost','economic_proxy','feasible_fraction','fallbacks','optimizer_failures','interventions','mean_ms','p95_ms','observer_failures','interventions_if_nominal_no_event']
    for mode in modes:
        rr=[m for m in metrics if m['controller']==mode];summary[mode]={k:float(np.mean([m[k] for m in rr])) for k in numeric};summary[mode]['n']=len(rr);summary[mode]['events']=sum(m['thermal_event'] for m in rr)
        if mode!='C0':
            base=[m for m in metrics if m['controller']=='C0']
            for key in numeric[:13]:comparison.append(dict(A='C0',B=mode,metric=key,**paired_ci([m[key] for m in base],[m[key] for m in rr])))
    a=[m for m in metrics if m['controller']=='C4_noEWS'];b=[m for m in metrics if m['controller']=='C4']
    for key in numeric[:13]:comparison.append(dict(A='C4_noEWS',B='C4',metric=key,**paired_ci([m[key] for m in a],[m[key] for m in b])))
    csv_write(out/'paired.csv',comparison);save(out/'paired.json',comparison);save(out/'summary.json',summary);save(out/'traces.json',traces)
    # Explicit falsification: dead probabilistic predictor cannot disable physical checks.
    m,r=rollout(seedbase,'C4',models,th,broken_detector=True);save(out/'dead_detector.json',dict(metrics=m,rows=r))
    save(out/'execution.json',dict(pairs=n,rollouts=n*len(modes),steps=120,modes=modes,seconds=time.perf_counter()-start,seeds=list(range(seedbase,seedbase+n)),oracle='offline noncausal, full state + future feed and parameters; future actuator capacity included',solver='ProcessLab fixed-budget coordinate search'))
    return summary
