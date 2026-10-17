"""Local scientific dashboard. Works offline after installation; loopback only."""
import argparse,json,threading,webbrowser,time,gzip
from pathlib import Path
import numpy as np
from flask import Flask,request,jsonify,send_from_directory,Response
from .physics import Model
from .truth import generate,SCENARIOS
from .observers import observe
from .discovery import discover
from .blind import classify,apply_after_validation
from .experiments import clean,savejson
from .symbolic import equations

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts'/'main'
app=Flask(__name__);job_lock=threading.Lock()

def bundle():
    data={'scenarios':list(SCENARIOS),'summary':{},'discoveries':{},'traces':{},'control':[], 'protocol':{}}
    p=ART/'estimation_summary.json'
    if p.exists():data['summary']=json.loads(p.read_text(encoding='utf-8'))
    for p in (ART/'discoveries').glob('*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        for r in d['ranking']:
            if r.get('equation_export_version')!=2:r['equations']=equations(Model.from_dict(r['model']))
        data['discoveries'][p.stem]=d
    for p in (ART/'traces').glob('*.json'):data['traces'][p.stem]=json.loads(p.read_text(encoding='utf-8'))
    for p in (ART/'traces').glob('*.json.gz'):
        key=p.name[:-8]
        if key not in data['traces']:data['traces'][key]=json.loads(gzip.decompress(p.read_bytes()))
    for name in ['protocol','identifiability','adversarial','scientific_summary']:
        p=ART/f'{name}.json'
        if p.exists():data[name]=json.loads(p.read_text(encoding='utf-8'))
    for p in (ART/'control_traces').glob('700000_*.json'):data['control'].append(json.loads(p.read_text(encoding='utf-8')))
    data['available']=bool(data['summary']);return clean(data)

@app.get('/')
def index():return send_from_directory(ROOT/'dashboard','index.html')

@app.get('/app.js')
def js():return send_from_directory(ROOT/'dashboard','app.js')

@app.get('/style.css')
def css():return send_from_directory(ROOT/'dashboard','style.css')

@app.get('/api/data')
def data():return jsonify(bundle())

@app.get('/api/health')
def health():return jsonify(ok=True,version='1.0.0',synthetic=True)

@app.get('/api/export/<name>')
def export(name):
    allowed={'estimation.csv','control.csv','blind.csv','ablations.csv','scientific_summary.json'}
    if name not in allowed:return jsonify(error='Exportação desconhecida'),404
    if not (ART/name).exists():
        compressed=ART/(name+'.gz')
        if compressed.exists():return Response(gzip.decompress(compressed.read_bytes()),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="{name}"'})
        return jsonify(error='Campanha ainda não executada'),404
    return send_from_directory(ART,name,as_attachment=True)

@app.post('/api/run')
def run():
    body=request.get_json(silent=True) or {};scenario=body.get('scenario','A_rich')
    if scenario not in SCENARIOS:return jsonify(error='Cenário inválido'),400
    try:
        seed=int(body.get('seed',20261017))
        if not 0<=seed<2**31:return jsonify(error='Seed fora do intervalo'),400
    except (ValueError,TypeError):return jsonify(error='Seed inválida'),400
    if not job_lock.acquire(blocking=False):return jsonify(error='Um experimento já está em execução'),409
    try:
        ep=generate(seed,scenario);r0=observe(ep.operational);ra=observe(ep.operational,kind='adaptive')
        diagnostic=None
        if body.get('blind'):
            threshold=json.loads((ART/'calibration.json').read_text(encoding='utf-8'))['threshold']
            diagnostic=classify(ep.operational,threshold);rd=apply_after_validation(ep.operational,diagnostic)
        else:
            source='A_rich' if scenario.startswith(('D_','X_')) else scenario
            p=ART/'models'/f'{source}.json';d=json.loads(p.read_text(encoding='utf-8'))['discovery'] if p.exists() else None
            rd=observe(ep.operational,Model.from_dict(d['model']) if d else Model())
        results={'UKF':r0,'Adaptive':ra,'Darwin':rd}
        trace=dict(scenario=scenario,seed=seed,dt=ep.operational.dt,u=ep.operational.inputs,y=ep.operational.measurements,truth=ep.truth,
            methods={m:dict(x=r['x'],std=np.sqrt(np.maximum(np.diagonal(r['cov'],axis1=1,axis2=2),0)),innovation=r['innovation'],nis=r['nis']) for m,r in results.items()},
            discovery_source='A_rich' if scenario.startswith(('D_','X_')) else scenario,diagnostic=diagnostic)
        return jsonify(clean(trace))
    finally:job_lock.release()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);ap.add_argument('--open',action='store_true');args=ap.parse_args()
    if args.open:threading.Timer(1.2,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    app.run(host='127.0.0.1',port=args.port,debug=False,threaded=True)

if __name__=='__main__':main()
