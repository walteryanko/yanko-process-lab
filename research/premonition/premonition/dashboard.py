from pathlib import Path
import json,gzip
import numpy as np
from .io import clean,save

def build(results='results',partial=False):
    root=Path(__file__).resolve().parents[1];results=Path(results)
    def read(p,default=None):
        q=results/p
        return json.loads(q.read_text()) if q.exists() else default
    control=[]
    for path in sorted((results/'EF/episodes').glob('*.json')):
        ep=json.loads(path.read_text());control.append(dict(**ep['metrics'],rows=ep['rows']))
    allmetrics=[{k:v for k,v in e.items() if k!='rows'} for e in control]
    selected_seeds=sorted(set(e['seed'] for e in control))[:12]
    control=[e for e in control if e['seed'] in selected_seeds]
    data=dict(controlMetrics=allmetrics,meta={'version':'1.0.0','model':'PG / MATLAB 2019 · SI','dt':.015,'partial':partial},audit=read('physical_audit.json'),map=read('A/map.json',{}),critical=read('A/critical_points.json',[]),B=read('B/summary.json',{}),Btraces=read('B/traces.json',[]),Bexecution=read('B/execution.json',{}),Bthresholds=read('B/thresholds.json',{}),
        detection=read('CD/summary.json',{}),probability=read('CD/probability.json',{}),detectionTraces=read('CD/traces.json',[]),failures=read('CD/failure_cases.json',[]),thresholds=read('CD/thresholds.json',{}),control=control,controlSummary=read('EF/summary.json',{}),paired=read('EF/paired.json',[]),execution=read('EF/execution.json',{}))
    # Include every tested detection episode for inspectable failure cases.
    all_detection=[]
    for split in ['test','falsification']:
        path=results/'CD'/f'{split}.npz'
        if not path.exists():continue
        with np.load(path) as z:
            for j,seed in enumerate(z['seed']):
                ev=np.flatnonzero(z['truth'][j,:,4]>344)
                all_detection.append(dict(seed=int(seed),split=split,truth=z['truth'][j],xhat=z['xhat'][j],features=z['features'][j],y=z['y'][j],scores={str(name):z['scores'][j,k] for k,name in enumerate(z['detector_names'])},event=int(ev[0]) if len(ev) else None))
    data['allDetection']=all_detection
    # Keep 7 significant digits in presentation data; full-precision scientific records remain in results.
    def compact(v):
        if isinstance(v,float):return float(f'{v:.7g}')
        if isinstance(v,list):return [compact(x) for x in v]
        if isinstance(v,dict):return {k:compact(x) for k,x in v.items()}
        return v
    presentation=compact(clean(data));presentation['audit']=clean(data['audit'])
    payload=json.dumps(presentation,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template=(root/'web/template.html').read_text(encoding='utf-8');html=template.replace('__DATA__',payload)
    target=root/'PREMONITION_LAB.html';target.write_text(html,encoding='utf-8');save(results/'dashboard_build.json',{'control_traces':len(control),'detection_traces':len(all_detection),'bytes':target.stat().st_size,'partial':partial})
    return target
