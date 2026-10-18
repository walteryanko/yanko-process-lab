from pathlib import Path
import sys,json
import numpy as np
from scipy.special import expit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from premonition.bifurcation_campaign import trajectory
from premonition.evaluation import alarm_metrics,aggregate
from premonition.io import save,csv_write
root=Path(__file__).resolve().parents[1]/'results/B'
m=json.loads((root/'bifurcation_probability.json').read_text());th=json.loads((root/'thresholds.json').read_text());execution=json.loads((root/'execution.json').read_text());fold=execution['fold'];sens=json.loads((root/'sensitivity.json').read_text());traces=json.loads((root/'traces.json').read_text())
for j,rate,control in [(3,.5,False),(6,1.,True)]:
 eps=[trajectory(63000+j*100+i,fold,window=64,rate=rate,noise_scale=1.,control=control) for i in range(12)];sens=[s for s in sens if s['setting']!=j]
 for name in th:
  rr=[]
  for e in eps:
   f=e['features'];z=(f-np.array(m['mean']))/np.array(m['scale']);prob=expit(m['cal_a']*(z@np.array(m['coef'])+m['intercept'])+m['cal_b']);scores={'thermal_342':np.array([r['yT']-342 for r in e['rows']]),'EWS':f[:,0]+.12*f[:,1],'spectral':f[:,3],'hybrid_probability':prob}
   rr.append(alarm_metrics(scores[name],e['event'],e['valid'],th[name],H=80))
  sens.append(dict(setting=j,window=64,rate=rate,noise=1.,colored=False,control=control,**aggregate(rr),detector=name))
 traces[4+j]=eps[0]
 print('refined',j,flush=True)
execution['target_limitation']='Event is frozen deterministic mean-input fold; noisy plant can tip earlier or later. Oscillatory coolant sensitivity recomputes the instantaneous mean-input fold; slow ramps run longer to reach the same endpoint.'
execution['sensitivity_refinement']='Pre-publication correction to two exploratory sensitivity settings; models, thresholds and independent main test unchanged.'
save(root/'sensitivity.json',sens);csv_write(root/'sensitivity.csv',sens);save(root/'traces.json',traces);save(root/'execution.json',execution)
