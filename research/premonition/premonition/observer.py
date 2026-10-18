"""Causal estimator contract: advance(previous applied inputs, current temperatures).
No plant parameter, truth state, episode or future trajectory arguments.
"""
from dataclasses import dataclass
import numpy as np
from .physics import *
CONV=np.array([CUNIT]*4+[1/1.8]*2)
QH=np.array([5.616e-8]*3+[2.4246e-13,.0346356,.0066123])*CONV**2
RH=np.diag((np.array([1.385,1.062])/1.8)**2)
H=np.eye(6)[[4,5]]

def spd(A):
    A=(A+A.T)/2;e,V=np.linalg.eigh(A)
    return (V*np.maximum(e,1e-12))@V.T

class UKF:
    def __init__(self,x=None,mode='historical',R=None):
        self.x=BASE.copy() if x is None else np.array(x,float).copy();self.P=np.diag([.08**2,.3**2,.1**2,.08**2,.6**2,.6**2])
        self.mode=mode;self.R=RH.copy() if R is None else R.copy();self.q=QH.copy();self.failures=0;self.innov=np.zeros(2);self.nis=0.;self.last_failure=None
    def advance(self,u,y):
        prior_x=self.x.copy();prior_P=self.P.copy()
        try:
            if self.mode=='ekf':
                xp=step(self.x,u);F=np.eye(6)+DT*jacobian(self.x,u);pp=F@self.P@F.T+np.diag(self.q)
            else:
                alpha=.001 if self.mode=='historical' else .35;n=6;c=alpha*alpha*n
                L=np.linalg.cholesky(c*spd(self.P));sig=np.r_[self.x[None,:],self.x[None,:]+L.T,self.x[None,:]-L.T]
                pts=np.empty_like(sig)
                for j in range(13):pts[j]=sig[j]+DT*rhs(sig[j],u) if self.mode=='historical' else step(sig[j],u)
                wm=np.full(13,.5/c);wm[0]=1-n/c;wc=wm.copy();wc[0]+=3-alpha**2
                # Reference-shift reduces cancellation at historical alpha=1e-3.
                xp=pts[0]+wm@(pts-pts[0]);d=pts-xp;pp=(d*wc[:,None]).T@d+np.diag(self.q)
            pp=spd(pp);mask=np.isfinite(y);ix=np.flatnonzero(mask)+4;innov=np.zeros(2)
            if len(ix):
                h=np.eye(6)[ix];r=self.R[np.ix_(mask,mask)];S=h@pp@h.T+r;K=np.linalg.solve(S,(pp@h.T).T).T
                resid=np.asarray(y)[mask]-xp[ix];xn=xp+K@resid;A=np.eye(6)-K@h;pn=spd(A@pp@A.T+K@r@K.T);innov[mask]=resid;self.nis=float(resid@np.linalg.solve(S,resid))
            else:xn=xp;pn=pp;self.nis=0.
            if not physical(xn):raise ValueError('Posterior outside physical domain')
            self.x=xn;self.P=pn;self.innov=innov
            if self.mode=='adaptive':self.q[4:]=np.clip(QH[4:]*max(1.,self.nis/2),QH[4:],QH[4:]*20)
        except (ValueError,np.linalg.LinAlgError,FloatingPointError) as e:
            self.failures+=1;self.last_failure=str(e)
            pred=step(prior_x,u)
            self.x=pred if physical(pred) else prior_x
            self.P=spd(prior_P+np.diag([.01,.01,.01,.001,.25,.25]));self.innov=np.zeros(2)
        return self.x.copy(),self.P.copy()

@dataclass(frozen=True)
class Observation:
    y:np.ndarray
    u:np.ndarray
    xhat:np.ndarray
    covariance:np.ndarray
    innovation:np.ndarray
    nis:float
