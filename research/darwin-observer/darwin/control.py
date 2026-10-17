"""Port of ProcessLab's NMPC: p=57, m=6, Ts=.015, coordinate search.

Same six-state RHS as the observer. Feasibility has lexicographic priority.
This is not a proof of closed-loop robustness or industrial safety.
"""
import time
import numpy as np
from .physics import njit,transition,U0,BASE,NP,Model,DT
from .observers import OnlineUKF
from .discovery import GuardedDarwin

@njit(cache=True)
def objective(x,u,seq,previous,sp,p):
    state=x.copy();cost=0.;violation=0.;peak=state[4];prev=previous
    for k in range(57):
        w=seq[min(k,5)];uu=u.copy();uu[3]=w
        state=transition(state,uu,p)
        if not np.all(np.isfinite(state)) or np.any(state[:4]<0):return 1e15,1e15,1e15
        cost+=.8*((sp-state[2])/sp)**2
        if k<6:cost+=.2*((w-prev)/453.6)**2;prev=w
        peak=max(peak,state[4]);violation+=max(0.,state[4]-344.)**2
    return cost,violation,peak

@njit(cache=True)
def optimize(x,u,sequence,previous,sp,p):
    seq=np.empty(6);seq[:5]=sequence[1:];seq[5]=sequence[5]
    best=objective(x,u,seq,previous,sp,p)
    for step in (120.,45.,15.):
        for j in range(6):
            for sign in (-1.,1.):
                trial=seq.copy();trial[j]=min(1366.2,max(22.7,trial[j]+sign*step));v=objective(x,u,trial,previous,sp,p)
                better=v[1]<best[1]-1e-7 or (abs(v[1]-best[1])<=1e-7 and v[0]<best[0])
                if better:seq=trial;best=v
    return seq,best

class NMPC:
    def __init__(self):self.sequence=np.full(6,453.6);self.previous=453.6;self.events=[];self.steps=0
    def action(self,x,u,sp,model=None):
        self.steps+=1;p=np.zeros(NP) if model is None else model.params
        seq,score=optimize(x,u,self.sequence,self.previous,sp,p);reverted=False
        # Validate every planned move, not just the current cooling flow.
        supported=True
        if model is not None:
            lo,hi,tlo,thi=model.envelope
            supported=bool(model.supports(x,u) and np.all((seq>=lo)&(seq<=hi)))
            if supported:
                predicted=x.copy()
                for k in range(57):
                    proposed=u.copy();proposed[3]=seq[min(k,5)]
                    predicted=transition(predicted,proposed,p)
                    if not np.all(np.isfinite(predicted)) or np.any(predicted[:4]<0) or not tlo<=predicted[4]<=thi:
                        supported=False;break
        if model is not None and (score[1]>1e-6 or not supported):
            seq0,score0=optimize(x,u,self.sequence,self.previous,sp,np.zeros(NP))
            # Conservative model-update policy: reversion on unvalidated feasibility.
            seq,score=seq0,score0;reverted=True;self.events.append(dict(step=self.steps,state='MODEL_FALLBACK'))
        feasible=score[1]<=1e-6
        if not feasible:
            # Explicit protective action, no false claim that optimization was feasible.
            seq=np.full(6,1366.2);self.events.append(dict(step=self.steps,state='MAX_COOLING',predicted_peak=float(score[2])))
        self.sequence=seq;self.previous=float(seq[0])
        return self.previous,dict(feasible=bool(feasible),model_fallback=reverted,predicted_peak=float(score[2]))

def rollout(seed,mode,discovery,steps=60,law=1,strength=.4,monitor=True):
    # Evaluator alone imports the plant; neither controller nor estimator sees it.
    from .truth import hidden_step
    rng=np.random.default_rng(seed);x=BASE.copy();x[:4]+=rng.normal(0,[.03,.2,.05,.03]);x[4:]+=rng.normal(0,.25,2)
    noise=rng.normal(0,.2,(steps,2));ctl=NMPC()
    obs=OnlineUKF(adaptive=mode=='adaptive_nominal') if mode in ('nominal','adaptive_nominal') else GuardedDarwin(discovery,monitor)
    xhat=BASE.copy();rows=[];start=time.perf_counter();previous=453.6
    for k in range(steps):
        u=U0.copy();u[4]+=3.*(k>=steps//3)-2.*(k>=2*steps//3)
        sp=2.47 if k<steps//2 else 2.53
        model=None
        if mode=='darwin_corrected' and obs.accepted:model=obs.active.model
        t0=time.perf_counter();mw,diagnostic=ctl.action(xhat,u,sp,model);seconds=time.perf_counter()-t0
        u[3]=mw;x=hidden_step(x,u,law,strength);y=x[4:]+noise[k]
        xhat,_=obs.update(u,y);flow=u[0]/14.8+u[1]/55.3+u[2]/24.7
        rows.append(dict(step=k+1,t=(k+1)*DT,CC=float(x[2]),CC_est=float(xhat[2]),T=float(x[4]),Tt=float(x[5]),mw=mw,
            sp=sp,production=flow*x[2]*DT,effort=((mw-previous)/453.6)**2,seconds=seconds,**diagnostic))
        previous=mw
    return dict(seed=seed,method=mode,iae=float(sum(abs(r['CC']-r['sp'])*DT for r in rows)),
        rmse_CC=float(np.sqrt(np.mean([(r['CC']-r['CC_est'])**2 for r in rows]))),
        tracking_rmse=float(np.sqrt(np.mean([(r['CC']-r['sp'])**2 for r in rows]))),
        production_kmol=float(sum(r['production'] for r in rows)),effort=float(sum(r['effort'] for r in rows)),
        violations=sum(r['T']>344.+1e-7 for r in rows),peak_T=max(r['T'] for r in rows),
        feasible_fraction=float(np.mean([r['feasible'] for r in rows])),model_fallbacks=sum(r['model_fallback'] for r in rows),
        observer_fallbacks=obs.fallbacks if isinstance(obs,GuardedDarwin) else 0,
        seconds=time.perf_counter()-start,solver_mean_ms=1000*np.mean([r['seconds'] for r in rows]),rows=rows,
        events=ctl.events+(obs.events if isinstance(obs,GuardedDarwin) else []))
