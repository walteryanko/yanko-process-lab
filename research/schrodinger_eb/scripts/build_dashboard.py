import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from eblab.experiments import serial

def build(root=ROOT,output=None):
    result=root/'results';data=dict(demos={},summaries={},rows={},studies={})
    for name in ['primary','robust','naive','physics_fixed','physics_joint','q64','no_observations']:
        p=result/name/'summary.json'
        if p.exists():data['summaries'][name]=json.loads(p.read_text())
        p=result/name/'runs.jsonl'
        if p.exists():
            fields=['seed','scenario','method','rmse','mae','crps','coverage','latency_mean_ms','fallback_count','failure']
            data['rows'][name]=[{k:r.get(k) for k in fields} for r in [json.loads(line) for line in p.read_text().splitlines()]]
    for sc in ['gaussian','weak_thermal']:
        data['demos'][sc]={}
        for m in ['M0','M1','M2','M3','M4','M5']:
            p=result/'primary'/f'demo_{sc}_{m}.json'
            if p.exists():data['demos'][sc][m]=json.loads(p.read_text())
    for name in ['observability','posterior_reference','synthetic_distributions','synthetic_metrics','scaling']:
        p=result/'studies'/(name+'.json')
        if p.exists():
            value=json.loads(p.read_text())
            if name=='posterior_reference':
                for r in value['snapshots']:r.pop('particles',None);r.pop('weights',None)
            data['studies'][name]=value
    for key,p in [('selection',result/'studies/selection.json'),('control',result/'control/control.json')]:
        if p.exists():
            data[key]=json.loads(p.read_text())
            if key=='control':data[key]['traces']=[r for r in data[key]['traces'] if r['seed']==4000]
    js='window.LAB_DATA='+json.dumps(serial(data),ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/')+';'
    (root/'web/data.js').write_text(js,encoding='utf-8')
    html=(root/'web/index.html').read_text();app=(root/'web/app.js').read_text()
    html=html.replace('<script src="data.js"></script>','<script>'+js+'</script>').replace('<script src="app.js"></script>','<script>'+app+'</script>')
    dest=Path(output) if output else root/'YCS_Ethylbenzene_Laboratory.html';dest.write_text(html,encoding='utf-8')
    print('Dashboard',dest,'bytes',dest.stat().st_size)
if __name__=='__main__':build(output=sys.argv[1] if len(sys.argv)>1 else None)
