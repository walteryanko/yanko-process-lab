"""Multiverse-MPC v0.1: finite-state scenario minimax-regret proof of concept.
Yanko ProcessLab, tabulated PG six-state model. Research-only synthetic experiment.
Model coefficients transcribed from github.com/walteryanko/yanko-process-lab,
lib/simulation/model.ts as fetched 2026-10-16. Not equivalent to historical SI variant.
"""
from __future__ import annotations
import argparse, csv, itertools, json, time
from pathlib import Path
import numpy as np
from scipy.optimize import brentq

CP=np.array([146.5,75.4,192.6,81.6]); RHO=np.array([14.8,55.3,24.7]); E=75362.4; RG=8.314; K0=16.96e12
HEAT=91556.9; V=1.89; VT=1.1; UA=30385.6
# Input order: FA FB FM mw Tfeed Tcool
U0=np.array([36.3,453.6,45.4,453.6,297.,289.]); DT=.015; MIN_MW=22.7; MAX_MW=1366.2
STUDY_LIMIT=344. # simulated research constraint only, not certified safety condition
QDIAG=np.array([5.616e-8,5.616e-5,5.616e-8,2.4246e-13,.0346356,.00666123])
SENSOR_STD=.25 # K: explicit lower-noise experimental regime, NOT historical 1% T reference
LEVELS=np.array([250.,453.6,900.,1200.]); H=9; BLOCK=3
SCHEDULES=np.array(list(itertools.product(LEVELS,repeat=H//BLOCK)),dtype=float)
UNIVERSE_SIGMAS=np.array([-1.75,-.85,0.,.85,1.75])

def deriv(x,u,ua=UA):
    """Vectorized exact transcription of ProcessLab model.ts (array ...x6)."""
    flow=u[...,0]/RHO[0]+u[...,1]/RHO[1]+u[...,2]/RHO[2]
    r=K0*np.exp(-E/(RG*x[...,4]))*x[...,0]
    q=u[...,3]*CP[1]*(u[...,5]-x[...,4])*(-np.expm1(-ua/(u[...,3]*CP[1])))
    cap=V*np.sum(x[...,:4]*CP,axis=-1)
    sens=(u[...,0]*CP[0]+u[...,1]*CP[1]+u[...,2]*CP[3])*(x[...,4]-u[...,4])
    out=np.empty_like(x)
    out[...,0]=(u[...,0]-flow*x[...,0])/V-r
    out[...,1]=(u[...,1]-flow*x[...,1])/V-r
    out[...,2]=r-flow*x[...,2]/V
    out[...,3]=(u[...,2]-flow*x[...,3])/V
    out[...,4]=(q-sens+HEAT*r*V)/cap
    out[...,5]=(u[...,3]*CP[1]*(u[...,5]-x[...,5])-q)/(RHO[1]*VT*CP[1])
    return out

def step(x,u,dt=DT,substep=.001,ua=UA):
    x=np.asarray(x,dtype=float).copy();u=np.asarray(u,dtype=float)
    n=max(1,int(np.ceil(dt/substep)));h=dt/n
    for _ in range(n):
        k1=deriv(x,u,ua);k2=deriv(x+.5*h*k1,u,ua);k3=deriv(x+.5*h*k2,u,ua);k4=deriv(x+h*k3,u,ua)
        x=x+h*(k1+2*k2+2*k3+k4)/6
    return x

def equilibrium():
    u=U0;fl=u[0]/RHO[0]+u[1]/RHO[1]+u[2]/RHO[2]
    def xof(t):
        k=K0*np.exp(-E/(RG*t));ca=u[0]/(fl+V*k);cc=V*k*ca/fl
        q=u[3]*CP[1]*(u[5]-t)*(-np.expm1(-UA/(u[3]*CP[1])))
        return np.array([ca,u[1]/fl-cc,cc,u[2]/fl,t,u[5]-q/(u[3]*CP[1])])
    f=lambda t:deriv(xof(t),u)[4]
    roots=[]
    for a in np.arange(260.,401.,.25):
        if f(a)*f(a+.25)<0:roots.append(brentq(f,a,a+.25,xtol=1e-11))
    if not roots:raise RuntimeError('No equilibrium found')
    return xof(max(roots))
BASE=equilibrium()


def ukf_update(x,p,u,z):
    """Causal 6-state UKF for fair information with original Q and explicit sensor R.
    Predict with RK4 vs ProcessLab UKF's Euler, so this is a new reference UKF.
    """
    n=6;alpha=.5;beta=2.;kappa=0.;lam=alpha**2*(n+kappa)-n;denom=n+lam
    wm=np.full(2*n+1,1/(2*denom)); wc=wm.copy();wm[0]=lam/denom;wc[0]=wm[0]+1-alpha**2+beta
    psym=(p+p.T)/2+np.eye(6)*1e-12
    L=np.linalg.cholesky(denom*psym)
    sig=np.concatenate([x[None,:],x[None,:]+L.T,x[None,:]-L.T],axis=0)
    pr=step(sig,np.broadcast_to(u,sig.shape))
    xp=np.sum(pr*wm[:,None],axis=0)
    d=pr-xp
    Pp=np.einsum('n,ni,nj->ij',wc,d,d)+np.diag(QDIAG)
    Rm=np.eye(2)*SENSOR_STD**2;Z=pr[:,4:6]
    zp=np.sum(Z*wm[:,None],axis=0);dz=Z-zp
    S=np.einsum('n,ni,nj->ij',wc,dz,dz)+Rm
    cx=np.einsum('n,ni,nj->ij',wc,d,dz)
    K=np.linalg.solve(S,cx.T).T
    xn=xp+K@(z-zp)
    hmat=np.zeros((2,6));hmat[0,4]=1;hmat[1,5]=1
    A=np.eye(6)-K@hmat
    pn=A@Pp@A.T+K@Rm@K.T
    pn=(pn+pn.T)/2
    xn[:4]=np.maximum(xn[:4],1e-8)
    return xn,pn

def scenarios(x,p,spread=1.0):
    """Mass-balance-consistent hidden-conversion axis [CA,CB,-CC] for first study.
    5 possible initial states; no access to true chemical state.
    """
    v=np.array([1.,1.,-1.,0.,0.,0.]);sigma=float(np.clip(np.sqrt(max(p[0,0],1e-8))*spread,.04,.24))
    # Clip shifts so concentrations never become negative.
    out=x[None,:]+UNIVERSE_SIGMAS[:,None]*sigma*v[None,:]
    out[:,:4]=np.maximum(out[:,:4],1e-7)
    return out

def costs(start_states,prev_mw,perturb=5.,target_t=None):
    """Enumerate shared input strings. Input perturb = known feed temperature bias.
    Per-scenario loss combines tracking, PG retention, and coolant use.
    """
    if target_t is None: target_t=BASE[4]-1.0
    nstart=len(start_states); nc=len(SCHEDULES)
    xx=np.broadcast_to(start_states[None,:,:],(nc,nstart,6)).copy()
    peaks=xx[...,4].copy();objective=np.zeros((nc,nstart))
    last=np.full((nc,nstart),prev_mw)
    for k in range(H):
        mw=np.repeat(SCHEDULES[:,k//BLOCK,None],nstart,axis=1)
        uu=np.broadcast_to(U0,(nc,nstart,6)).copy();uu[...,3]=mw;uu[...,4]+=perturb
        xx=step(xx,uu,substep=.003)
        peaks=np.maximum(peaks,xx[...,4]);overs=np.maximum(xx[...,4]-STUDY_LIMIT,0.)
        # Tracking (K), maximize product concentration vs small effort cost; same for all policies
        objective+=(xx[...,4]-target_t)**2 + 4.*(BASE[2]-xx[...,2])**2 + .018*((mw-453.6)/450.)**2 + .05*((mw-last)/450.)**2 + 100*overs**2
        last=mw
    return objective,peaks

def choose(est,p,prev,policy,spread=1.0,perturb=5.):
    worlds=scenarios(est,p,spread)
    losses,peaks=costs(worlds,prev,perturb)
    feasible=np.all(peaks<=STUDY_LIMIT+1e-9,axis=1)
    # Same candidate set, same constraints (nominal controller sees only its own estimate).
    # This research conservative gate evaluates all plausible worlds for both policies;
    # also score nominal only on its central (mean) scenario.
    if not np.any(feasible):
        feasible=np.min(peaks,axis=1)<=np.min(np.max(peaks,axis=1))+1e-9
    if policy=='nominal': score=losses[:,2]
    elif policy=='regret':
        per_world_best=np.min(np.where(feasible[:,None],losses,np.inf),axis=0)
        score=np.max(losses-per_world_best[None,:],axis=1)
    elif policy=='worst':score=np.max(losses,axis=1)
    else:raise ValueError(policy)
    winner=int(np.argmin(np.where(feasible,score,np.inf)))
    return float(SCHEDULES[winner,0]),winner,float(score[winner]),worlds,losses

def stage_cost(x,mw,prev,target_t=None):
    if target_t is None:target_t=BASE[4]-1.
    over=max(0,float(x[4])-STUDY_LIMIT)
    return ((float(x[4])-target_t)**2+4*(BASE[2]-float(x[2]))**2
           +.018*((mw-453.6)/450.)**2 + .05*((mw-prev)/450.)**2+100*over**2)

def rollout(seed,policy,nsteps=24,spread=1.,perturb=5.,hidden_delta=None,noise=None):
    rng=np.random.default_rng(seed)
    delta=float(rng.normal(0,.145)) if hidden_delta is None else float(hidden_delta)
    delta=np.clip(delta,-.28,.34)
    true=BASE.copy();true[:4]+=delta*np.array([1.,1.,-1.,0.])
    # temperatures identical across possible worlds at t=0 (partial observability).
    xhat=BASE.copy()
    p=np.diag([.16**2,.18**2,.16**2,.04**2,.4**2,.4**2])
    prev=U0[3];rows=[];total=0.;peakt=float(true[4]);sse_t=0.
    if noise is None:noise=rng.normal(0,SENSOR_STD,size=(nsteps,2))
    for k in range(nsteps):
        mw,idx,_,worlds,_=choose(xhat,p,prev,policy,spread,perturb)
        u=U0.copy();u[3]=mw;u[4]+=perturb
        true=step(true,u)
        z=true[4:6]+noise[k]
        xhat,p=ukf_update(xhat,p,u,z)
        j=stage_cost(true,mw,prev);total+=j;peakt=max(peakt,float(true[4]));sse_t+=(float(true[4])-BASE[4]+1)**2
        rows.append({'seed':seed,'policy':policy,'step':k,'hours':(k+1)*DT,'true_ca':true[0], 'true_cc':true[2], 'estimated_cc':xhat[2], 't':true[4], 'tt':true[5], 'mw':mw, 'loss_step':j, 'cum_loss':total,'study_exceedance':max(0.,true[4]-STUDY_LIMIT),'candidate':idx, 'hidden_delta':delta})
        prev=mw
    return {'policy':policy,'seed':seed,'delta':delta,'loss':total,'peak':peakt,'rmse_t':np.sqrt(sse_t/nsteps),'rmse_cc':float(np.sqrt(np.mean([(r['true_cc']-r['estimated_cc'])**2 for r in rows]))),'violations':int(sum(r['study_exceedance']>0 for r in rows)),'rows':rows}

def experiment(seeds=tuple(range(12)),nsteps=24,spread=1.0,perturb=5.0):
    rng=np.random.default_rng(248)
    outcomes=[];time_start=time.perf_counter()
    for i in seeds:
        # Common random numbers for fair paired trajectories.
        hidden=float(np.clip(rng.normal(0,.145),-.28,.34));noise=rng.normal(0,SENSOR_STD,size=(nsteps,2))
        for mode in ('nominal','regret','worst'):
            outcomes.append(rollout(i,mode,nsteps,spread,perturb,hidden,noise))
    return outcomes,time.perf_counter()-time_start

def summarize(runs):
    result={}
    for mode in ('nominal','regret','worst'):
        group=[r for r in runs if r['policy']==mode]
        result[mode]={k:float(np.mean([r[k] for r in group])) for k in ('loss','peak','rmse_t','rmse_cc','violations')}
    nom=np.array([r['loss'] for r in runs if r['policy']=='nominal'])
    for mode in ('regret','worst'):
        alt=np.array([r['loss'] for r in runs if r['policy']==mode])
        diff=nom-alt
        result[mode]['paired_gain_percent']=float(100*np.mean(diff)/np.mean(nom))
        result[mode]['wins']=int(np.sum(diff>1e-9));result[mode]['losses']=int(np.sum(diff<-1e-9));result[mode]['ties']=int(np.sum(np.abs(diff)<=1e-9));result[mode]['pair_diff_mean']=float(np.mean(diff))
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--trials',type=int,default=12);parser.add_argument('--steps',type=int,default=24);parser.add_argument('--spread',type=float,default=1.);parser.add_argument('--perturb',type=float,default=5.);parser.add_argument('--out',default='results');args=parser.parse_args()
    runs,seconds=experiment(range(args.trials),args.steps,args.spread,args.perturb);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    with open(out/'trajectories.csv','w',newline='') as f:
        w=csv.DictWriter(f,list(runs[0]['rows'][0]));w.writeheader();w.writerows(x for run in runs for x in run['rows'])
    with open(out/'episodes.csv','w',newline='') as f:
        w=csv.DictWriter(f,['seed','policy','delta','loss','peak','rmse_t','rmse_cc','violations']);w.writeheader();w.writerows({k:v for k,v in run.items() if k!='rows'} for run in runs)
    summary={'model':'Yanko ProcessLab: tabulated PG nonlinear 6-state, not historical', 'base':BASE.tolist(),'seed_policy':'Paired truth/noise, seed 248', 'n_trials':args.trials,'n_steps':args.steps,'spread':args.spread,'feed_temp_perturbation_K':args.perturb,'sensor_std_K':SENSOR_STD,'study_limit_K':STUDY_LIMIT,'results':summarize(runs),'execution_seconds':seconds}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
