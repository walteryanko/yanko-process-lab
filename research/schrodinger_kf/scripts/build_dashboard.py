import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from schrodinger_lab.experiments import serial
from schrodinger_lab.model import metadata
def display_precision(obj):
    # Display-only export; all full-precision scientific evidence stays in results/.
    if isinstance(obj,float):return float(format(obj,'.10g'))
    if isinstance(obj,list):return [display_precision(x) for x in obj]
    if isinstance(obj,dict):return {k:display_precision(v) for k,v in obj.items()}
    return obj
data={'model':metadata(),'demos':{},'benchmarks':{},'development':{},'studies':{},'control':None}
for group in ['main','hostile','hostile_naive','physics_fixed','physics_joint']:
    folder=root/'results'/group
    if (folder/'summary.json').exists():data['benchmarks'][group]=json.loads((folder/'summary.json').read_text())
    if group.endswith('naive') or group=='physics_joint':continue
    for p in folder.glob('demo_*.json'):
        d=json.loads(p.read_text());sc=d['episode']['scenario'];method=d['result']['method']
        # Thin only the displayed transport snapshots. Full raw matrices remain in results/.
        for k,s in enumerate(d['trace']['snapshots']):
            if k%6 and k!=len(d['trace']['snapshots'])-1:s['transport']=None;s['transport_source']=None
        data['demos'].setdefault(sc,{})[method]=d
for file in ['synthetic_metrics','synthetic_distributions','observability','scaling']:
    p=root/'results/studies'/f'{file}.json'
    if p.exists():data['studies'][file]=json.loads(p.read_text())
p=root/'results/development/selection.json'
if p.exists():data['development']=json.loads(p.read_text())
p=root/'results/control/control.json'
if p.exists():data['control']=json.loads(p.read_text())
(root/'web/data.js').write_text('window.LAB_DATA='+json.dumps(display_precision(serial(data)),ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
print('Dashboard data built:',len(data['demos']),'scenarios')
