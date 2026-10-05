"""Paired, independently integrated truth; all failures and overrides retained."""
import argparse, csv, hashlib, json, multiprocessing as mp, os, time, traceback
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from model import *
from compiled import Models,compile_models
from networks import NeuralTransition,LSTM
from observer import Observer,KINDS
from control import NMPC
from protocol import CASES,SEEDS,CONFIGS,scenario,specification

_MODELS=None;_NETWORK=None;_LSTMS=None;_SIGNATURE=None

def init_worker(lib,signature):
    global _MODELS,_NETWORK,_LSTMS,_SIGNATURE
    _MODELS=Models(lib);_NETWORK=NeuralTransition.load();_SIGNATURE=signature
    _LSTMS={k:LSTM.load(WEIGHTS/f'lstm_q_{k}.json') for k in ['physical','neural']}

def disturbance_noise(case,seed,steps):
    rng=np.random.default_rng(seed+10000*CASES.index(case))
    return rng.normal(size=(steps,7)),rng.normal(size=steps)

def actual_input(u,normal,loss=1.,noise=1.):
    actual=u.copy();actual[:4]*=1+.01*noise*normal[:4];actual[3]*=loss
    actual[4:]+=.2*normal[4:]
    actual[0]=np.clip(actual[0],.04*F0[0],2*F0[0]);actual[3]=max(0.,actual[3]);return actual

def truth_step(state,u,kin):
    sol=solve_ivp(lambda t,x:rhs(x,u,kin),(0.,DT),state,method='DOP853',rtol=2e-10,atol=1e-11,dense_output=True)
    if not sol.success:raise RuntimeError(sol.message)
    grid=np.linspace(0,DT,21);dense=sol.sol(grid).T
    if not np.all(np.isfinite(dense)):raise ValueError('Nonfinite true state')
    return dense[-1].copy(),grid,dense

def job_name(job):
    case,e,p,m,con,seed=job;return f'{case}__{e}__{p}__{m}__{int(con)}__{seed}'

def run(job):
    case,e,p,m,con,seed=job;name=job_name(job);start=time.perf_counter()
    path=RESULTS/'runs'/f'{name}.json'
    if path.exists():
        old=json.loads(path.read_text())
        if old.get('signature')==_SIGNATURE:return old
    steps=int(round(10./DT));input_norm,sensor_norm=disturbance_noise(case,seed,steps)
    true=BASE.copy();estimate=BASE+np.array([.006,.22,-.12,.04,1.5])
    kind='neural' if e in ['nake','lstm_nake'] else 'physical'
    obs=Observer(estimate,_MODELS,e,_LSTMS[kind],_NETWORK)
    nmpc=NMPC(_MODELS,p,m,con)
    trace={k:[] for k in ['time','true','estimate','command','actual','reference','Tmax','violation_h','latency_ms','solver_success','fallback','predicted_Tmax','q','nis','cov_diagonal']}
    iae=ise=itae=event_iae=thermal_iae=violation=0.;tmax=true[4];errors=[];fraction_errors=[]
    effort=np.zeros(2);total_moves=np.zeros(2);previous=np.ones(2);fails=fallbacks=rate_overrides=0;status='complete';error=None
    try:
        for k in range(steps):
            t=k*DT;u,ref,kin,loss,noise,missing=scenario(case,t)
            action,diag=nmpc.step(estimate,u,ref);u[0]=action[0]*F0[0];u[3]=action[1]*Q0
            au=actual_input(u,input_norm[k],loss,noise);nxt,grid,dense=truth_step(true,au,kin)
            dd=fraction(dense)-ref;dx=nxt-true
            step_iae=float(np.trapezoid(abs(dd),grid));iae+=step_iae;ise+=float(np.trapezoid(dd**2,grid))
            itae+=float(np.trapezoid(abs(dd)*(t+grid),grid))
            if t>=(3. if case.startswith('servo') else 5.):event_iae+=step_iae
            thermal_iae+=float(np.trapezoid(abs(dense[:,4]-TNOM),grid))
            vh=float(np.trapezoid((dense[:,4]>T_LIMIT).astype(float),grid));violation+=vh
            tmax=max(tmax,float(dense[:,4].max()));fails+=int(not diag['solver_success']);fallbacks+=int(diag['fallback'])
            change=abs(action-previous);total_moves+=change;effort+=(action-1.)**2*DT
            rate_overrides+=int(np.any(change>[.12001,.08001]))
            previous=action.copy();true=nxt
            y=float(true[4]+1.5*sensor_norm[k]) if not missing else np.nan
            estimate,cov,nis=obs.update(u,y);errors.append(estimate-true);fraction_errors.append(float(fraction(estimate)-fraction(true)))
            values=[(k+1)*DT,true.copy(),estimate.copy(),u.copy(),au.copy(),ref,float(dense[:,4].max()),vh,
                    diag['latency_ms'],diag['solver_success'],diag['fallback'],diag['predicted_Tmax_C'] if con else np.nan,
                    obs.last_q.copy(),nis if nis is not None else np.nan,np.diag(cov)]
            for key,value in zip(trace,values):trace[key].append(value)
            if tmax>T_STOP or true[4]<0. or np.min(true[:4])<-1e-7:
                status='domain_stop';error='true plant left reduced-model numerical domain';break
    except Exception as ex:
        status='error';error=str(ex);dump(RESULTS/'errors'/f'{name}.json',dict(error=str(ex),traceback=traceback.format_exc()))
    arrays={k:np.asarray(v) for k,v in trace.items()};tracedir=RESULTS/'traces';tracedir.mkdir(exist_ok=True)
    np.savez_compressed(tracedir/f'{name}.npz',**arrays)
    n=len(errors);rmse=np.sqrt(np.mean(np.asarray(errors)**2,axis=0)) if n else np.zeros(5)
    row=dict(name=name,signature=_SIGNATURE,case=case,estimator=e,prediction=p,mode=m,constrained=con,seed=seed,
             status=status,error=error,samples=n,duration_h=n*DT,IAE=iae,IAE_event=event_iae,ISE=ise,ITAE=itae,
             temperature_IAE_K_h=thermal_iae,Tmax_C=tmax,violation_h=violation,
             xEB_estimate_RMSE=float(np.sqrt(np.mean(np.array(fraction_errors)**2))) if n else None,
             state_RMSE=rmse,terminal_true_fraction=float(fraction(true)),terminal_estimated_fraction=float(fraction(estimate)),
             final_abs_offset=float(abs(fraction(true)-scenario(case,max(0.,n*DT-1e-8))[1])),
             covariance_repairs=obs.repairs,positivity_projections=obs.projections,
             solver_failed_statuses=fails,fallbacks=fallbacks,move_rate_overrides=rate_overrides,
             median_latency_ms=float(np.median(arrays['latency_ms'])) if n else 0.,
             p95_latency_ms=float(np.percentile(arrays['latency_ms'],95)) if n else 0.,
             normalized_squared_effort=effort,normalized_total_variation=total_moves,wall_seconds=time.perf_counter()-start)
    dump(path,row);return row

def openloop(case,seed):
    steps=int(round(10./DT));norm,sens=disturbance_noise(case,seed,steps);true=BASE.copy()
    estimate=BASE+np.array([.006,.22,-.12,.04,1.5]);observers={}
    for k in KINDS:
        kind='neural' if k in ['nake','lstm_nake'] else 'physical'
        observers[k]=Observer(estimate,_MODELS,k,_LSTMS[kind],_NETWORK)
    errors={k:[] for k in KINDS};ferrors={k:[] for k in KINDS};failed={};true_trace=[];est_trace={k:[] for k in KINDS}
    for i in range(steps):
        t=i*DT;u,ref,kin,loss,noise,missing=scenario(case,t)
        # Servo cases are steady nominal open-loop observer tests: no hidden actuator policy.
        true,grid,dense=truth_step(true,actual_input(u,norm[i],loss,noise),kin);true_trace.append(true.copy())
        if not 0.<true[4]<T_STOP:break
        y=true[4]+1.5*sens[i] if not missing else np.nan
        for k,o in observers.items():
            if k in failed:continue
            try:
                x,cov,nis=o.update(u,y);errors[k].append(x-true);ferrors[k].append(float(fraction(x)-fraction(true)));est_trace[k].append(x.copy())
            except Exception as ex:failed[k]=str(ex)
    rows=[]
    for k,o in observers.items():
        err=np.asarray(errors[k]);n=len(err);after=err[int(5./DT):]
        fe=np.asarray(ferrors[k]);afe=fe[int(5./DT):]
        rows.append(dict(case=case,seed=seed,estimator=k,status='error' if k in failed else 'complete',error=failed.get(k),samples=n,
                         state_RMSE=np.sqrt(np.mean(err**2,axis=0)) if n else np.zeros(5),
                         xEB_RMSE=float(np.sqrt(np.mean(fe**2))) if n else None,
                         xEB_RMSE_after5=float(np.sqrt(np.mean(afe**2))) if len(afe) else None,
                         T_RMSE_after5=float(np.sqrt(np.mean(after[:,4]**2))) if len(after) else None,
                         repairs=o.repairs,projections=o.projections))
    folder=RESULTS/'openloop_traces';folder.mkdir(exist_ok=True)
    np.savez_compressed(folder/f'{case}__{seed}.npz',true=np.array(true_trace),**{k:np.array(v) for k,v in est_trace.items()})
    return rows

def save_metrics(rows,path):
    dump(path.with_suffix('.json'),rows)
    flat=[]
    for r in rows:flat.append({k:v for k,v in r.items() if not isinstance(v,(list,dict,np.ndarray))})
    keys=list(dict.fromkeys(k for r in flat for k in r))
    with path.with_suffix('.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(flat)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=6);ap.add_argument('--smoke',action='store_true');ap.add_argument('--openloop',action='store_true');args=ap.parse_args()
    lib=compile_models();protocol=specification();dump(RESULTS/'protocol.json',protocol)
    h=hashlib.sha256(json.dumps(protocol,sort_keys=True,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x).encode())
    for file in sorted(WEIGHTS.glob('*.json')):h.update(file.read_bytes())
    for file in sorted(HERE.glob('*.py')):
        if file.name not in ['report.py','audit.py']:h.update(file.read_bytes())
    signature=h.hexdigest();jobs=[(case,c['estimator'],c['prediction'],c['mode'],con,seed) for case in CASES for c in CONFIGS for con in [False,True] for seed in SEEDS]
    if args.smoke:jobs=[('benzene_50',c['estimator'],c['prediction'],c['mode'],True,9001) for c in CONFIGS]
    rows=[];start=time.perf_counter()
    if args.openloop:
        ojobs=[(case,seed) for case in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise'] for seed in SEEDS]
        with mp.get_context('fork').Pool(args.workers,initializer=init_worker,initargs=(lib,signature)) as pool:
            for r in pool.starmap(openloop,ojobs):rows.extend(r)
        save_metrics(rows,RESULTS/'metrics_openloop');print('Open-loop runs',len(rows),'seconds',time.perf_counter()-start,flush=True);return
    with mp.get_context('fork').Pool(args.workers,initializer=init_worker,initargs=(lib,signature)) as pool:
        for i,r in enumerate(pool.imap_unordered(run,jobs,chunksize=1)):
            rows.append(r)
            if (i+1)%8==0 or i+1==len(jobs):
                print('Runs',i+1,'/',len(jobs),'complete',sum(q['status']=='complete' for q in rows),
                      'fallbacks',sum(q['fallbacks'] for q in rows),'wall_s',round(time.perf_counter()-start,1),flush=True)
    rows.sort(key=lambda r:r['name']);save_metrics(rows,RESULTS/('metrics_smoke' if args.smoke else 'metrics'))

if __name__=='__main__':main()
