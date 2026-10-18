"""Re-execute dissertation trajectories; truth is retained only by this evaluator.

Each controller receives the commanded inputs and noisy [T,Tt], not the hidden
input noise or concentrations. Setpoint preview is the known scheduled recipe,
as in the recovered Simulink Reference generator.
"""
import argparse,json,time,hashlib,traceback,csv
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from .physics import Model,NP,transition,njit,STATE_NAMES,LEGACY_RHO
from .data import Record
from .observers import OnlineUKF,observe
from .discovery import discover,GuardedDarwin,paired_interval
from .detection import calibrate_threshold
from .experiments import savejson,savecsv
from .thesis_cases import *
from .thesis_control import ThesisNMPC,compile_kernel

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts'/'thesis'
METHODS=('UKF_Euler','UKF_RK4','Darwin')
NOMINAL=Model(variant=1)

@njit(cache=True)
def plant_segment(x,u,dt):
    n=max(1,int(np.ceil(dt/.0025)));h=dt/n;z=x.copy();peak=x[4];over=0.;dose=0.
    for j in range(n):
        a=z[4];z=transition(z,u,np.zeros(NP),h,1,1);b=z[4];peak=max(peak,b)
        dose+=h*(max(a-T_LIMIT,0)+max(b-T_LIMIT,0))/2
        if a>T_LIMIT and b>T_LIMIT:over+=h
        elif (a>T_LIMIT)!=(b>T_LIMIT):over+=h*(max(a,b)-T_LIMIT)/max(abs(a-b),1e-15)
    return z,peak,over,dose

def advance(x,scenario,start,end,mw,noise):
    boundaries=[start,end]+[e[0] for e in scenario.events if start+1e-10<e[0]<end-1e-10]
    b=(np.floor(start/.1+1e-8)+1)*.1
    if b<end-1e-10:boundaries.append(b)
    boundaries=sorted(set(boundaries));peak=x[4];over=0.;dose=0.;acc=np.zeros(6)
    for a,b in zip(boundaries[:-1],boundaries[1:]):
        mid=(a+b)/2;u,_=commanded(scenario,mid)
        if scenario.kind!='open':u[3]=mw
        u+=noise[min(int(np.floor(mid/.1+1e-8)),len(noise)-1)]
        x,pk,ov,ex=plant_segment(x,u,b-a);peak=max(peak,pk);over+=ov;dose+=ex;acc+=(b-a)*u
    return x,peak,over,dose,acc/(end-start)

def commissioning_episode(seed,steps=240):
    rng=np.random.default_rng(seed);u=np.tile(U_NOM,(steps,1))
    levels=rng.uniform(230.,1000.,int(np.ceil(steps/20)))
    u[:,3]=np.repeat(levels,20)[:steps]
    u[:,0]*=np.repeat(rng.uniform(.95,1.05,len(levels)),20)[:steps]
    u[:,4]+=np.repeat(rng.uniform(-1.,1.,len(levels)),20)[:steps]
    noise=rng.normal(size=(int(steps*.015/.1)+2,6))*INPUT_STD
    x=X_NOM.copy();truth=[x.copy()]
    for k in range(steps):
        actual=u[k]+noise[int(k*.015/.1+1e-8)]
        x=transition(x,actual,np.zeros(NP),.015,6,1);truth.append(x.copy())
    truth=np.array(truth);y=truth[:,4:]+rng.normal(size=(steps+1,2))*np.sqrt(R_HIST)
    return Record(seed,u,y),truth

def fit_commissioning():
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    for seed in list(range(310000,310012))+list(range(320000,320008)):
        rec,truth=commissioning_episode(seed);records.append(rec)
        p=OUT/'commissioning'/f'{seed}.npz';p.parent.mkdir(exist_ok=True)
        np.savez_compressed(p,inputs=rec.inputs,measurements=rec.measurements,truth_evaluation_only=truth)
    cal=[commissioning_episode(seed)[0] for seed in range(330000,330020)]
    options=observer_options(X_NOM)
    threshold,details=calibrate_threshold([observe(r,NOMINAL,**options) for r in cal])
    savejson(OUT/'calibration.json',dict(threshold=threshold,details=details,seeds=list(range(330000,330020))))
    result=discover(records[:12],records[12:],threshold=threshold,variant=1,observer_options=options)
    result['commissioning_notes']='Original historical physics, no injected defect. Input noise is hidden from identification. New calibration is independent of final dissertation scenarios.'
    savejson(OUT/'discovery.json',result)
    print(json.dumps(dict(selected=result['selected'],accepted=result['accepted'],gain=result['relative_gain'],paired_CI=result['paired_CI'],threshold=threshold)),flush=True)
    return result

def make_observer(method,x0,discovery):
    opts=observer_options(x0,1 if method=='UKF_Euler' else 0)
    if method=='Darwin':return GuardedDarwin(discovery,nominal_model=NOMINAL,observer_options=opts)
    return OnlineUKF(NOMINAL,**opts)

def rollout(scenario_key,method,thermal,seed,discovery,save=True):
    scenario=BY_KEY[scenario_key];times=time_grid(scenario.hours);n=len(times)-1
    rng=np.random.default_rng(seed)
    input_noise=rng.normal(size=(int(scenario.hours/.1)+3,6))*INPUT_STD
    measurement_noise=rng.normal(size=(n+1,2))*np.sqrt(R_HIST)
    x=initial_state(scenario);obs=make_observer(method,x,discovery)
    ctl=ThesisNMPC(thermal) if scenario.kind!='open' else None
    xs=np.empty((n+1,6));xh=xs.copy();std=xs.copy();ys=np.empty((n+1,2));us=np.empty((n,6));ua=us.copy()
    innovation=np.full((n+1,2),np.nan);nis=np.zeros(n+1);refs=np.array([commanded(scenario,t)[1] for t in times]);mw=np.full(n,U_NOM[3])
    solver_success=np.ones(n,dtype=bool);iterations=np.zeros(n);fallback=np.zeros(n,dtype=bool);solver_ms=np.zeros(n)
    xs[0]=x;xh[0]=x;std[0]=np.sqrt(P_HIST);ys[0]=x[4:]+measurement_noise[0]
    peak=x[4];over=0.;dose=0.;start=time.perf_counter()
    for k in range(n):
        u,sp=commanded(scenario,times[k]);model=obs.active.model if method=='Darwin' else NOMINAL
        if ctl:
            # The reference schedule is known; future disturbances are not previewed.
            future=np.array([commanded(scenario,times[k]+(j+1)*.015)[1] for j in range(57)])
            mw[k],info=ctl.action(xh[k],u,sp,model,future)
            solver_success[k]=info['solver_success'];iterations[k]=info['iterations'];fallback[k]=info['fallback'];solver_ms[k]=info['solver_ms'];u[3]=mw[k]
        else:mw[k]=u[3]
        us[k]=u
        x,pk,ov,ex,ua[k]=advance(x,scenario,times[k],times[k+1],mw[k],input_noise)
        peak=max(peak,pk);over+=ov;dose+=ex;xs[k+1]=x;ys[k+1]=x[4:]+measurement_noise[k+1]
        xh[k+1],diagnostic=obs.update(u,ys[k+1],times[k+1]-times[k])
        current=obs.active if method=='Darwin' else obs
        std[k+1]=np.sqrt(np.maximum(np.diag(current.P)[:6],0));innovation[k+1]=diagnostic['innovation'];nis[k+1]=diagnostic['nis']
        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(xh[k+1])) or np.min(x[:4])<-1e-8:raise FloatingPointError(f'Nonphysical trajectory: {scenario_key}/{method}/{seed}/{k}')
    error=xh-xs;track=xs[:,2]-refs
    row=dict(scenario=scenario_key,method=method,thermal=('open' if not ctl else ('soft' if thermal else 'none')),seed=seed,hours=scenario.hours,
             RMSE_track_CC=float(np.sqrt(np.mean(track**2))),IAE_track_CC=float(np.trapezoid(abs(track),times)),
             ISE_track_CC=float(np.trapezoid(track**2,times)),T_peak_K=float(peak),T_above_limit_h=float(over),thermal_excess_Kh=float(dose),
             solver_success_fraction=float(solver_success.mean()),solver_fallbacks=int(fallback.sum()),solver_mean_ms=float(solver_ms.mean()),
             simulation_seconds=time.perf_counter()-start,observer_reverts=int(obs.fallbacks) if method=='Darwin' else 0,
             nominal_retained=not bool(discovery['accepted']) if method=='Darwin' else True)
    for j,name in enumerate(STATE_NAMES):
        row['RMSE_est_'+name]=float(np.sqrt(np.mean(error[:,j]**2)))
        row['IAE_est_'+name]=float(np.trapezoid(abs(error[:,j]),times))
    row['effort_sum_delta_mw2']=float(np.sum(np.diff(np.r_[U_NOM[3],mw])**2))
    flow=ua[:,0]/LEGACY_RHO[0]+ua[:,1]/LEGACY_RHO[1]+ua[:,2]/LEGACY_RHO[2]
    row['production_kmol']=float(np.sum(flow*(xs[:-1,2]+xs[1:,2])/2*np.diff(times)))
    if save:
        folder=OUT/'trajectories'/scenario_key;folder.mkdir(parents=True,exist_ok=True)
        path=folder/f'{method}_{row["thermal"]}_{seed}.npz'
        np.savez_compressed(path,t=times,truth=xs,estimate=xh,std=std,measurements=ys,input_commanded=us,input_actual_evaluation_only=ua,
                            reference=refs,mw=mw,innovation=innovation,nis=nis,solver_success=solver_success,iterations=iterations,fallback=fallback,solver_ms=solver_ms)
        row['trajectory']=str(path.relative_to(OUT))
        if method=='Darwin' and obs.events:savejson(folder/f'events_{row["thermal"]}_{seed}.json',obs.events)
    return row

def task(args):
    scenario,method,thermal,seed,discovery=args
    try:return dict(ok=True,row=rollout(scenario,method,thermal,seed,discovery))
    except Exception:return dict(ok=False,task=[scenario,method,thermal,seed],error=traceback.format_exc())

def run_campaign(n=20,workers=4):
    discovery=json.loads((OUT/'discovery.json').read_text(encoding='utf-8'))
    tasks=[]
    for i,s in enumerate(SCENARIOS):
        for thermal in ([False] if s.kind=='open' else [False,True]):
            for method in METHODS:
                for j in range(n):tasks.append((s.key,method,thermal,410000+i*1000+j,discovery))
    protocol=dict(version='1.1.0-thesis',created_before_main_campaign=True,scenarios=[s.as_dict() for s in SCENARIOS],n=n,methods=list(METHODS),
        controls=['none','soft penalty QR=1000'],primary_model='complete historical SI transform',hidden_structural_mismatch=False,
        baseline_source_commit='173f10932031e1b7b453bb77ad57a249889a75ab',Ts=.015,p=57,m=6,controller_integration_substeps=1,
        controller_solver='SciPy SLSQP with exact CasADi gradient',setpoint_preview=True,future_disturbance_preview=False,
        Qe=.8,Rdu=.2,Q_process=Q_HIST.tolist(),R_measurement=R_HIST.tolist(),P0=P_HIST.tolist(),alpha=1e-3,
        input_noise_sd=INPUT_STD.tolist(),input_noise_hold_h=.1,measurement_noise_hold_h=.015,thermal_limit_K=T_LIMIT,
        thermal_limit_label='160°F; dissertation rounded this to 344 K',noise_seed_formula='410000 + scenario_index*1000 + replicate',
        metric_definitions={'RMSE_est':'sqrt(mean((estimated-state - true-state)^2)), complete trajectory including startup',
        'RMSE_track_CC':'sqrt(mean((true CC - scheduled CC reference)^2))','IAE_track_CC':'trapezoidal integral of abs(true CC-reference) in kmol h/m3',
        'IAE_est':'trapezoidal integral of abs(estimated-state - true-state)','thermal_violation':'fine plant integration, h above 160°F, no measurement-noise threshold'},
        qualification='Scenario reconstruction, not bitwise reproduction of MATLAB runs. Figure 25 temperature axis inconsistent; use archived 60°F nominal. Open-loop IAE tracks departure from nominal, not a controlled loop.')
    savejson(OUT/'protocol.json',protocol)
    rows=[];failures=[];started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(task,t) for t in tasks]
        for f in as_completed(futures):
            a=f.result();rows.append(a['row']) if a['ok'] else failures.append(a)
            done=len(rows)+len(failures)
            if done%30==0 or done==len(tasks):
                savecsv(OUT/'metrics_partial.csv',rows);savejson(OUT/'failures.json',failures)
                print(f'{done}/{len(tasks)} tasks; failures={len(failures)}; elapsed={time.perf_counter()-started:.1f}s',flush=True)
    rows.sort(key=lambda r:(r['scenario'],r['thermal'],r['method'],r['seed']))
    savecsv(OUT/'metrics.csv',rows);savejson(OUT/'failures.json',failures)
    savejson(OUT/'execution.json',dict(tasks=len(tasks),completed=len(rows),failed=len(failures),seconds=time.perf_counter()-started,n=n))
    if failures:raise RuntimeError(f'{len(failures)} experiment failures; retained in failures.json')
    summarize()

def summarize():
    rows=list(csv.DictReader((OUT/'metrics.csv').open(encoding='utf-8')));summary=[];paired=[]
    keys=['RMSE_track_CC','IAE_track_CC','T_peak_K','T_above_limit_h','thermal_excess_Kh','solver_mean_ms']+['RMSE_est_'+x for x in STATE_NAMES]+['IAE_est_'+x for x in STATE_NAMES]
    groups=sorted({(r['scenario'],r['thermal'],r['method']) for r in rows})
    for sc,th,m in groups:
        group=[r for r in rows if (r['scenario'],r['thermal'],r['method'])==(sc,th,m)]
        out=dict(scenario=sc,thermal=th,method=m,n=len(group))
        for key in keys:
            vals=np.array([float(r[key]) for r in group]);ci=paired_interval(vals,seed=20261018)
            out[key]=float(vals.mean());out[key+'_lo']=ci[0];out[key+'_hi']=ci[1]
        out['violation_episodes']=sum(float(r['T_above_limit_h'])>1e-8 for r in group)
        summary.append(out)
        if m=='Darwin':
            for baseline in ['UKF_Euler','UKF_RK4']:
                base={int(r['seed']):r for r in rows if (r['scenario'],r['thermal'],r['method'])==(sc,th,baseline)}
                for key in ['IAE_track_CC','RMSE_track_CC','RMSE_est_CC']:
                    delta=np.array([float(base[int(r['seed'])][key])-float(r[key]) for r in group]);ci=paired_interval(delta,seed=20261018)
                    avg=np.mean([float(base[int(r['seed'])][key]) for r in group])
                    paired.append(dict(scenario=sc,thermal=th,baseline=baseline,metric=key,n=len(group),mean_difference=float(delta.mean()),CI_lo=ci[0],CI_hi=ci[1],gain_percent=float(100*delta.mean()/max(avg,1e-15))))
    savecsv(OUT/'summary.csv',summary);savecsv(OUT/'paired_comparisons.csv',paired)
    savejson(OUT/'summary.json',dict(groups=summary,paired=paired))
    return summary,paired

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['fit','compile','pilot','run','summary'],required=True);ap.add_argument('--n',type=int,default=20);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    if args.stage=='compile':compile_kernel()
    elif args.stage=='fit':fit_commissioning()
    elif args.stage=='pilot':
        d=json.loads((OUT/'discovery.json').read_text(encoding='utf-8')) if (OUT/'discovery.json').exists() else dict(accepted=False)
        rows=[rollout(sc,m,th,400001,d) for sc in ['CL_START','REG_FA15','SERVO_P20'] for th in [False,True] for m in METHODS]
        savecsv(OUT/'pilot_metrics.csv',rows);print(json.dumps(rows,indent=2))
    elif args.stage=='run':run_campaign(args.n,args.workers)
    else:summarize()

if __name__=='__main__':main()
