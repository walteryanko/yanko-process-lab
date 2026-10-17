"""Paired, causal experiments. Truth generation is separate from filter API."""
import argparse,csv,json,time,platform,sys,traceback,hashlib
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
from scipy.stats import norm
from .model import *
from .probability import moments,weighted_quantile,crps_ensemble,energy_score
from .filters import FilterConfig,make_filter,METHODS,parameter_std,sample_prior

SCENARIOS=['gaussian','ambiguous','student','outliers','correlated','missing','bias','physics']

def initial(scenario,joint=False):
    mean=BASE.copy()
    std=np.array([.06,.3,.14,.12,.45,.45]);cov=np.diag(std**2)
    if scenario=='ambiguous':
        cov+=.45**2*np.outer(NULL_CC,NULL_CC)+.25**2*np.outer(NULL_CM,NULL_CM)
    if joint:
        mean=np.r_[mean,np.zeros(4)]
        cc=np.zeros((10,10));cc[:6,:6]=cov;cc[6:,6:]=np.diag(parameter_std()**2);cov=cc
    return mean,cov

def measurement_spec(scenario,informed=True):
    R=np.eye(2)*.35**2;kind='gaussian'
    if scenario=='correlated' and informed:R[0,1]=R[1,0]=.75*.35**2
    if informed and scenario=='student':kind='student'
    if informed and scenario=='outliers':kind='mixture'
    return R,kind

def generate(seed,scenario,steps=48):
    if scenario not in SCENARIOS:raise ValueError('Unknown scenario')
    # Streams separated from every estimator and from any diagnostics.
    rng=np.random.default_rng(np.random.SeedSequence([seed,113]))
    m,p=initial(scenario);x0,reject=sample_prior(m,p,1,rng,FilterConfig())
    true=np.empty((steps+1,6));true[0]=x0[0]
    controls=np.broadcast_to(U0,(steps,6)).copy()
    t=np.arange(steps)
    controls[:,3]+=50*np.sin(t/8)
    controls[steps//3:2*steps//3,0]*=1.02
    controls[steps//2:,4]+=.5
    theta=rng.normal(size=4)*parameter_std() if scenario=='physics' else np.zeros(4)
    process=rng.normal(size=(steps,6))*np.sqrt(Q_PUBLISHED)
    process_reject=0
    for k in range(steps):
        det=step(true[k],controls[k],theta=theta)
        candidate=det+process[k]
        while not valid(candidate):
            process_reject+=1;process[k]=rng.normal(size=6)*np.sqrt(Q_PUBLISHED);candidate=det+process[k]
        true[k+1]=candidate
    R,kind=measurement_spec(scenario);err=rng.multivariate_normal(np.zeros(2),R,size=steps)
    if scenario=='student':err/=np.sqrt(rng.chisquare(3,size=(steps,1))/3)
    if scenario=='outliers':err*=np.where(rng.random((steps,1))<.06,10.,1.)
    bias=rng.normal(0,1.0,size=2) if scenario=='bias' else np.zeros(2)
    y=true[1:,4:6]+err+bias
    if scenario=='missing':y[rng.random(y.shape)<.3]=np.nan
    return dict(seed=seed,scenario=scenario,true=true,u=controls,y=y,theta=theta,
                process=process,bias=bias,truth_rejections=reject+process_reject)

def run(ep,method,cfg=FilterConfig(),record_particles=False):
    mean,cov=initial(ep['scenario'],cfg.joint);R,_=measurement_spec(ep['scenario'],True)
    if cfg.likelihood=='naive':R=np.eye(2)*.35**2;cfg=replace(cfg,likelihood='gaussian')
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
            pc=pts[:,:6];means,pcov=moments(pc,w);postmeans.append(means)
            if method in ('M0','M0_original'):
                low=m[:6]-norm.ppf(.95)*np.sqrt(np.diag(p)[:6]);high=m[:6]+norm.ppf(.95)*np.sqrt(np.diag(p)[:6])
                for level in coverages:
                    d=norm.ppf((1+level)/2)*np.sqrt(np.diag(p)[:6]);coverages[level].append((truth[k]>=m[:6]-d)&(truth[k]<=m[:6]+d))
            else:
                low=np.array([weighted_quantile(pc[:,j],w,[.05])[0] for j in range(6)])
                high=np.array([weighted_quantile(pc[:,j],w,[.95])[0] for j in range(6)])
                for level in coverages:
                    qu=np.array([weighted_quantile(pc[:,j],w,[(1-level)/2,(1+level)/2]) for j in range(6)])
                    coverages[level].append((truth[k]>=qu[:,0])&(truth[k]<=qu[:,1]))
            lows.append(low);highs.append(high);errors.append(m[:6]-truth[k]);diagnostics.append(f.last.copy())
            crps.append([crps_ensemble(pc[:,j],w,truth[k,j]) for j in range(6)])
            # Standardized full energy score, every 4th sample to bound diagnostic cost.
            if k%4==0:energy.append(energy_score(pc,w,truth[k],SCALES))
            if record_particles:
                plan=getattr(f,'plan',None);matrix_n=len(plan) if plan is not None else 0
                if plan is not None and len(plan)>128:
                    edges=np.linspace(0,len(plan),129,dtype=int)[:-1]
                    plan=np.add.reduceat(np.add.reduceat(plan,edges,axis=0),edges,axis=1)
                snapshots.append(dict(particles=pc.tolist(),weights=w.tolist(),
                                      parameters=pts[:,6:].tolist() if cfg.joint else [],
                                      transport=plan.tolist() if plan is not None else None,
                                      transport_original_n=matrix_n,transport_aggregated=matrix_n>128,
                                      transport_source=f.transport_source[:,:6].tolist() if hasattr(f,'plan') and f.plan is not None else None))
            for h in forecast:
                if k+h<len(truth) and k%4==0:
                    # Constant-input open-loop prediction; no future control access.
                    xx=m[:6].copy()
                    for _ in range(h):xx=step(xx,u,max_step=cfg.max_step,theta=m[6:] if cfg.joint else None)
                    forecast[h].append((xx-truth[k+h])**2)
        except Exception as exc:
            failure=dict(step=k,type=type(exc).__name__,message=str(exc));break
    result=dict(seed=int(ep['seed']),scenario=ep['scenario'],method=method,particles=cfg.particles,joint=cfg.joint,
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
        if cfg.joint:result['parameter_rmse']=np.sqrt(np.mean((np.array(estimates)[:,6:]-ep['theta'])**2,axis=0)).tolist()
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
                    summary['paired_vs_M0']={'n':len(diff),'delta_rmse_cc':float(diff.mean()),'ci95':np.quantile(boot,[.025,.975]),
                                            'wins':int(sum(diff<0)),'losses':int(sum(diff>0)),
                                            'percent':100*float(diff.mean())/np.mean([b['rmse'][2] for r,b in pairs])}
            out[scenario][method]=summary
    return serial(out)

def save_csv(path,rows):
    fields=['scenario','seed','method','joint','particles','steps_completed','failure','rmse_CC','mae_CC','crps_CC','coverage90_CC',
            'calibration_error','width90','energy','latency_mean_ms','latency_p95_ms','latency_p99_ms','fallback_count','rejected_count','bridge_updates']
    with open(path,'w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for r in rows:
            z={k:r.get(k) for k in fields};z.update(rmse_CC=r.get('rmse',[None]*6)[2],mae_CC=r.get('mae',[None]*6)[2],
             crps_CC=r.get('crps',[None]*6)[2],coverage90_CC=r.get('coverage',{}).get('0.9',[None]*6)[2],failure=json.dumps(r['failure']))
            w.writerow(z)

def campaign(args):
    if not 2<=args.particles<=1024 or not 1<=args.steps<=512 or args.trials<1:
        raise ValueError('Use 2..1024 particles, 1..512 steps and at least one trial.')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True);(out/'datasets').mkdir(exist_ok=True);(out/'traces').mkdir(exist_ok=True)
    if (out/'runs.jsonl').exists():
        raise FileExistsError('Choose a fresh --out directory; existing evidence is not overwritten.')
    cfg=FilterConfig(particles=args.particles,epsilon=args.epsilon,bridge_steps=args.bridge_steps,joint=args.joint,threshold=args.threshold)
    rows=[];start=time.perf_counter()
    for scenario in args.scenarios:
        for seed in range(args.start_seed,args.start_seed+args.trials):
            ep=generate(seed,scenario,args.steps);np.savez_compressed(out/'datasets'/f'{scenario}_{seed}.npz',**{k:v for k,v in ep.items() if isinstance(v,np.ndarray)})
            _,kind=measurement_spec(scenario)
            run_cfg=replace(cfg,likelihood='naive' if args.naive else kind)
            for method in args.methods:
                res,tr=run(ep,method,run_cfg,record_particles=(seed==args.start_seed));rows.append(res)
                np.savez_compressed(out/'traces'/f'{scenario}_{seed}_{method}.npz',estimates=tr['estimates'],lower90=tr['lower90'],upper90=tr['upper90'],covariance=tr['covariance'])
                if seed==args.start_seed:write_json(out/f'demo_{scenario}_{method}.json',dict(episode=ep,result=res,trace=tr))
                with (out/'runs.jsonl').open('a',encoding='utf-8') as fh:fh.write(json.dumps(serial(res))+'\n')
            if (seed-args.start_seed)%5==0:print(f'{scenario}: {seed-args.start_seed+1}/{args.trials}, {time.perf_counter()-start:.1f}s',flush=True)
    write_json(out/'summary.json',paired_summary(rows));save_csv(out/'episodes.csv',rows)
    write_json(out/'manifest.json',dict(config=vars(args),model=metadata(),seconds=time.perf_counter()-start,
              python=sys.version,platform=platform.platform(),numpy=np.__version__,experiment='Synthetic CSTR; no plant data',
              split='test' if args.start_seed>=2000 else 'development',failed=[r for r in rows if r['failure']],
              dataset_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'datasets').glob('*.npz')}))

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='results/main');p.add_argument('--trials',type=int,default=100)
    p.add_argument('--start-seed',type=int,default=2000);p.add_argument('--steps',type=int,default=48)
    p.add_argument('--particles',type=int,default=128);p.add_argument('--epsilon',type=float,default=.001)
    p.add_argument('--bridge-steps',type=int,default=64);p.add_argument('--threshold',type=float,default=float('inf'))
    p.add_argument('--scenarios',nargs='+',default=['gaussian','ambiguous']);p.add_argument('--methods',nargs='+',default=list(METHODS))
    p.add_argument('--joint',action='store_true');p.add_argument('--naive',action='store_true');campaign(p.parse_args())

if __name__=='__main__':main()
