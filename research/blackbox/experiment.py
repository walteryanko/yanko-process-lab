"""Paired closed-loop experiment. Independent DOP853 plant; no truth feedback."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from time import perf_counter
from pathlib import Path
import argparse,csv,json,platform,sys
import numpy as np
import scipy,sklearn,casadi
from scipy.integrate import solve_ivp
from common import *
from control import build_step,CompiledTransition,BlackBoxNAKE,NMPC
from protocol import CASES,CONFIGS,inputs

def score(case,kind,constrained,seed,rows,errors,covs,nis,times,stop,elapsed,margin=0.):
    a=np.asarray(rows);e=np.asarray(errors);pp=np.asarray(covs)
    t=a[:,0];dt=a[:,1];tracking=a[:,4]-a[:,3]
    sd=np.sqrt(pp[:,2,2]);cover=float(np.mean(abs(e[:,2])<=1.96*sd))
    nees=[float(v@np.linalg.solve(p,v)) for v,p in zip(e,pp)]
    return dict(case=case,configuration=kind,constrained=bool(constrained),seed=seed,margin_K=margin,
      completed=stop is None,stop_reason=stop,completed_h=float(t[-1]),steps=len(t),
      IAE=float(np.sum(abs(tracking)*dt)),ISE=float(np.sum(tracking**2*dt)),
      ITAE=float(np.sum(t*abs(tracking)*dt)),ITSE=float(np.sum(t*tracking**2*dt)),
      post_event_IAE=float(np.sum(abs(tracking)*dt*(t>(CASES[case]['on'] or 0.)))),
      max_tracking_deviation_pct=float(100*np.max(abs(tracking))/BASE[2]),
      steady_CC_error=float(np.mean(tracking[-min(67,len(t)):])),
      CC_estimation_RMSE=float(np.sqrt(np.mean(e[:,2]**2))),
      state_estimation_RMSE=np.sqrt(np.mean(e**2,axis=0)),CC_coverage95=cover,
      NEES_mean=float(np.mean(nees)),NIS_mean=float(np.nanmean(nis)),
      T_max=float(max(np.max(a[:,7]),np.max(a[:,9]))),
      thermal_violation_K=float(max(0,np.max(a[:,9])-T_LIMIT)),
      time_above344_h=float(np.sum(a[:,10])),
      thermal_violation_integral_Kh=float(np.sum(a[:,11])),
      mw_min=float(np.min(a[:,2])),mw_max=float(np.max(a[:,2])),
      coolant_total_kmol=float(np.sum(a[:,2]*dt)),
      control_TV_kmol_h=float(np.sum(abs(np.diff(np.r_[U_BASE[3],a[:,2]])))),
      normalized_control_effort=float(np.sum((np.diff(np.r_[U_BASE[3],a[:,2]])/U_BASE[3])**2)),
      solver_failure_count=int(np.sum(a[:,12]==0)),fallback_count=int(np.sum(a[:,13])),
      estimator_covariance_repairs=int(a[-1,16]),
      solver_latency_median_ms=float(np.median(a[:,14])),solver_latency_p95_ms=float(np.percentile(a[:,14],95)),
      estimator_latency_median_ms=float(np.median(times)),
      adaptive_Q_factor_max=float(np.max(a[:,15])),wall_seconds=elapsed)

TRACE_FIELDS=['time_h','duration_h','mw','CC_ref','CC_true','CC_est','T_est','T_true','Tt_true',
              'T_peak_interval','time_above344_h','violation_integral_Kh','solver_success','fallback',
              'solver_ms','adaptive_Q_factor','covariance_repairs','T_pred_max']

def run_job(job):
    case,kind,constrained,seed,margin=job;c=CASES[case];cfg=CONFIGS[kind]
    n=round(c['duration']/DT);rng=np.random.default_rng(seed)
    # Generated in advance: identical realizations despite adaptive control actions.
    process_noise=rng.normal(size=(n,6))*.01;measurement_noise=rng.normal(size=(n,2))*.01*BASE[4:]
    true=cold_state() if case=='startup' else BASE.copy()
    x0=true+rng.normal(size=6)*np.array([.03,.12,.03,.06,.2,.2])
    net=NeuralTransition.load();physical=build_step('physical')
    neural=build_step('neural',net);predictor=neural if cfg['controller']=='neural' else physical
    estimator=BlackBoxNAKE(x0,CompiledTransition(neural),net) if cfg['estimator']=='nake' else UKF(
        x0,q=Q_COMMON,r=R_HISTORICAL,transition_model=CompiledTransition(physical))
    controller=NMPC(predictor,constrained,margin=margin,network=net if cfg['controller']=='neural' else None)
    rows=[];errors=[];covs=[];nis=[];times=[];stop=None;start=perf_counter()
    for k in range(n):
        t=k*DT;command,sp=inputs(case,t)
        try:
            mw,info=controller.step(estimator.x,command,sp);command[3]=mw
            plant_input=command*(1+process_noise[k]);plant_input[3]=np.clip(plant_input[3],MW_MIN,MW_MAX)
            def thermal_event(tt,xx):return xx[4]-T_STOP
            thermal_event.terminal=True;thermal_event.direction=1
            sol=solve_ivp(lambda tt,xx:rhs6(xx,plant_input),(0,DT),true,method='DOP853',
                rtol=2e-10,atol=1e-11,dense_output=True,events=thermal_event)
            if not sol.success:stop='plant_integration: '+sol.message;break
            duration=float(sol.t[-1]);subt=np.linspace(0,duration,21);substates=sol.sol(subt);true=sol.y[:,-1]
            measured=true[4:]+measurement_noise[k]
            st=perf_counter();estimate,p,inn,_=estimator.update(command,measured);times.append(1000*(perf_counter()-st))
            peak=float(np.max(substates[4]));viol=np.maximum(0,substates[4]-T_LIMIT)
            above=float(np.trapezoid((substates[4]>T_LIMIT+1e-3).astype(float),subt))
            integral=float(np.trapezoid(viol,subt))
            rows.append([t+duration,duration,mw,sp,true[2],estimate[2],estimate[4],true[4],true[5],peak,
                above,integral,int(info['solver_success']),int(info['fallback']),info['latency_ms'],
                getattr(estimator,'factor',1.),estimator.repairs,info['predicted_Tmax']])
            errors.append(estimate-true);covs.append(p);nis.append(inn)
            if len(sol.t_events[0]):stop='practical_temperature_355.4_K';break
            if np.any(true[:4]<-1e-7):stop='negative_plant_concentration';break
        except (ValueError,FloatingPointError,np.linalg.LinAlgError,RuntimeError) as ex:
            stop=type(ex).__name__+': '+str(ex);break
    tag=f'{case}__{kind}__{"on" if constrained else "off"}__{seed}'
    if margin:tag+=f'__margin{margin:g}'
    # All traces persisted as text with exact protocol tags; never silently omit failures.
    path=RESULTS/'traces'/f'{tag}.csv';path.parent.mkdir(exist_ok=True)
    with path.open('w',newline='') as f:
        wr=csv.writer(f,lineterminator='\n');wr.writerow(TRACE_FIELDS);wr.writerows(rows)
    if not rows:
        metric=dict(case=case,configuration=kind,constrained=bool(constrained),seed=seed,margin_K=margin,
                    completed=False,stop_reason=stop,completed_h=0,steps=0)
    else:
        metric=score(case,kind,constrained,seed,rows,errors,covs,nis,times,stop,perf_counter()-start,margin)
    dump(RESULTS/'runs'/f'{tag}.json',metric)
    return metric

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seeds',type=int,default=3);ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--cases',nargs='*',default=list(CASES));ap.add_argument('--configs',nargs='*',default=list(CONFIGS))
    ap.add_argument('--constraints',choices=['both','on','off'],default='both');ap.add_argument('--margin',type=float,default=0.)
    ap.add_argument('--reuse',action='store_true');args=ap.parse_args()
    RESULTS.mkdir(exist_ok=True);(RESULTS/'runs').mkdir(exist_ok=True);(RESULTS/'traces').mkdir(exist_ok=True)
    seeds=list(range(8001,8001+args.seeds));constraints=[False,True] if args.constraints=='both' else [args.constraints=='on']
    jobs=[(c,k,on,s,args.margin) for c in args.cases for k in args.configs for on in constraints for s in seeds]
    protocol=dict(cases=CASES,configurations=CONFIGS,test_seeds=seeds,run_count=len(jobs),
      actual_cases=args.cases,actual_configurations=args.configs,Ts_h=DT,p=57,m=6,Qe=.8,Rdu=.2,
      thermal_limit_K=T_LIMIT,practical_stop_K=T_STOP,temperature_margin_K=args.margin,
      constraints='explicit hard prediction inequalities for T<=344-margin; all runs retain coolant bounds',
      bounds_mw_kmol_h=[MW_MIN,MW_MAX],solver='SciPy SLSQP with exact CasADi physical derivatives and analytic neural chain rule compiled in C, maxiter60 ftol1e-8',
      workers=args.workers,
      horizon_moves='first six consecutive samples optimized, last move held through prediction step57',
      disturbance_preview='none; future exogenous inputs and reference held at current commanded value',
      process_noise='independent unobserved multiplicative Gaussian 1% on all six inputs at each sample; actual mw clipped to bounds',
      measurement_noise='independent additive Gaussian std=1% nominal T and Tt, in kelvin',
      measurement_std_K=.01*BASE[4:],Q_common=Q_COMMON,R=R_HISTORICAL,
      Q_nake='Q_common + independent-validation one-step neural residual MSE, multiplied by EMA of previous NIS/dof bounded [1,25]',
      initial_state_nominal=BASE,initial_state_startup=cold_state(),
      initial_estimate_sd=[.03,.12,.03,.06,.2,.2],
      plant_integrator='DOP853 rtol2e-10 atol1e-11, independent of predictors; 21 dense temperature samples per interval',
      physical_predictor_integrator='RK4 five substeps per sample',
      temperature_stop_censoring='Stop at355.4K; incomplete trajectories not compared by smaller truncated IAE',
      metrics='sampled rectangle integral using CC_true minus active current reference, time in h; ITAE global time',
      reconstructing_historical=True,source='Brandao dissertation2019 sections5.3.1 and5.3.2; REV05 manuscript',
      calibration='effective enthalpy calibrated at one nominal point, not recovered physical enthalpy or Simulink source',
      effective_dH=P_ADJUSTED.dH,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
      sklearn=sklearn.__version__,casadi=casadi.__version__,platform=platform.platform())
    protocol_name='protocol.json' if args.margin==0 else 'protocol_margin.json';dump(RESULTS/protocol_name,protocol)
    records=[];pending=[]
    for job in jobs:
        c,k,on,s,margin=job;tag=f'{c}__{k}__{"on" if on else "off"}__{s}'
        if margin:tag+=f'__margin{margin:g}'
        path=RESULTS/'runs'/f'{tag}.json'
        if args.reuse and path.exists():records.append(json.loads(path.read_text()))
        else:pending.append(job)
    started=perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs={pool.submit(run_job,j):j for j in pending}
        for f in as_completed(futs):
            r=f.result();records.append(r)
            print(f"{len(records)}/{len(jobs)}",r['case'],r['configuration'],r['constrained'],r['seed'],
                  'IAE',round(r.get('IAE',0),6),'Tmax',round(r.get('T_max',0),3),'stop',r['stop_reason'],flush=True)
    records.sort(key=lambda r:(r['case'],r['configuration'],r['constrained'],r['seed']))
    name='metrics.json' if args.margin==0 else 'metrics_margin.json';dump(RESULTS/name,records)
    scalarfields=[k for r in records for k,v in r.items() if not isinstance(v,(dict,list))]
    scalarfields=list(dict.fromkeys(scalarfields))
    with (RESULTS/name.replace('.json','.csv')).open('w',newline='') as f:
        wr=csv.DictWriter(f,scalarfields,extrasaction='ignore',lineterminator='\n');wr.writeheader();wr.writerows(records)
    print('done',len(records),'elapsed_s',round(perf_counter()-started,2),flush=True)

if __name__=='__main__':main()
