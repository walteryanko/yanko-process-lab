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
    cfg=FilterConfig(particles=64,bandwidth=.05,epsilon=.02)
    candidates=[('enkf','M1',cfg)]
    candidates += [(f'sb{n}','M4',replace(cfg,bridge_steps=n)) for n in [32,64,128]]
    candidates += [(f'h{h}','M4',replace(cfg,bandwidth=h)) for h in [.02,.1]]
    candidates += [(f'eps{e}','M3',replace(cfg,epsilon=e)) for e in [.005,.02,.1]]
    candidates += [(f'gate{t}','M5',replace(cfg,threshold=t)) for t in [2.,6.]]
    for sc in ['gaussian','weak_thermal']:
        for seed in range(101,109):
            ep=generate(seed,sc,20)
            for name,m,c in candidates:
                r,_=run(ep,m,c);r['candidate']=name;rows.append(r)
            print('development',sc,seed,flush=True)
    write_json(out/'development_runs.json',rows);summary=[]
    for name,m,c in candidates:
        rr=[r for r in rows if r['candidate']==name];good=[r for r in rr if not r['failure']]
        summary.append(dict(candidate=name,method=m,config=serial(c.__dict__),n=len(rr),failed=len(rr)-len(good),
          crps=float(np.mean([r['crps'][2] for r in good])),rmse=float(np.mean([r['rmse'][2] for r in good])),
          fallback_fraction=sum(r['fallback_count'] for r in good)/sum(r['steps_completed'] for r in good),
          bridge_updates=sum(r['bridge_updates'] for r in good)))
    ref={(r['scenario'],r['seed']):r for r in rows if r['candidate']=='enkf'};gates=[]
    for name in ['gate2.0','gate6.0']:
        rr=[r for r in rows if r['candidate']==name];delta=[]
        for seed in range(101,109):delta.append(np.mean([r['crps'][2]-ref[(r['scenario'],r['seed'])]['crps'][2] for r in rr if r['seed']==seed]))
        rng=np.random.default_rng(45);ci=np.quantile(rng.choice(delta,(2000,len(delta))).mean(1),[.025,.975])
        gates.append(dict(candidate=name,mean_delta_crps=np.mean(delta),ci95=ci,enabled=bool(ci[1]<0)))
    # Freeze test settings only from development. Require >=90% converged M3 updates.
    eligible=[r for r in summary if r['method']=='M3' and r['fallback_fraction']<=.1 and not r['failed']]
    best=min(eligible,key=lambda r:r['crps']) if eligible else None
    sb=min([r for r in summary if r['method']=='M4' and not r['failed']],key=lambda r:r['crps'])
    write_json(out/'selection.json',dict(summary=summary,gates=gates,epsilon=best['config']['epsilon'] if best else None,
        bandwidth=sb['config']['bandwidth'],bridge_steps=sb['config']['bridge_steps'],
        adaptive_enabled=any(g['enabled'] for g in gates),adaptive_threshold=None,
        rule='M3: <=10% fallback then lowest CRPS. M4: lowest CRPS. Gate: upper paired seed-cluster CI95 < 0.',
        dev_seeds=list(range(101,109)),test_seeds=list(range(2000,2100))))

def observability(out):
    from .filters import parameter_std
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    def outputs(x,theta=None,excited=False):
        yy=[x[4]];xx=[x.copy()]
        for k in range(80):
            u=U0.copy()
            if excited:u[0]*=1+.1*np.sin(k/8);u[3]*=1+.02*np.sin(k/11)
            x=step(x,u,theta=theta);yy.append(x[4]);xx.append(x.copy())
        return np.array(yy),np.array(xx)
    jac=[]
    for j in range(5):
        d=np.eye(5)[j]*SCALES[j]*1e-4
        jac.append((outputs(BASE+d)[0]-outputs(BASE-d)[0])/(2e-4*1.5))
    J=np.array(jac).T;_,sv,v=np.linalg.svd(J,full_matrices=False);jp=[]
    for j in range(5):
        d=np.eye(5)[j]*parameter_std()[j]*1e-3
        jp.append((outputs(BASE,d)[0]-outputs(BASE,-d)[0])/(2e-3*1.5))
    joint=np.linalg.svd(np.column_stack([J,np.array(jp).T]),compute_uv=False)
    direction=v[-1]*SCALES
    amplitude=min(.8,min(BASE[:4]/np.maximum(abs(direction[:4]),1e-12))*.8)
    x1=BASE-amplitude*direction;x2=BASE+amplitude*direction
    t1,h1=outputs(x1);t2,h2=outputs(x2);te1,_=outputs(x1,excited=True);te2,_=outputs(x2,excited=True)
    write_json(out/'observability.json',dict(singular_values=sv,rank_relative_1e_7=int(sum(sv>sv[0]*1e-7)),
       scaled_directions=v,joint_singular_values=joint,joint_rank_relative_1e_7=int(sum(joint>joint[0]*1e-7)),
       hypotheses=[x1,x2],histories=[h1,h2],time=np.arange(81)*DT,
       initial_CEB_separation=abs(x1[2]-x2[2]),final_CEB_separation=abs(h1[-1,2]-h2[-1,2]),
       thermal_rms=float(np.sqrt(np.mean((t1-t2)**2))),thermal_kl=float(np.sum((t1-t2)**2)/(2*2.25)),
       excited_thermal_kl=float(np.sum((te1-te2)**2)/(2*2.25)),
       interpretation='Local sensitivity diagnostic, not a global identifiability theorem. Hypotheses demonstrate ambiguity, not posterior modes.'))

def reference(out):
    from .filters import make_filter
    from scipy.stats import gaussian_kde
    out=Path(out);out.mkdir(parents=True,exist_ok=True);ep=generate(2000,'weak_thermal',60);snapshots=[]
    for n in [4096,8192]:
        cfg=FilterConfig(particles=n);m,p=initial('weak_thermal');R,_=measurement_spec('weak_thermal')
        f=make_filter('M2',m,p,R,cfg,2000+987654)
        for k,(u,y) in enumerate(zip(ep['u'],ep['y'])):
            f.advance(u,y)
            if k in [0,7,23,59]:
                x,w,_=f.posterior();grid=np.linspace(x[:,2].min()-.05,x[:,2].max()+.05,401);kdes=[]
                for factor in [.8,1.,1.2]:
                    kde=gaussian_kde(x[:,2],weights=w);kde.set_bandwidth(kde.factor*factor);d=kde(grid)
                    peaks,_=find_peaks(d,prominence=.05*d.max())
                    kdes.append(dict(factor=factor,density=d,modes=grid[peaks]))
                snapshots.append(dict(n=n,step=k,grid=grid,kdes=kdes,particles=x[:,2],weights=w,
                    true_CEB=ep['true'][k+1,2],mean=float(w@x[:,2]),ess=ess(w)))
        print('reference PF',n,flush=True)
    write_json(out/'posterior_reference.json',dict(seed=2000,scenario='weak_thermal',snapshots=snapshots,
        limitation='Two particle counts, one trajectory, KDE bandwidth sensitivity. High-resolution numerical reference, not exact posterior.'))

def scaling(out):
    from .filters import make_filter
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
    for n in [64,128,256,512,1024]:
        ep=generate(901,'gaussian',6);cfg=FilterConfig(particles=n)
        for method in ['M0','M1','M2','M3','M4']:
            m,p=initial('gaussian');R,_=measurement_spec('gaussian');f=make_filter(method,m,p,R,cfg,42)
            f.advance(ep['u'][0],ep['y'][0]);lat=[];failure=None
            tracemalloc.start()
            try:
                for k in range(1,6):f.advance(ep['u'][k],ep['y'][k]);lat.append(f.last['latency_ms'])
            except Exception as ex:failure=str(ex)
            _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
            rows.append(dict(n=n,method=method,samples=len(lat),update_mean_ms=np.mean(lat),p95_ms=np.quantile(lat,.95),
                p99_ms=np.quantile(lat,.99),peak_traced_MiB=peak/2**20,failure=failure,headroom_vs_90s=90000/max(lat)))
            print('scaling',n,method,flush=True)
    write_json(out/'scaling.json',rows)

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


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',choices=['development','synthetic','observability','reference','scaling'])
    p.add_argument('--out',default='results/studies');a=p.parse_args();globals()[a.study](a.out)

