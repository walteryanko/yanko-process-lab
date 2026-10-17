from dataclasses import dataclass
import time
import numpy as np
from .model import BASE,Q_PUBLISHED,H,SCALES,step,valid
from .probability import normalize,ess,systematic,moments,spd,loglik,robust_cov,non_gaussianity
from .transport import transform
from .bridge import generate

@dataclass
class FilterConfig:
    particles: int = 128
    epsilon: float = .001
    bridge_steps: int = 64
    bandwidth: float = .05
    max_step: float = .0025
    likelihood: str = 'gaussian'
    joint: bool = False
    threshold: float = float('inf')
    resample_ess: float = .5
    sinkhorn_max_iter: int = 1000

def parameter_std():return np.array([.08,.08,.025,.04])

def propagate(x,u,cfg):
    a=np.array(x,copy=True)
    a[...,:6]=step(a[...,:6],u,max_step=cfg.max_step,theta=a[...,6:10] if cfg.joint else None)
    return a

def physical(x,cfg):
    ok=valid(x[...,:6])
    if cfg.joint:ok=ok & np.all(np.abs(x[...,6:10])<1.,axis=-1)
    return ok

def sample_prior(mean,cov,n,rng,cfg):
    out=rng.multivariate_normal(mean,spd(cov),size=n);rejected=0
    for _ in range(100):
        bad=~physical(out,cfg)
        if not np.any(bad):return out,rejected
        rejected+=int(bad.sum());out[bad]=rng.multivariate_normal(mean,spd(cov),size=bad.sum())
    raise ValueError('Prior rejection sampler failed')

class UKF:
    def __init__(self,mean,cov,R,cfg,seed=0,original=False):
        self.cfg=cfg;self.x=mean.copy();self.P=cov.copy();self.R=R;self.rng=np.random.default_rng(seed)
        self.original=original;self.last={};self.n=len(mean)
        self.q=np.r_[Q_PUBLISHED,np.zeros(self.n-6)]
    def advance(self,u,y):
        start=time.perf_counter();n=self.n;alpha=.001 if self.original else .35;c=alpha**2*n
        wm=np.full(2*n+1,1/(2*c));wm[0]=1-n/c;wc=wm.copy();wc[0]+=3-alpha**2
        L=np.linalg.cholesky(c*spd(self.P));pts=np.r_[self.x[None,:],self.x+L.T,self.x-L.T]
        # Domain violations are explicit failures, not clipped sigma points.
        if not np.all(physical(pts,self.cfg)):raise ValueError('UKF sigma points outside domain')
        if self.original:
            pts[:,:6]=step(pts[:,:6],u,method='euler')
        else:pts=propagate(pts,u,self.cfg)
        xp=wm@pts;d=pts-xp;pp=(d*wc[:,None]).T@d+np.diag(self.q)
        pp=spd(pp);mask=np.isfinite(y);ix=np.flatnonzero(mask)+4
        if len(ix):
            hh=np.eye(n)[ix];rr=self.R[np.ix_(mask,mask)];innov=y[mask]-xp[ix]
            rr=robust_cov(innov,rr,pp[np.ix_(ix,ix)],self.cfg.likelihood)
            ss=hh@pp@hh.T+rr;k=np.linalg.solve(ss,(pp@hh.T).T).T
            xn=xp+k@innov;a=np.eye(n)-k@hh;pn=spd(a@pp@a.T+k@rr@k.T)
        else:xn,pn=xp,pp
        if not physical(xn,self.cfg):raise ValueError('UKF posterior outside domain')
        self.x=xn;self.P=pn;self.last=dict(latency_ms=1000*(time.perf_counter()-start),ess=None,
                                         fallback=0,rejected=0,branch='gaussian',ng=None)
        return self.x,self.P
    def posterior(self,n=None,seed=0):
        a,rejected=sample_prior(self.x,self.P,n or self.cfg.particles,np.random.default_rng(seed),self.cfg)
        return a,np.full(len(a),1/len(a)),rejected

class Ensemble:
    def __init__(self,kind,mean,cov,R,cfg,seed=0):
        self.kind=kind;self.cfg=cfg;self.R=R;self.rng=np.random.default_rng(seed)
        self.x,self.initial_rejected=sample_prior(mean,cov,cfg.particles,self.rng,cfg)
        self.w=np.full(len(self.x),1/len(self.x));self.last={};self.plan=None;self.transport_source=None
        self.q=np.r_[Q_PUBLISHED,np.zeros(len(mean)-6)];self.path=None
    def enkf(self,prior,y):
        n=len(prior);mask=np.isfinite(y);ix=np.flatnonzero(mask)+4
        if not len(ix):return prior.copy()
        mean=prior.mean(0);d=prior-mean;cov=d.T@d/(n-1)
        rr=self.R[np.ix_(mask,mask)];res=y[mask]-mean[ix]
        rr=robust_cov(res,rr,cov[np.ix_(ix,ix)],self.cfg.likelihood)
        k=np.linalg.solve(cov[np.ix_(ix,ix)]+rr,cov[:,ix].T).T
        noise=self.rng.multivariate_normal(np.zeros(len(ix)),rr,size=n)
        return prior+(y[mask]+noise-prior[:,ix])@k.T
    def advance(self,u,y,inspect=False):
        start=time.perf_counter();n=len(self.x);self.plan=None;self.path=None
        prior=propagate(self.x,u,self.cfg)
        noise=self.rng.normal(size=prior.shape)*np.sqrt(self.q)
        new=prior+noise;rejected=0
        for _ in range(100):
            bad=~physical(new,self.cfg)
            if not np.any(bad):break
            rejected+=int(bad.sum());new[bad]=prior[bad]+self.rng.normal(size=(bad.sum(),prior.shape[1]))*np.sqrt(self.q)
        else:raise ValueError('Process-noise rejection failed')
        prior=new;ll=loglik(prior,y,self.R,self.cfg.likelihood)
        w=normalize(np.log(np.maximum(self.w,1e-300))+ll)
        neff=ess(w);ng=non_gaussianity(prior,w);branch=self.kind;fallback=0;td={};bd={}
        if self.kind=='adaptive':
            branch='bridge' if ng>self.cfg.threshold and neff/n>.05 else 'enkf'
        observed=bool(np.any(np.isfinite(y)))
        if branch=='enkf':
            out=self.enkf(prior,y);weights=np.full(n,1/n)
        elif branch=='pf':
            if neff<n*self.cfg.resample_ess:
                out=prior[systematic(w,self.rng)];weights=np.full(n,1/n)
            else:out=prior;weights=w
        elif not observed:
            out=prior;weights=self.w.copy()
        elif branch=='transport':
            scales=np.r_[SCALES,parameter_std()] if self.cfg.joint else SCALES
            try:
                out,self.plan,td=transform(prior,w,scales,self.cfg.epsilon,max_iter=self.cfg.sinkhorn_max_iter)
                self.transport_source=prior.copy()
            except ArithmeticError:
                out=prior[systematic(w,self.rng)];fallback=1;td={'converged':False}
            weights=np.full(n,1/n)
        elif branch=='bridge':
            out,bd,self.path=generate(prior,w,self.rng,self.cfg.bridge_steps,self.cfg.bandwidth,save_path=inspect)
            weights=np.full(n,1/n)
        else:raise ValueError('Unknown ensemble method: '+branch)
        bad=~physical(out,self.cfg)
        if np.any(bad):
            # Explicit whole-analysis PF fallback avoids hidden per-particle projection.
            rejected+=int(bad.sum());out=prior[systematic(w,self.rng)];weights=np.full(n,1/n);fallback+=1
        self.x,self.w=out,weights
        self.last=dict(latency_ms=1000*(time.perf_counter()-start),ess=neff,fallback=fallback,
                       rejected=rejected,branch=branch,ng=ng,transport=td,bridge=bd,
                       unique_fraction=float(len(np.unique(out,axis=0))/n),
                       posterior_ess=ess(weights))
        return moments(self.x,self.w)
    def posterior(self,n=None,seed=0):return self.x.copy(),self.w.copy(),0

METHODS={'M0':'UKF RK4','M1':'EnKF','M2':'Bootstrap PF','M3':'Entropic transform PF',
         'M4':'Schrödinger–Föllmer / EnSBF','M5':'Adaptive (development gate)'}

def make_filter(method,mean,cov,R,cfg,seed):
    if method in ('M0','M0_original'):return UKF(mean,cov,R,cfg,seed,original=method=='M0_original')
    return Ensemble({'M1':'enkf','M2':'pf','M3':'transport','M4':'bridge','M5':'adaptive'}[method],mean,cov,R,cfg,seed)
