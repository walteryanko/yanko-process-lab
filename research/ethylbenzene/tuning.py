"""Additional fair baseline: constant UKF Q chosen on held-out validation.

Existing main experiments are untouched. Q is selected from independent
open-loop validation, never from a closed-loop test score. Four additional
NMPC combinations then use that one constant Q in all test cases.
"""
import argparse,hashlib,json,multiprocessing as mp,time
import numpy as np
from model import *
from networks import NeuralTransition,LSTM
from compiled import Models,compile_models
from observer import Observer,Q_BASE
from protocol import CASES,SEEDS,specification
import experiment as exp

FACTORS=[.25,1.,4.,16.,64.,100.]
_BASE_OBSERVER=Observer

def validation_data(seed=4601,count=16,steps=160):
    rng=np.random.default_rng(seed);trajectories=[]
    for j in range(count):
        state=BASE+rng.normal(size=5)*[.01,.3,.15,.05,2.];cmd=U0.copy();kin=np.ones(3);loss=noise=1.
        commands=[];states=[];measurements=[]
        for i in range(steps):
            if i%25==0:
                cmd=U0.copy();cmd[:4]*=rng.uniform([.8,.8,.75,.9],[1.2,1.25,1.1,1.1]);cmd[4:]+=rng.uniform(-2,2,3)
            if i%40==0:kin=rng.uniform(.87,1.13,3);noise=rng.uniform(.5,2.);loss=rng.uniform(.93,1.07)
            actual=cmd.copy();actual[:4]*=1+rng.normal(0,.01*noise,4);actual[3]*=loss;actual[4:]+=rng.normal(0,.2,3)
            actual[0]=np.clip(actual[0],.04*F0[0],2.*F0[0]);actual[3]=max(0.,actual[3])
            state=transition(state,actual,multiplier=kin,substeps=16)
            commands.append(cmd.copy());states.append(state.copy());measurements.append(state[4]+rng.normal(0,1.5))
        trajectories.append((np.array(commands),np.array(states),np.array(measurements)))
    return trajectories

def select():
    models=Models();data=validation_data();scores=[]
    for factor in FACTORS:
        q=Q_BASE*factor;err=[];te=[]
        for commands,states,measurements in data:
            o=Observer(BASE+np.array([.006,.22,-.12,.04,1.5]),models)
            o.qbase=q.copy()
            for j,(u,x,y) in enumerate(zip(commands,states,measurements)):
                estimate,cov,nis=o.update(u,y)
                if j>=40:err.append(float(fraction(estimate)-fraction(x)));te.append(float(estimate[4]-x[4]))
        rmse=float(np.sqrt(np.mean(np.array(err)**2)));temp=float(np.sqrt(np.mean(np.array(te)**2)))
        score=(rmse/.001)**2+(temp/1.5)**2
        scores.append(dict(factor=factor,score=score,xEB_RMSE=rmse,T_RMSE_C=temp));print('UKF validation',scores[-1],flush=True)
    best=min(scores,key=lambda r:r['score']);q=Q_BASE*best['factor']
    result=dict(validation_seed=4601,validation_trajectories=16,steps=160,scored_after_step=40,
                objective='(xEB_RMSE/0.001)^2 + (T_RMSE/1.5 K)^2; independent validation only',
                candidate_factors=FACTORS,scores=scores,chosen_factor=best['factor'],constant_Q=q,
                extra_configs=4,extra_control_runs=144,extra_observer_runs=15,
                note='selected Q is identical in every control/test regime; control results never select it')
    dump(RESULTS/'tuning_ukf.json',result);return result

def tuned_factory(x0,models,kind='ukf',lstm=None,network=None):
    if kind=='ukf_tuned':
        o=_BASE_OBSERVER(x0,models,'ukf',lstm,network)
        o.qbase=np.array(json.loads((RESULTS/'tuning_ukf.json').read_text())['constant_Q']);return o
    return _BASE_OBSERVER(x0,models,kind,lstm,network)

def init(lib,signature):
    exp.init_worker(lib,signature);exp.Observer=tuned_factory;exp.KINDS=['ukf_tuned']

def init_openloop(lib,signature):
    init(lib,signature);exp.RESULTS=RESULTS/'ukf_tuned';exp.RESULTS.mkdir(exist_ok=True)

def run(workers=6):
    lib=compile_models();tuning=json.loads((RESULTS/'tuning_ukf.json').read_text())
    signature=hashlib.sha256((json.dumps(tuning,sort_keys=True)+'UKF-validation-baseline-v1'+json.dumps(specification(),default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x)).encode()).hexdigest()
    jobs=[(case,'ukf_tuned',p,m,con,seed) for case in CASES for p in ['physical','neural'] for m in ['siso','mimo'] for con in [False,True] for seed in SEEDS]
    rows=[];start=time.perf_counter()
    with mp.get_context('fork').Pool(workers,initializer=init,initargs=(lib,signature)) as pool:
        for i,r in enumerate(pool.imap_unordered(exp.run,jobs,chunksize=1)):
            rows.append(r)
            if (i+1)%8==0:print('Tuned UKF runs',i+1,'/',len(jobs),'seconds',round(time.perf_counter()-start,1),flush=True)
    rows.sort(key=lambda r:r['name']);exp.save_metrics(rows,RESULTS/'metrics_tuned')
    oj=[(case,seed) for case in ['servo_up','benzene_50','recycle_minus50','thermal_loss','kinetics_noise'] for seed in SEEDS]
    obs=[]
    with mp.get_context('fork').Pool(min(4,workers),initializer=init_openloop,initargs=(lib,signature)) as pool:
        for r in pool.starmap(exp.openloop,oj):obs.extend(r)
    exp.save_metrics(obs,RESULTS/'metrics_openloop_tuned')
    print('Tuned UKF finished',len(rows),'control runs and',len(obs),'observer runs',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--select-only',action='store_true');ap.add_argument('--run-only',action='store_true');ap.add_argument('--workers',type=int,default=6);a=ap.parse_args()
    if not a.run_only:select()
    if not a.select_only:run(a.workers)
