from pathlib import Path
import time,json
import numpy as np
from .physics import *
from .observer import UKF,Observation
from .detectors import *
from .scenarios import specification,open_loop
from .evaluation import *
from .io import save,csv_write

def observe_episode(seed,models=None,adversarial=False,mode='historical'):
    spec=specification(seed,adversarial=adversarial);truth,y=open_loop(spec);obs=UKF(mode=mode);det=Detectors(models);features=[];scores={};xh=[];unc=[];alpha_truth=[]
    for k in range(len(y)):
        x,Pc=obs.advance(spec['known'][k],y[k]);packet=Observation(y[k],spec['known'][k],x,Pc,obs.innov,obs.nis);r=det.update(packet)
        features.append(r['features']);xh.append(x);unc.append(np.diag(Pc));alpha_truth.append(reactive_alpha(truth[k],spec['actual'][k],spec['params'][k]))
        for name,v in r['scores'].items():scores.setdefault(name,[]).append(v)
    lab,valid,ev=future_labels(truth[:,4]);features=np.array(features);xh=np.array(xh)
    # Warm-up is excluded for all detectors for matched exposure.
    valid[:31]=False
    return dict(seed=seed,kind=spec['kind'],features=features,scores={k:np.array(v) for k,v in scores.items()},label=lab,valid=valid,event=ev,
                truth=truth,y=y,xhat=xh,cov_diag=np.array(unc),known=spec['known'],alpha_truth=np.array(alpha_truth),
                rmse_CC=float(np.sqrt(np.mean((truth[:,2]-xh[:,2])**2))),rmse_alpha=float(np.sqrt(np.mean((np.array(alpha_truth)-features[:,4])**2))),failures=obs.failures)

def training_arrays(eps):return np.vstack([e['features'][e['valid']] for e in eps]),np.concatenate([e['label'][e['valid']] for e in eps])
def attach_models(eps,models):
    for e in eps:
        for name,m in models.items():e['scores'][name]=m.predict(e['features'])

def evaluate(eps,thresholds):
    rows=[];summary={};probs={}
    for name in eps[0]['scores']:
        for e in eps:rows.append(dict(seed=e['seed'],kind=e['kind'],detector=name,**alarm_metrics(e['scores'][name],e['event'],e['valid'],thresholds[name])))
        summary[name]=aggregate([r for r in rows if r['detector']==name])
        if name in ['D4','D5','D5_noEWS']:
            y=np.concatenate([e['label'][e['valid']] for e in eps]);p=np.concatenate([e['scores'][name][e['valid']] for e in eps]);probs[name]=probability_metrics(y,p)
    return rows,summary,probs

def campaign_CD(out,pilot=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);start=time.perf_counter()
    counts=[24,16,12,12] if pilot else [160,80,100,100]
    groups=[]
    for label,base,n in zip(['train','calibration','test','falsification'],[10000,20000,300000,400000],counts):
        eps=[]
        for i in range(n):
            eps.append(observe_episode(base+i,adversarial=label=='falsification'))
            if (i+1)%20==0:print(json.dumps(dict(stage=label,done=i+1,n=n)),flush=True)
        groups.append(eps)
    train,cal,test,adv=groups;X,y=training_arrays(train);Xc,yc=training_arrays(cal)
    models={'D4':train_model(X,y,Xc,yc,'logistic'), 'D5':train_model(X,y,Xc,yc), 'D5_noEWS':train_model(X,y,Xc,yc,indices=NOEWS)}
    for name,m in models.items():save(out/'models'/f'{name}.json',m.d)
    for eps in groups:attach_models(eps,models)
    th={'D0':0.,'D1':0.};cal_summary={}
    for name in ['D2','D3','D4','D5','D5_noEWS']:th[name],cal_summary[name]=choose_threshold(cal,name)
    save(out/'thresholds.json',th);save(out/'calibration_selection.json',cal_summary)
    allsum={};allprob={};allrows=[]
    for label,eps in [('test',test),('falsification',adv)]:
        rows,s,p=evaluate(eps,th);allsum[label]=s;allprob[label]=p;allrows.extend([dict(split=label,**r) for r in rows])
        csv_write(out/f'{label}_estimation.csv',[{k:e[k] for k in ['seed','kind','rmse_CC','rmse_alpha','failures']} for e in eps])
        # Lossless numeric archives for all test features, probabilities, labels and truth.
        np.savez_compressed(out/f'{label}.npz',features=np.array([e['features'] for e in eps]),truth=np.array([e['truth'] for e in eps]),xhat=np.array([e['xhat'] for e in eps]),y=np.array([e['y'] for e in eps]),valid=np.array([e['valid'] for e in eps]),label=np.array([e['label'] for e in eps]),scores=np.array([[e['scores'][name] for name in th] for e in eps]),seed=np.array([e['seed'] for e in eps]),detector_names=np.array(list(th)))
    # Estimator ablation uses the identical independent test episodes, never changes plant/noise.
    ablations=[]
    for mode in ['rk4','adaptive','ekf']:
        for i,e in enumerate(test):
            alt=observe_episode(e['seed'],models,mode=mode)
            mm=alarm_metrics(alt['scores']['D5'],alt['event'],alt['valid'],th['D5'])
            ablations.append(dict(seed=e['seed'],mode=mode,rmse_CC=alt['rmse_CC'],rmse_alpha=alt['rmse_alpha'],failures=alt['failures'],**mm))
        print(json.dumps(dict(stage='estimator_ablation',mode=mode,n=len(test))),flush=True)
    csv_write(out/'ablations.csv',ablations)
    paired={}
    for label,eps in [('test',test),('falsification',adv)]:
        l0=[];l1=[]
        for e in eps:
            mask=e['valid'];yt=e['label'][mask]
            if not mask.any():continue
            l0.append(np.mean((yt-e['scores']['D5_noEWS'][mask])**2));l1.append(np.mean((yt-e['scores']['D5'][mask])**2))
        paired[label+'_brier_full_minus_noEWS']=paired_ci(l0,l1)
    save(out/'paired.json',paired);csv_write(out/'detection_metrics.csv',allrows);save(out/'summary.json',allsum);save(out/'probability.json',allprob)
    failures=[]
    for e in test+adv:
        m=alarm_metrics(e['scores']['D5'],e['event'],e['valid'],th['D5'])
        if m['false_onsets'] or m['missed']:failures.append(dict(seed=e['seed'],kind=e['kind'],**m))
    save(out/'failure_cases.json',failures)
    selected=[]
    for eps in [test,adv]:
        for kind in dict.fromkeys(e['kind'] for e in eps):selected.append(next(e for e in eps if e['kind']==kind))
    save(out/'traces.json',selected)
    protocol=dict(counts=counts,split_seeds=[[e['seed'] for e in eps] for eps in groups],train_rows=len(y),train_events=int(y.sum()),calibration_rows=len(yc),seconds=time.perf_counter()-start,
                  label='thermal first crossing, 20-sample horizon',note='Probability calibrated on calibration only; false-alarm and recall tested on whole unseen trajectories.')
    save(out/'execution.json',protocol);return allsum
