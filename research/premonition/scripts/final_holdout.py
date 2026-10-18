from pathlib import Path
import sys,json,time
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from premonition.detection_campaign import observe_episode,evaluate,attach_models
from premonition.detectors import load_models
from premonition.evaluation import alarm_metrics,paired_ci
from premonition.io import save,csv_write,sha
out=Path(__file__).resolve().parents[1]/'results/CD';start=time.perf_counter();models=load_models(out/'models');th=json.loads((out/'thresholds.json').read_text())
save(out/'holdout_freeze.json',{'model_hashes':{f.name:sha(f) for f in (out/'models').glob('*.json')},'threshold_hash':sha(out/'thresholds.json'),'test_seeds':[300000,300099],'falsification_seeds':[400000,400099],'reason':'Keep all final evaluation seeds disjoint from pilot and exploratory evaluation; no refitting or threshold changes.'})
groups=[];allsum={};allprob={};allrows=[];failures=[];paired={};selected=[]
for label,base,adv in [('test',300000,False),('falsification',400000,True)]:
 eps=[]
 for i in range(100):
  eps.append(observe_episode(base+i,adversarial=adv))
  if (i+1)%20==0:print(label,i+1,flush=True)
 attach_models(eps,models);groups.append(eps);rows,s,p=evaluate(eps,th);allsum[label]=s;allprob[label]=p;allrows.extend([dict(split=label,**r) for r in rows]);csv_write(out/f'{label}_estimation.csv',[{k:e[k] for k in ['seed','kind','rmse_CC','rmse_alpha','failures']} for e in eps])
 np.savez_compressed(out/f'{label}.npz',features=np.array([e['features'] for e in eps]),truth=np.array([e['truth'] for e in eps]),xhat=np.array([e['xhat'] for e in eps]),y=np.array([e['y'] for e in eps]),valid=np.array([e['valid'] for e in eps]),label=np.array([e['label'] for e in eps]),scores=np.array([[e['scores'][name] for name in th] for e in eps]),seed=np.array([e['seed'] for e in eps]),detector_names=np.array(list(th)))
 l0=[];l1=[]
 for e in eps:
  mask=e['valid'];yt=e['label'][mask]
  if mask.any():
   l0.append(np.mean((yt-e['scores']['D5_noEWS'][mask])**2));l1.append(np.mean((yt-e['scores']['D5'][mask])**2))
  m=alarm_metrics(e['scores']['D5'],e['event'],e['valid'],th['D5'])
  if m['false_onsets'] or m['missed']:failures.append(dict(seed=e['seed'],kind=e['kind'],**m))
 paired[label+'_brier_full_minus_noEWS']=paired_ci(l0,l1)
 for kind in dict.fromkeys(e['kind'] for e in eps):selected.append(next(e for e in eps if e['kind']==kind))
ablations=[]
for mode in ['rk4','adaptive','ekf']:
 for e in groups[0]:
  alt=observe_episode(e['seed'],models,mode=mode);mm=alarm_metrics(alt['scores']['D5'],alt['event'],alt['valid'],th['D5']);ablations.append(dict(seed=e['seed'],mode=mode,rmse_CC=alt['rmse_CC'],rmse_alpha=alt['rmse_alpha'],failures=alt['failures'],**mm))
 print('ablation',mode,flush=True)
csv_write(out/'ablations.csv',ablations);save(out/'paired.json',paired);csv_write(out/'detection_metrics.csv',allrows);save(out/'summary.json',allsum);save(out/'probability.json',allprob);save(out/'failure_cases.json',failures);save(out/'traces.json',selected)
e=json.loads((out/'execution.json').read_text());e['split_seeds'][2]=[x['seed'] for x in groups[0]];e['split_seeds'][3]=[x['seed'] for x in groups[1]];e['final_holdout_seconds']=time.perf_counter()-start;e['final_holdout']='No model or threshold tuning after freeze';save(out/'execution.json',e)
