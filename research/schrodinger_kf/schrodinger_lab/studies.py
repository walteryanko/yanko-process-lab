"""Development ablations, synthetic reference problems and observability."""
import argparse,time,tracemalloc,json
from pathlib import Path
from dataclasses import replace
import numpy as np
from scipy.stats import wasserstein_distance
from scipy.signal import find_peaks
from scipy.special import logsumexp
from .model import *
from .probability import *
from .transport import transform
from .bridge import generate as sb_generate
from .filters import FilterConfig,parameter_std
from .experiments import generate,run,measurement_spec,write_json,initial,serial

def development(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
    candidates=[('M0',FilterConfig()),('M1',FilterConfig()),('M2',FilterConfig())]
    candidates += [('M3',FilterConfig(epsilon=e)) for e in [.001,.005,.02]]
    candidates += [('M4',FilterConfig(bridge_steps=n)) for n in [32,64,128]]
    # Gate tested BEFORE enabling M5; inf is the always-Gaussian control.
    candidates += [('M5',FilterConfig(threshold=t)) for t in [1.5,3.,6.,float('inf')]]
    for sc in ['gaussian','ambiguous','outliers']:
        for seed in range(1000,1006):
            ep=generate(seed,sc,24);_,kind=measurement_spec(sc)
            for method,cfg in candidates:
                r,_=run(ep,method,replace(cfg,likelihood=kind));rows.append(r)
            print('development',sc,seed,flush=True)
    write_json(out/'all_candidates.json',rows)
    groups={}
    for r in rows:
        cfg=r['config'];key=(r['method'],cfg['epsilon'],cfg['bridge_steps'],cfg['threshold'])
        groups.setdefault(key,[]).append(r)
    summary=[]
    for key,rr in groups.items():
        good=[r for r in rr if not r['failure']]
        summary.append(dict(method=key[0],epsilon=key[1],steps=key[2],threshold=key[3],n=len(rr),
                            failures=len(rr)-len(good),crps_cc=float(np.mean([r['crps'][2] for r in good])),
                            rmse_cc=float(np.mean([r['rmse'][2] for r in good])),
                            latency_ms=float(np.mean([r['latency_mean_ms'] for r in good])),
                            bridge_updates=sum(r['bridge_updates'] for r in good)))
    chosen={m:min([s for s in summary if s['method']==m],key=lambda s:(s['failures'],s['crps_cc'])) for m in ['M3','M4','M5']}
    # A gate is justified only with a paired development CRPS CI below zero vs
    # the same adaptive implementation with the always-Gaussian gate disabled.
    gate=chosen['M5'];off={ (r['scenario'],r['seed']):r for r in rows if r['method']=='M5' and np.isinf(r['config']['threshold']) }
    rr=[r for r in rows if r['method']=='M5' and r['config']['threshold']==gate['threshold']]
    clusters={}
    for r in rr:clusters.setdefault(r['seed'],[]).append(r['crps'][2]-off[(r['scenario'],r['seed'])]['crps'][2])
    delta=np.array([np.mean(v) for v in clusters.values()]);rng=np.random.default_rng(45)
    ci=np.quantile(rng.choice(delta,(2000,len(delta))).mean(1),[.025,.975])
    enabled=bool(ci[1]<0 and not gate['failures'])
    selection=dict(epsilon=chosen['M3']['epsilon'],bridge_steps=chosen['M4']['steps'],bandwidth=.05,
                   adaptive_threshold=gate['threshold'] if enabled else None,adaptive_enabled=enabled,
                   adaptive_ci95_crps=ci.tolist(),rule='min development CRPS; adaptive enabled only if paired seed-cluster CI95 upper<0',
                   dev_seeds=list(range(1000,1006)),test_seeds=list(range(2000,2100)),summary=summary)
    write_json(out/'selection.json',selection);print(json.dumps(serial(selection)),flush=True)

def synthetic(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(731)
    grid=np.linspace(-6,6,24001);dx=grid[1]-grid[0];rows=[];data={}
    for case,h,y,sd in [('linear',lambda x:x,.7,.5),('sine',np.sin,.7,.2),('bimodal',lambda x:x*x,4.,.3)]:
        density=normalize(-.5*(grid/1.5)**2-.5*((h(grid)-y)/sd)**2)
        peaks,_=find_peaks(density,prominence=density.max()*.02)
        x=rng.normal(0,1.5,(512,1));w=normalize(-.5*((h(x[:,0])-y)/sd)**2)
        pf=x[systematic(w,rng)]
        # Separated modes can make Sinkhorn slow: preserve a failed solve as a
        # reported PF fallback instead of aborting or accepting wrong marginals.
        try:
            tp,plan,td=transform(x,w,np.array([1.5]),.05,max_iter=1500)
        except ArithmeticError:
            tp=pf.copy();td={'converged':False,'fallback':'systematic PF','epsilon':.05}
        sb,bd,_=sb_generate(x,w,rng,steps=128,bandwidth=.05)
        sets={'PF':pf[:,0],'M3':tp[:,0],'M4':sb[:,0]}
        data[case]=dict(grid=grid[::8],density=density[::8]/dx,particles=x[:,0],weights=w,sets=sets,reference_modes=grid[peaks],transport=td)
        for method,a in sets.items():rows.append(dict(case=case,method=method,mean=float(a.mean()),std=float(a.std()),
              reference_mean=float(grid@density),reference_sd=float(np.sqrt(density@(grid-grid@density)**2)),
              w1=float(wasserstein_distance(grid,a,u_weights=density)),negative_mass=float(np.mean(a<0)),
              reference_negative_mass=float(density[grid<0].sum()),reference_modes=grid[peaks].tolist(),
              fallback=(method=='M3' and not td['converged'])))
    # Partial observation x1+x2: analytic Gaussian posterior.
    x=rng.normal(size=(1024,2));hh=np.array([1.,1.]);y=1.;r=.25
    w=normalize(-.5*(x@hh-y)**2/r);pm,pc=moments(x,w)
    exact_m=hh/(2+r);exact_p=np.eye(2)-np.outer(hh,hh)/(2+r)
    partial=dict(empirical_mean=pm,analytic_mean=exact_m,empirical_cov=pc,analytic_cov=exact_p,
                 mean_error=float(np.linalg.norm(pm-exact_m)),unobserved_difference_variance=float(np.array([1.,-1.])@pc@np.array([1.,-1.])))
    # SDE discretization/KDE ablation: repeated generators of exactly the same target.
    x=rng.normal(size=(256,1));w=normalize(-.5*((x[:,0]-.8)/.5)**2);m,p=moments(x,w);ablation=[]
    for steps in [16,32,64,128,256]:
        for bandwidth in [0.,.05,.15]:
            vals=[]
            for seed in range(10):
                a,d,_=sb_generate(x,w,np.random.default_rng(500+seed),steps,bandwidth)
                vals.append([a.mean()-m[0],a.var()-p[0,0],wasserstein_distance(x[:,0],a[:,0],u_weights=w)])
            a=np.array(vals);ablation.append(dict(steps=steps,bandwidth=bandwidth,mean_bias=float(a[:,0].mean()),variance_bias=float(a[:,1].mean()),w1=float(a[:,2].mean())))
    write_json(out/'synthetic_metrics.json',dict(rows=rows,partial=partial,bridge_ablation=ablation))
    write_json(out/'synthetic_distributions.json',data)

def observability(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    steps=32
    def outputs(x,theta=None,excited=False):
        hist=[x[4:].copy()]
        for k in range(steps):
            u=U0.copy()
            if excited:u[3]+=70*np.sin(k/6)+30;u[0]*=1.02 if k>8 else 1.
            x=step(x,u,theta=theta);hist.append(x[4:].copy())
        return np.array(hist)
    base=outputs(BASE);jac=[]
    for j in range(6):
        d=np.eye(6)[j]*SCALES[j]*1e-4
        jac.append(((outputs(BASE+d)-outputs(BASE-d))/(2e-4)/.35).ravel())
    J=np.array(jac).T;_,s,v=np.linalg.svd(J,full_matrices=False)
    excited_jac=[]
    for j in range(6):
        d=np.eye(6)[j]*SCALES[j]*1e-4
        excited_jac.append(((outputs(BASE+d,excited=True)-outputs(BASE-d,excited=True))/(2e-4)/.35).ravel())
    se=np.linalg.svd(np.array(excited_jac).T,compute_uv=False)
    jp=[]
    for j in range(4):
        d=np.eye(4)[j]*parameter_std()[j]*1e-3
        jp.append(((outputs(BASE,d)-outputs(BASE,-d))/(2e-3)/.35).ravel())
    _,sp,vp=np.linalg.svd(np.column_stack([J,np.array(jp).T]),full_matrices=False)
    deltas=np.linspace(-1.1,1.1,161);profiles=[]
    rng=np.random.default_rng(83);observed=base+rng.normal(0,.35,base.shape)
    for d in deltas:
        xx=BASE+d*NULL_CC;y=outputs(xx);res=(observed-y)/.35
        profiles.append(dict(delta_cc=float(d),max_thermal_difference=float(np.max(np.abs(y-base))),
                             loglik=float(-.5*np.sum(res*res)),initial_state=xx.tolist()))
    lw=np.array([r['loglik'] for r in profiles]);prior=normalize(-.5*(deltas/.45)**2);post=normalize(np.log(prior)+lw)
    # Independent finite-dimensional grid reference: product prior over active CA
    # and invisible CC. Shows a ridge from a continuous prior, not planted modes.
    ac=np.linspace(-.14,.14,49);dc=np.linspace(-.9,.9,81)
    xx=BASE+ac[:,None,None]*np.eye(6)[0]+dc[None,:,None]*NULL_CC
    loss=np.zeros(xx.shape[:2]);obs=observed[1:9]
    for k in range(8):xx=step(xx,U0);loss+=np.sum(((xx[...,4:]-obs[k])/.35)**2,axis=-1)
    log_prior=-.5*(ac[:,None]/.06)**2-.5*(dc[None,:]/.45)**2
    density=normalize((log_prior-.5*loss).ravel()).reshape(loss.shape)
    marginal=density.sum(0);peaks,_=find_peaks(marginal,prominence=.05*marginal.max())
    write_json(out/'observability.json',dict(singular_values=s,rank_relative_1e_7=int(sum(s>s[0]*1e-7)),
             null_directions=[NULL_CC,NULL_CM],joint_singular_values=sp,profiles=profiles,
             excited_singular_values=se,excited_rank_relative_1e_7=int(sum(se>se[0]*1e-7)),
             prior_delta=prior,posterior_delta=post,delta_grid=deltas,
             posterior_prior_w1=float(wasserstein_distance(deltas,deltas,u_weights=prior,v_weights=post)),
             reference=dict(active_CA_grid=ac,hidden_CC_grid=dc,density=density,cc_marginal=marginal,
                            modes=dc[peaks],noise_seed=83,description='Continuous Gaussian prior; 8 measurements; deterministic transition'),
             interpretation='Two exact unobservable initial-composition directions. Ambiguity is continuous; no separated CSTR modes established.'))

def scaling(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
    for n in [64,128,256,512,1024]:
        ep=generate(901,'gaussian',6);cfg=FilterConfig(particles=n,bridge_steps=64,epsilon=.005)
        for method in ['M0','M1','M2','M3','M4']:
            # tracemalloc peak describes Python/NumPy tracked allocations, not process RSS.
            tracemalloc.start();t=time.perf_counter();r,_=run(ep,method,cfg);elapsed=time.perf_counter()-t
            current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            rows.append(dict(n=n,method=method,seconds=elapsed,peak_traced_MiB=peak/2**20,
                             update_mean_ms=r.get('latency_mean_ms'),p99_ms=r.get('latency_p99_ms'),
                             failure=r['failure'],headroom_vs_54s=54000/max(r.get('latency_p99_ms',float('inf')),1e-6)))
            print('scaling',n,method,elapsed,flush=True)
    write_json(out/'scaling.json',rows)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',choices=['development','synthetic','observability','scaling']);p.add_argument('--out',default='results/studies');a=p.parse_args()
    globals()[a.study](a.out)
