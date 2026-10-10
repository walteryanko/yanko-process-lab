import numpy as np
from src.plant.model import *
from lbe.learning import build_step
from lbe.config import SENSOR_STD

class HybridUKF:
    def __init__(self,x,learned=False,adaptive=False,augmented=False,euler=False,kind='UKF'):
        self.n=8 if augmented else 6;self.x=np.r_[x,[0.,0.]] if augmented else x.copy()
        self.P=np.diag(np.r_[np.diag(P0),[.02**2,.03**2]] if augmented else np.diag(P0))
        self.R=RBASE.copy();self.baseQ=np.r_[QFIX,[1e-6,1e-6]] if augmented else QFIX.copy()
        self.qscale=1.;self.adaptive=adaptive;self.f=build_step(learned,euler);self.fm=self.f.map(2*self.n+1)
        self.nis=np.nan;self.innovation=np.zeros(2);self.repairs=0;self.kind=kind
    @property
    def state(self):return self.x[:6]
    @property
    def bias(self):return self.x[6:8] if self.n==8 else np.zeros(2)
    def cycle(self,u,p,z):
        n=self.n;alpha=.3;c=alpha**2*n
        w=np.full(2*n+1,1/(2*c));w[0]=(c-n)/c;wc=w.copy();wc[0]+=3-alpha**2
        P=(self.P+self.P.T)/2
        try:L=np.linalg.cholesky(c*P)
        except np.linalg.LinAlgError:
            e,v=np.linalg.eigh(P);P=(v*np.maximum(e,1e-12))@v.T;L=np.linalg.cholesky(c*P);self.repairs+=1
        s=self.x+np.vstack([np.zeros(n),L.T,-L.T]);s[:,:4]=np.maximum(s[:,:4],1e-8)
        bs=s[:,6:].T if n==8 else np.zeros((2,2*n+1))
        pred=np.array(self.fm(s[:,:6].T,np.tile(u[:,None],(1,2*n+1)),np.tile(np.array([p.FB,p.FM,p.T0])[:,None],(1,2*n+1)),bs)).T
        if n==8:pred=np.c_[pred,s[:,6:]]
        mu=w@pred;dif=pred-mu;PP=(dif.T*wc)@dif+np.diag(self.baseQ*self.qscale)
        available=np.isfinite(z);ix=np.flatnonzero(available)+4
        if len(ix):
            R=self.R[np.ix_(available,available)];S=PP[np.ix_(ix,ix)]+R;nu=z[available]-mu[ix]
            K=np.linalg.solve(S,PP[:,ix].T).T;self.x=mu+K@nu
            H=np.eye(n)[ix];A=np.eye(n)-K@H;self.P=A@PP@A.T+K@R@K.T
            self.nis=float(nu@np.linalg.solve(S,nu));self.innovation=np.zeros(2);self.innovation[available]=nu
            if self.adaptive:
                # Slow covariance matching, projected to SPD diagonal bounds. Not a consistency proof.
                target=np.maximum(nu*nu-np.diag(PP[np.ix_(ix,ix)]),.25*SENSOR_STD[available]**2)
                rr=np.diag(self.R).copy();rr[available]=np.clip(.99*rr[available]+.01*target,.25*SENSOR_STD[available]**2,4*SENSOR_STD[available]**2)
                self.R=np.diag(rr);self.qscale=float(np.clip(.98*self.qscale+.02*self.nis/len(ix),.3,10))
        else:self.x=mu;self.P=PP;self.nis=np.nan
        self.x[:4]=np.maximum(self.x[:4],1e-8);self.x[4:6]=np.clip(self.x[4:6],275,395)
        if n==8:self.x[6:]=np.clip(self.x[6:],-.30,.30)
        self.P=(self.P+self.P.T)/2
        return self.state
