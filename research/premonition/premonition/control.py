"""Detector -> Supervisor -> NMPC -> independent ConstraintGuard -> fallback.
Risk is a dimensionless penalty, never labelled an accident probability.
"""
import numpy as np,time
from .physics import *
MODES={'C0':0,'C1':1,'C2':2,'C3':3,'C4':4,'conservative':5,'oracle_offline':6,'C4_noEWS':4}

@njit(cache=True)
def objective(x,seq,previous,sp,uh,ph,mode,warning,sigma):
    z=x.copy();cost=0.;violation=0.;peak=x[4];prev=previous;dyn=0.;thermal=0.;headroom=0.
    for k in range(57):
        w=seq[min(k,5)]
        if uh.shape[1]>6:w=min(w,uh[k,6])
        u=uh[k].copy();u[3]=w;p=ph[k]
        z=step(z,u,p,n=3)
        if not physical(z):return 1e12,1e12,500.,1e12
        cost+=.8*((sp-z[2])/sp)**2
        if k<6:cost+=.2*((w-prev)/U0[3])**2;prev=w
        peak=max(peak,z[4]);violation+=max(0.,z[4]-344.)**2
        if mode in (1,3,4,5):
            margin=2. if mode==1 else 1.+2.*warning if mode in (3,4) else 4.
            thermal+=.02*max(0.,z[4]-(344.-margin))**2
        if mode==2 or mode==4:
            J=jacobian(z,u,p);a=J[0,0];b=J[0,4];c=J[4,0]+J[4,1]-J[4,2];d=J[4,4]
            ar=(a+d+np.sqrt(max(0.,(a-d)**2+4*b*c)))/2
            res=0.
            dz=rhs(z,u,p)
            for j in range(6):res+=(dz[j]/SCALE[j])**2
            if res<1.:dyn+=.02*max(0.,ar+1.)**2
        if mode==4:
            headroom+=.0001*(w/UMAX)**4*(1.+min(sigma,3.))
    if mode>0:cost+=thermal+dyn+headroom
    return cost,violation,peak,thermal+dyn+headroom

@njit(cache=True)
def optimize(x,u,sequence,previous,sp,uh,ph,mode,warning,sigma):
    seq=np.empty(6);seq[:5]=sequence[1:];seq[5]=sequence[5]
    best=objective(x,seq,previous,sp,uh,ph,mode,warning,sigma)
    for delta in (120.,45.,15.):
        for j in range(6):
            for sign in (-1.,1.):
                trial=seq.copy();trial[j]=min(UMAX,max(UMIN,trial[j]+sign*delta));v=objective(x,trial,previous,sp,uh,ph,mode,warning,sigma)
                if v[1]<best[1]-1e-7 or (abs(v[1]-best[1])<=1e-7 and v[0]<best[0]):seq=trial;best=v
    return seq,best

class Supervisor:
    def __init__(self):self.counter=0;self.active=False;self.failures=0
    def decide(self,score,threshold,physical_warning=False):
        if not np.isfinite(score):self.failures+=1;self.counter=0;self.active=False;return False
        self.counter=self.counter+1 if score>=threshold else 0
        self.active=self.counter>=2 or physical_warning
        return self.active

class ConstraintGuard:
    def check(self,x,sequence,previous,sp,uh,ph):
        if not np.all(np.isfinite(sequence)) or np.min(sequence)<UMIN or np.max(sequence)>UMAX:return False,'invalid_action'
        value=objective(x,sequence,previous,sp,uh,ph,0,0.,0.)
        return bool(value[1]<=1e-6), 'feasible' if value[1]<=1e-6 else 'predicted_infeasible'

class NMPC:
    def __init__(self,mode='C0'):
        self.mode=mode;self.sequence=np.full(6,U0[3]);self.previous=U0[3];self.supervisor=Supervisor();self.guard=ConstraintGuard()
    def action(self,obs,detection,thresholds,future=None):
        start=time.perf_counter();u=obs.u;x=obs.xhat;mode=MODES[self.mode];uh=np.tile(u,(57,1));ph=np.tile(P,(57,1))
        if self.mode=='oracle_offline':
            if future is None:raise ValueError('Offline oracle needs explicit evaluator-only future')
            uh,ph,x=future
        score_name='D4' if self.mode=='C3' else 'D5_noEWS' if self.mode=='C4_noEWS' else 'D5'
        score=detection['scores'].get(score_name,np.nan);threshold=thresholds.get(score_name,1.)
        physical_warning=detection['scores'].get('D1',-1)>-1
        active=self.supervisor.decide(score,threshold,physical_warning) if self.mode in ['C3','C4','C4_noEWS'] else False
        warning=float(active);sigma=np.sqrt(obs.covariance[4,4]);sp=self.sp
        seq,best=optimize(x,u,self.sequence,self.previous,sp,uh,ph,mode,warning,sigma)
        ok,reason=self.guard.check(x,seq,self.previous,sp,uh,ph);fallback='none'
        if not ok:
            if mode!=0:
                nominal,ns=optimize(x,u,self.sequence,self.previous,sp,uh,ph,0,0.,sigma)
                feasible,_=self.guard.check(x,nominal,self.previous,sp,uh,ph)
                if feasible:seq=nominal;best=ns;fallback='nominal';ok=True
            if not ok:
                seq=np.full(6,UMAX);fallback='max_cooling'
                # Record that this is best effort, not a claim of feasible rescue.
                best=objective(x,seq,self.previous,sp,uh,ph,0,0.,sigma)
                ok,_=self.guard.check(x,seq,self.previous,sp,uh,ph)
        intervention=bool(active and self.mode in ['C3','C4','C4_noEWS']);self.sequence=seq;self.previous=float(seq[0])
        return self.previous,dict(feasible=ok,guard_reason=reason,fallback=fallback,intervention=intervention,score=float(score) if np.isfinite(score) else None,predicted_peak=float(best[2]),objective=float(best[0]),risk_penalty=float(best[3]),seconds=time.perf_counter()-start,
             optimizer_failed=bool(not np.isfinite(best[0]) or best[0]>=1e12),optimization='bounded fixed-budget coordinate search, no stationarity certificate')
