"""Reproducible campaign runner. All failed configurations remain recorded."""
import argparse,csv,hashlib,json,os,time,traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from .physics import Model,BASE,U0,NP,correction
from .truth import generate,SCENARIOS
from .observers import observe
from .detection import calibrate_threshold
from .discovery import discover,paired_interval
from .residual import fit_baselines,observe_residual
from .metrics import estimate_metrics,summary
from .identification import local_observability

ROOT=Path(__file__).resolve().parents[1]
TRAIN_SCENARIOS=list(SCENARIOS)[:12]
TEST_SCENARIOS=list(SCENARIOS)

def clean(obj):
    if isinstance(obj,np.ndarray):return clean(obj.tolist())
    if isinstance(obj,(np.floating,float)):return float(obj) if np.isfinite(obj) else None
    if isinstance(obj,(np.integer,)):return int(obj)
    if isinstance(obj,(np.bool_,)):return bool(obj)
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [clean(v) for v in obj]
    return obj

def savejson(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(clean(obj),indent=2,ensure_ascii=False),encoding='utf-8');tmp.replace(path)

def savecsv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r));Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)

def save_episode(path,ep,results=None):
    data=dict(u=ep.operational.inputs,y=ep.operational.measurements,truth=ep.truth,seed=ep.operational.seed,
        metadata=json.dumps(ep.metadata),dt=ep.operational.dt)
    if results:
        for name,r in results.items():
            for key in ('x','cov','innovation','S','nis'):data[name+'_'+key]=r[key]
    Path(path).parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,**data)

def fit_scenario(args):
    scenario,index,out,threshold,ntrain,nval=args;out=Path(out)
    train=[generate(10000+index*1000+i,scenario) for i in range(ntrain)]
    validation=[generate(50000+index*1000+i,scenario) for i in range(nval)]
    for name,eps in [('train',train),('validation',validation)]:
        for ep in eps:save_episode(out/'datasets'/name/scenario/f'{ep.operational.seed}.npz',ep)
    tr=[e.operational for e in train];va=[e.operational for e in validation]
    d=discover(tr,va,threshold);savejson(out/'discoveries'/f'{scenario}.json',d)
    # Parametric contender is selected with the same independent validation protocol.
    param_names=['H0','UA_constant','kinetic_rate','kinetic_activation','reaction_heat','sensor_bias','sensor_drift','thermal_capacity','feed_composition','feed_temperature']
    eligible=[r for r in d['ranking'] if r['name'] in param_names and r['eligible']]
    null=next(r for r in d['ranking'] if r['name']=='H0');best=min(eligible,key=lambda r:r['score']) if eligible else null
    gain=1-best['validation_mse']/max(null['validation_mse'],1e-12)
    ci=paired_interval(np.array(null['validation_episodes'])-best['validation_episodes'])
    param=best['model'] if gain>.1 and ci[0]>0 and any(x['state']=='DETECT' and x['details']['persistent'] for x in d['events']) else null['model']
    artifact=fit_baselines(tr);bundle=dict(discovery=d,parametric=param,residual=artifact)
    savejson(out/'models'/f'{scenario}.json',bundle)
    return scenario,d['selected'],d['execution_seconds']

def eval_scenario(args):
    scenario,index,out,n=args;out=Path(out);source='A_rich' if scenario.startswith(('D_','X_')) else scenario
    bundle=json.loads((out/'models'/f'{source}.json').read_text(encoding='utf-8'));d=bundle['discovery'];dm=Model.from_dict(d['model']);pm=Model.from_dict(bundle['parametric'])
    threshold=json.loads((out/'calibration.json').read_text(encoding='utf-8'))['threshold'];rows=[];failures=[];traces=[]
    for i in range(n):
        seed=100000+index*1000+i;ep=generate(seed,scenario);results={}
        methods=[('UKF',lambda:observe(ep.operational)),('EKF',lambda:observe(ep.operational,kind='ekf')),
            ('Adaptive',lambda:observe(ep.operational,kind='adaptive')),('DarwinParametric',lambda:observe(ep.operational,pm)),
            ('Darwin',lambda:observe(ep.operational,dm)),('ResidualRBF',lambda:observe_residual(ep.operational,bundle['residual'],'rbf')),
            ('Neural',lambda:observe_residual(ep.operational,bundle['residual'],'mlp'))]
        for method,fn in methods:
            try:
                r=fn();results[method]=r;m=dm if method=='Darwin' else pm if method=='DarwinParametric' else Model()
                met=estimate_metrics(ep,r,m,threshold)
                # Multistep report uses implemented static physical model only.
                if method in ('ResidualRBF','Neural','Adaptive'):met['forecast10_K']=None
                rows.append(dict(scenario=scenario,seed=seed,method=method,**met))
            except Exception as e:failures.append(dict(scenario=scenario,seed=seed,method=method,error=str(e),trace=traceback.format_exc()))
        save_episode(out/'datasets'/'test'/scenario/f'{seed}.npz',ep,results)
        if i<2:
            trace=dict(scenario=scenario,seed=seed,dt=ep.operational.dt,u=ep.operational.inputs,y=ep.operational.measurements,truth=ep.truth,
                methods={m:dict(x=r['x'],std=np.sqrt(np.maximum(np.diagonal(r['cov'],axis1=1,axis2=2),0)),innovation=r['innovation'],nis=r['nis']) for m,r in results.items()},discovery_source=source)
            traces.append(trace)
    savecsv(out/'per_scenario'/f'{scenario}.csv',rows);savejson(out/'traces'/f'{scenario}.json',traces);savejson(out/'failures'/f'{scenario}.json',failures)
    return scenario,rows,failures

def control_task(args):
    seed,out,steps=args
    from .control import rollout
    d=json.loads((Path(out)/'discoveries'/'A_rich.json').read_text(encoding='utf-8'));runs=[]
    for mode in ['nominal','adaptive_nominal','darwin_nominal','darwin_corrected']:
        runs.append(rollout(seed,mode,d,steps))
    return runs

def blind_task(args):
    scenario,seed,threshold=args
    from .blind import classify,apply_after_validation
    e=generate(seed,scenario);d=classify(e.operational,threshold);r=apply_after_validation(e.operational,d);n=observe(e.operational)
    expected='sensor' if scenario in ('C_bias','C_drift','C_noise','C_dropout') else 'physics' if scenario=='C_UA' else 'nominal'
    pred='sensor' if d['label'].startswith('sensor') else d['label']
    row=dict(scenario=scenario,seed=seed,expected=expected,predicted=pred,label=d['label'],accepted=d['accepted'],
        detected=d['diagnostic']['detected'],false_equation=expected!='physics' and d['accepted'] and pred=='physics',
        rmse_CC=float(np.sqrt(np.mean((r['x'][91:,2]-e.truth[91:,2])**2))),
        UKF_rmse_CC=float(np.sqrt(np.mean((n['x'][91:,2]-e.truth[91:,2])**2))))
    return row,d

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default=str(ROOT/'artifacts'/'main'));ap.add_argument('--n',type=int,default=100)
    ap.add_argument('--workers',type=int,default=4);ap.add_argument('--stage',choices=['fit','test','control','blind','summarize','all'],default='all');args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((ROOT/'configs'/'protocol.json').read_text(encoding='utf-8'));savejson(out/'protocol.json',protocol);start=time.perf_counter()
    if args.stage in ('all','fit'):
        calibration=[observe(generate(900000+i).operational) for i in range(50)];threshold,v=calibrate_threshold(calibration)
        savejson(out/'calibration.json',dict(threshold=threshold,statistics=v,seeds=list(range(900000,900050))))
        # Warm common compiled kernels before workers are started.
        observe(generate(999999).operational,kind='adaptive')
        with ProcessPoolExecutor(args.workers) as pool:
            futs=[pool.submit(fit_scenario,(s,i,str(out),threshold,12,8)) for i,s in enumerate(TRAIN_SCENARIOS)]
            for f in as_completed(futs):print('FIT',f.result(),flush=True)
    if args.stage in ('all','test'):
        rows=[];fail=[]
        with ProcessPoolExecutor(args.workers) as pool:
            futs=[pool.submit(eval_scenario,(s,i,str(out),args.n)) for i,s in enumerate(TEST_SCENARIOS)]
            for f in as_completed(futs):
                s,r,e=f.result();rows+=r;fail+=e;print('TEST',s,len(r),'failures',len(e),flush=True)
        rows.sort(key=lambda r:(r['scenario'],r['seed'],r['method']));savecsv(out/'estimation.csv',rows);savejson(out/'estimation_summary.json',summary(rows));savejson(out/'failures.json',fail)
    if args.stage in ('all','control'):
        from .control import rollout
        d=json.loads((out/'discoveries'/'A_rich.json').read_text(encoding='utf-8'));rollout(699999,'nominal',d,steps=2)
        rows=[]
        with ProcessPoolExecutor(args.workers) as pool:
            futs=[pool.submit(control_task,(700000+i,str(out),60)) for i in range(args.n)]
            for k,f in enumerate(as_completed(futs)):
                runs=f.result()
                for r in runs:
                    savejson(out/'control_traces'/f"{r['seed']}_{r['method']}.json",r)
                    rows.append({a:b for a,b in r.items() if a not in ('rows','events')})
                if (k+1)%10==0:print('CONTROL',k+1,flush=True)
        rows.sort(key=lambda r:(r['seed'],r['method']));savecsv(out/'control.csv',rows)
    if args.stage in ('all','blind'):
        threshold=json.loads((out/'calibration.json').read_text(encoding='utf-8'))['threshold'];rows=[]
        tasks=[(s,800000+j*1000+i,threshold) for j,s in enumerate(['H0','C_bias','C_drift','C_noise','C_dropout','C_UA']) for i in range(args.n)]
        with ProcessPoolExecutor(args.workers) as pool:
            futs=[pool.submit(blind_task,a) for a in tasks]
            for k,f in enumerate(as_completed(futs)):
                r,d=f.result();rows.append(r);savejson(out/'blind_decisions'/f"{r['seed']}.json",d)
                if (k+1)%100==0:print('BLIND',k+1,flush=True)
        rows.sort(key=lambda r:(r['scenario'],r['seed']));savecsv(out/'blind.csv',rows)
    savejson(out/f'execution_{args.stage}.json',dict(stage=args.stage,seconds=time.perf_counter()-start,n=args.n,workers=args.workers,observability=local_observability(BASE,U0)))

if __name__=='__main__':main()
