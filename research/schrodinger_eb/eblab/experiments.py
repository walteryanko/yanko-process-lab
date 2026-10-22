"""Paired, causal experiments. Truth generation is separate from filter API."""
import argparse,csv,json,time,platform,sys,traceback,hashlib
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
from scipy.stats import norm
from .model import *
from .probability import moments,weighted_quantile,crps_ensemble,energy_score
from .filters import FilterConfig,make_filter,METHODS,parameter_std,sample_prior

SCENARIOS=['gaussian','weak_thermal','student','outliers','correlated','missing','bias','physics','feed_step']

def initial(scenario,joint=False,noise_state=None):
    mean=BASE.copy();std=np.array([.012,.35,.18,.06,1.5])
    if scenario=='weak_thermal':std=np.array([.012,.8,.4,.15,1.5])
    if joint:mean=np.r_[mean,np.zeros(5)];std=np.r_[std,parameter_std()]
    if noise_state:mean=np.r_[mean,0.];std=np.r_[std,1.5]
    return mean,np.diag(std**2)

def measurement_spec(scenario,informed=True):
    R=np.array([[.09 if informed and scenario in ('bias','correlated') else 2.25]])
    kind='student' if informed and scenario=='student' else 'mixture' if informed and scenario=='outliers' else 'gaussian'
    return R,kind

def generate(seed,scenario,steps=60):
    if scenario not in SCENARIOS:raise ValueError('Unknown scenario')
    rng=np.random.default_rng(np.random.SeedSequence([seed,113]))
    m,p=initial(scenario);x0,reject=sample_prior(m,p,1,rng,FilterConfig())
    true=np.empty((steps+1,5));true[0]=x0[0]
    controls=np.broadcast_to(U0,(steps,7)).copy();k=np.arange(steps)
    controls[:,0]*=1+.015*np.sin(k/9);controls[:,3]*=1+.004*np.sin(k/13)
    if scenario=='feed_step':
        controls[steps//3:,1]*=1.5;controls[2*steps//3:,2]*=.5
    theta=rng.normal(size=5)*parameter_std() if scenario=='physics' else np.zeros(5)
    process=np.empty((steps,5));process_reject=0
    for k in range(steps):
        det=step(true[k],controls[k],theta=theta,method='dop853')
        for _ in range(10000):
            process[k]=rng.normal(size=5)*np.sqrt(Q_PUBLISHED);candidate=det+process[k]
            if valid(candidate):break
            process_reject+=1
        else:raise ValueError('Truth rejection failed')
        true[k+1]=candidate
    R,kind=measurement_spec(scenario);err=rng.normal(size=(steps,1))*np.sqrt(R[0,0])
    if scenario=='student':err/=np.sqrt(rng.chisquare(3,size=(steps,1))/3)
    if scenario=='outliers':err*=np.where(rng.random((steps,1))<.06,10.,1.)
    latent=np.zeros((steps,1))
    if scenario=='bias':latent[:]=rng.normal(0,1.5)
    if scenario=='correlated':
        b=rng.normal(0,1.5)
        for k in range(steps):b=.75*b+rng.normal(0,1.5*np.sqrt(1-.75**2));latent[k]=b
    y=true[1:,4:5]+err+latent
    if scenario=='missing':y[rng.random(y.shape)<.3]=np.nan
    return dict(seed=seed,scenario=scenario,true=true,u=controls,y=y,theta=theta,
                process=process,latent_sensor=latent,truth_rejections=reject+process_reject)

def run(ep,method,cfg=FilterConfig(),record_particles=False):
    mean,cov=initial(ep['scenario'],cfg.joint,cfg.noise_state);R,_=measurement_spec(ep['scenario'],True)
    if cfg.likelihood=='naive':R=np.array([[2.25]]);cfg=replace(cfg,likelihood='gaussian')
    # Shared initial MC stream between ensemble methods. Divergent algorithms may
    # consume different RNG counts later; the plant/noise pairing is exact.
    f=make_filter(method,mean,cov,R,cfg,int(ep['seed'])+987654)
    estimates=[];lows=[];highs=[];lat=[];diagnostics=[];snapshots=[];errors=[];crps=[];energy=[]
    truth=ep['true'][1:];postmeans=[];postcov=[];forecast={1:[],3:[],6:[]};coverages={.5:[],.8:[],.9:[],.95:[]}
    failure=None;pred_rejections=0
    for k,(u,y) in enumerate(zip(ep['u'],ep['y'])):
        try:
            m,p=f.advance(u,y);estimates.append(m.copy());postcov.append(p.copy());lat.append(f.last['latency_ms'])
            pts,w,rej=f.posterior(seed=int(ep['seed'])*1000+k+720001);pred_rejections+=rej
            pc=pts[:,:5];means,pcov=moments(pc,w);postmeans.append(means)
            if method in ('M0','M0_original'):
                low=m[:5]-norm.ppf(.95)*np.sqrt(np.diag(p)[:5]);high=m[:5]+norm.ppf(.95)*np.sqrt(np.diag(p)[:5])
                for level in coverages:
                    d=norm.ppf((1+level)/2)*np.sqrt(np.diag(p)[:5]);coverages[level].append((truth[k]>=m[:5]-d)&(truth[k]<=m[:5]+d))
            else:
                low=np.array([weighted_quantile(pc[:,j],w,[.05])[0] for j in range(5)])
                high=np.array([weighted_quantile(pc[:,j],w,[.95])[0] for j in range(5)])
                for level in coverages:
                    qu=np.array([weighted_quantile(pc[:,j],w,[(1-level)/2,(1+level)/2]) for j in range(5)])
                    coverages[level].append((truth[k]>=qu[:,0])&(truth[k]<=qu[:,1]))
            lows.append(low);highs.append(high);errors.append(m[:5]-truth[k]);diagnostics.append(f.last.copy())
            crps.append([crps_ensemble(pc[:,j],w,truth[k,j]) for j in range(5)])
            # Standardized full energy score, every 8th sample to bound diagnostic cost.
            if k%8==0:energy.append(energy_score(pc,w,truth[k],SCALES))
            if record_particles:
                plan=getattr(f,'plan',None);matrix_n=len(plan) if plan is not None else 0
                if plan is not None and len(plan)>32:
                    edges=np.linspace(0,len(plan),33,dtype=int)[:-1]
                    plan=np.add.reduceat(np.add.reduceat(plan,edges,axis=0),edges,axis=1)
                snapshots.append(dict(particles=pc.tolist(),weights=w.tolist(),
                                      parameters=pts[:,5:10].tolist() if cfg.joint else [],
                                      transport=plan.tolist() if plan is not None else None,
                                      transport_original_n=matrix_n,transport_aggregated=matrix_n>32,
                                      transport_source=f.transport_source[:,:5].tolist() if hasattr(f,'plan') and f.plan is not None else None))
            for h in forecast:
                if k+h<len(truth) and k%8==0:
                    # Constant-input open-loop prediction; no future control access.
                    xx=m[:5].copy()
                    for _ in range(h):xx=step(xx,u,max_step=cfg.max_step,theta=m[5:10] if cfg.joint else None)
                    forecast[h].append((xx-truth[k+h])**2)
        except Exception as exc:
            failure=dict(step=k,type=type(exc).__name__,message=str(exc));break
    result=dict(initial_rejected=getattr(f,'initial_rejected',0),seed=int(ep['seed']),scenario=ep['scenario'],method=method,particles=cfg.particles,joint=cfg.joint,
                config=asdict(cfg),steps_completed=len(errors),requested_steps=len(truth),failure=failure,
                truth_rejections=int(ep['truth_rejections']),diagnostic_sample_rejections=pred_rejections)
    if errors:
        e=np.array(errors);c=np.array(crps);lat=np.array(lat);covs={str(l):np.mean(v,axis=0).tolist() for l,v in coverages.items()}
        result.update(rmse=np.sqrt(np.mean(e*e,axis=0)).tolist(),mae=np.mean(np.abs(e),axis=0).tolist(),
                      rmse_early=np.sqrt(np.mean(e[:min(8,len(e))]**2,axis=0)).tolist(),
                      percent_mae=(100*np.mean(np.abs(e)/np.maximum(np.abs(truth[:len(e)]),1e-6),axis=0)).tolist(),
                      crps=np.mean(c,axis=0).tolist(),energy=float(np.mean(energy)),coverage=covs,
                      calibration_error=float(np.mean([abs(np.array(covs[str(l)])[2]-l) for l in coverages])),
                      width90=float(np.mean(np.array(highs)[:,2]-np.array(lows)[:,2])),
                      latency_mean_ms=float(lat.mean()),latency_p95_ms=float(np.quantile(lat,.95)),latency_p99_ms=float(np.quantile(lat,.99)),
                      ess_mean=float(np.mean([d['ess'] for d in diagnostics if d['ess'] is not None])) if method!='M0' and method!='M0_original' else None,
                      fallback_count=sum(d['fallback'] for d in diagnostics),rejected_count=sum(d['rejected'] for d in diagnostics),
                      bridge_updates=sum(d['branch']=='bridge' for d in diagnostics),
                      forecasts={str(h):np.sqrt(np.mean(v,axis=0)).tolist() if v else None for h,v in forecast.items()})
        if cfg.joint:result['parameter_rmse']=np.sqrt(np.mean((np.array(estimates)[:,5:10]-ep['theta'])**2,axis=0)).tolist()
    trace=dict(estimates=np.array(estimates),lower90=np.array(lows),upper90=np.array(highs),
               covariance=np.array(postcov),diagnostics=diagnostics,snapshots=snapshots)
    return result,trace

def serial(obj):
    if isinstance(obj,np.ndarray):return serial(obj.tolist())
    if isinstance(obj,(np.integer,np.floating)):return serial(obj.item())
    if isinstance(obj,float) and not np.isfinite(obj):return None
    if isinstance(obj,dict):return {str(k):serial(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [serial(v) for v in obj]
    return obj

def write_json(path,obj):Path(path).write_text(json.dumps(serial(obj),ensure_ascii=False,indent=2),encoding='utf-8')

def paired_summary(rows,reference='M0'):
    out={};rng=np.random.default_rng(61421)
    for scenario in sorted(set(r['scenario'] for r in rows)):
        group=[r for r in rows if r['scenario']==scenario];out[scenario]={}
        refs={r['seed']:r for r in group if r['method']==reference and r['failure'] is None}
        for method in sorted(set(r['method'] for r in group)):
            runs=[r for r in group if r['method']==method];good=[r for r in runs if r['failure'] is None]
            summary={'n':len(runs),'completed':len(good),'failed':len(runs)-len(good)}
            if good:
                for key in ['rmse','mae','rmse_early','crps']:summary[key]=np.mean([r[key] for r in good],axis=0)
                for key in ['energy','calibration_error','width90','latency_mean_ms','latency_p95_ms','latency_p99_ms','fallback_count','rejected_count','bridge_updates']:
                    summary[key]=float(np.mean([r[key] for r in good]))
                summary['coverage90']=np.mean([r['coverage']['0.9'] for r in good],axis=0)
                pairs=[(r,refs[r['seed']]) for r in good if r['seed'] in refs]
                if pairs:
                    diff=np.array([r['rmse'][2]-b['rmse'][2] for r,b in pairs])
                    boot=np.mean(rng.choice(diff,(2000,len(diff)),replace=True),axis=1)
                    summary['paired_vs_M0']={'n':len(diff),'delta_rmse_ceb':float(diff.mean()),'ci95':np.quantile(boot,[.025,.975]),
                                            'wins':int(sum(diff<0)),'losses':int(sum(diff>0)),
                                            'percent':100*float(diff.mean())/np.mean([b['rmse'][2] for r,b in pairs])}
            out[scenario][method]=summary
    return serial(out)

def save_csv(path,rows):
    fields=['scenario','seed','method','joint','particles','steps_completed','failure','rmse_CEB','mae_CEB','crps_CEB','coverage90_CEB',
            'calibration_error','width90','energy','latency_mean_ms','latency_p95_ms','latency_p99_ms','fallback_count','rejected_count','bridge_updates']
    with open(path,'w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for r in rows:
            z={k:r.get(k) for k in fields};z.update(rmse_CEB=r.get('rmse',[None]*5)[2],mae_CEB=r.get('mae',[None]*5)[2],
             crps_CEB=r.get('crps',[None]*5)[2],coverage90_CEB=r.get('coverage',{}).get('0.9',[None]*5)[2],failure=json.dumps(r['failure']))
            w.writerow(z)

def worker(job):
    scenario,seed,args=job;out=Path(args.out);ep=generate(seed,scenario,args.steps)
    np.savez_compressed(out/'datasets'/f'{scenario}_{seed}.npz',**{k:v for k,v in ep.items() if isinstance(v,np.ndarray)})
    if args.no_observations:ep['y']=np.full_like(ep['y'],np.nan)
    _,kind=measurement_spec(scenario)
    cfg=FilterConfig(particles=args.particles,epsilon=args.epsilon,bridge_steps=args.bridge_steps,
        bandwidth=args.bandwidth,joint=args.joint,threshold=args.threshold,qfactor=args.qfactor,
        likelihood='naive' if args.naive else kind,
        noise_state=scenario if scenario in ('bias','correlated') and not args.naive else None)
    rows=[]
    for method in args.methods:
        res,tr=run(ep,method,cfg,record_particles=seed==args.start_seed);rows.append(res)
        np.savez_compressed(out/'traces'/f'{scenario}_{seed}_{method}.npz',estimates=tr['estimates'],lower90=tr['lower90'],upper90=tr['upper90'],covariance=tr['covariance'])
        if seed==args.start_seed:write_json(out/f'demo_{scenario}_{method}.json',dict(episode=ep,result=res,trace=tr))
    return rows

def campaign(args):
    from concurrent.futures import ProcessPoolExecutor,as_completed
    if not 2<=args.particles<=1024 or not 1<=args.steps<=512 or args.trials<1:raise ValueError('Invalid budget')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for d in ['datasets','traces']:(out/d).mkdir(exist_ok=True)
    if (out/'runs.jsonl').exists():raise FileExistsError('Use a new output directory')
    jobs=[(sc,seed,args) for sc in args.scenarios for seed in range(args.start_seed,args.start_seed+args.trials)]
    rows=[];start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(worker,j) for j in jobs]
        for i,f in enumerate(as_completed(futures)):
            rr=f.result();rows.extend(rr)
            with (out/'runs.jsonl').open('a',encoding='utf-8') as fh:
                for r in rr:fh.write(json.dumps(serial(r),allow_nan=False)+'\n')
            if i%10==0:print(f'{out.name}: {i+1}/{len(jobs)} episodes, {time.perf_counter()-start:.1f}s',flush=True)
    rows.sort(key=lambda r:(r['scenario'],r['seed'],r['method']))
    # Final canonical journal is independent of worker completion ordering.
    tmp=out/'runs.tmp'
    import os
    with tmp.open('w',encoding='utf-8') as fh:
        for r in rows:fh.write(json.dumps(serial(r),allow_nan=False)+'\n')
        fh.flush();os.fsync(fh.fileno())
    tmp.replace(out/'runs.jsonl')
    assert len((out/'runs.jsonl').read_text(encoding='utf-8').splitlines())==len(rows)
    write_json(out/'summary.json',paired_summary(rows));save_csv(out/'episodes.csv',rows)
    write_json(out/'manifest.json',dict(config=vars(args),model=metadata(),seconds=time.perf_counter()-start,
        python=sys.version,platform=platform.platform(),numpy=np.__version__,experiment='Synthetic ethylbenzene reduced model; no plant data',
        split='test' if args.start_seed>=2000 else 'development',failed=[r for r in rows if r['failure']],
        dataset_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'datasets').glob('*.npz')}))
    print('Completed',len(rows),'runs; failures',sum(r['failure'] is not None for r in rows),flush=True)

def parser():
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/primary');p.add_argument('--trials',type=int,default=100)
    p.add_argument('--start-seed',type=int,default=2000);p.add_argument('--steps',type=int,default=60)
    p.add_argument('--particles',type=int,default=128);p.add_argument('--epsilon',type=float,default=.1)
    p.add_argument('--bridge-steps',type=int,default=64);p.add_argument('--bandwidth',type=float,default=.1)
    p.add_argument('--threshold',type=float,default=float('inf'));p.add_argument('--workers',type=int,default=4)
    p.add_argument('--qfactor',type=float,default=1.);p.add_argument('--no-observations',action='store_true')
    p.add_argument('--scenarios',nargs='+',default=['gaussian','weak_thermal']);p.add_argument('--methods',nargs='+',default=list(METHODS))
    p.add_argument('--joint',action='store_true');p.add_argument('--naive',action='store_true');return p

def main():campaign(parser().parse_args())
if __name__=='__main__':main()
