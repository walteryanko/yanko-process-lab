"""Conservation-informed UKF: 3 measured/reactive states plus identifiable biases.

Assumes initial inventories and measured feed streams are known. Does not obtain
inventories or concentration from plant truth after initialization. Nuisance mass
balances are propagated analytically; this is a physical information assumption,
not a solution to structural unobservability with unknown inventory.
"""
import numpy as np
from src.plant.model import Parameters, U0, DT, P0, QFIX, RBASE, feed
from lbe.learning import build_step

class ReducedUKF:
    def __init__(self,x,augmented=False,learned=False,adaptive=False,kinetic_only=False,
                 parameter_q=1e-6,alpha=.3):
        self.augmented=augmented;self.learned=learned;self.adaptive=adaptive
        self.nb=(1 if kinetic_only else 2) if augmented else 0
        self.n=3+self.nb;self.z=np.r_[x[[0,4,5]],np.zeros(self.nb)]
        self.sums=np.array([x[0]+x[2],x[1]+x[2],x[3]])
        self.Pz=np.diag(np.r_[np.diag(P0)[[0,4,5]],np.array([.02**2,.03**2])[:self.nb]])
        self.baseQ=np.r_[QFIX[[0,4,5]],np.full(self.nb,parameter_q)]
        self.R=RBASE.copy();self.alpha=alpha;self.qscale=1.;self.repairs=0
        self.nis=np.nan;self.innovation=np.zeros(2)
        self.f=build_step(learned);self.fm=self.f.map(2*self.n+1)
        self._publish()
    @property
    def state(self):return self.x[:6]
    @property
    def bias(self):return np.r_[self.z[3:],np.zeros(2-self.nb)] if self.nb else np.zeros(2)
    def _full(self,z,sums):
        z=np.asarray(z);a=z[...,0];cc=sums[0]-a
        return np.stack([a,sums[1]-cc,cc,np.broadcast_to(sums[2],a.shape),z[...,1],z[...,2]],axis=-1)
    def _publish(self):
        xx=self._full(self.z,self.sums)
        self.x=np.r_[xx,self.bias] if self.nb else xx
        J=np.zeros((6,self.n));J[0,0]=1;J[1,0]=1;J[2,0]=-1;J[4,1]=1;J[5,2]=1
        pp=J@self.Pz@J.T
        # Tiny stated numerical floor, not fake uncertainty for unknown feed.
        pp+=np.eye(6)*1e-12
        if self.nb:
            fullJ=np.zeros((8,self.n));fullJ[:6]=J
            fullJ[6:,3:]=np.eye(2)[:,:self.nb]
            self.P=fullJ@self.Pz@fullJ.T+np.eye(8)*1e-12
        else:self.P=pp
    def cycle(self,u,p,z):
        n=self.n;c=self.alpha**2*n
        wm=np.full(2*n+1,1/(2*c));wm[0]=(c-n)/c;wc=wm.copy();wc[0]+=3-self.alpha**2
        cov=(self.Pz+self.Pz.T)/2
        try:L=np.linalg.cholesky(c*cov)
        except np.linalg.LinAlgError:
            ev,V=np.linalg.eigh(cov);cov=(V*np.maximum(ev,1e-12))@V.T
            L=np.linalg.cholesky(c*cov);self.repairs+=1
        sig=self.z+np.vstack([np.zeros(n),L.T,-L.T])
        full=self._full(sig,self.sums)
        biases=np.zeros((2,2*n+1))
        if self.nb:biases[:self.nb]=sig[:,3:].T
        pred=np.array(self.fm(full.T,np.tile(u[:,None],(1,2*n+1)),
                     np.tile(np.array([p.FB,p.FM,p.T0])[:,None],(1,2*n+1)),biases)).T
        pr=np.c_[pred[:,[0,4,5]],sig[:,3:]]
        mu=wm@pr;dev=pr-mu;PP=(dev.T*wc)@dev+np.diag(self.baseQ*self.qscale)
        v,_=feed(u,p);dec=np.exp(-v/p.V*DT)
        self.sums=dec*self.sums+(1-dec)*np.array([u[0],p.FB,p.FM])/v
        av=np.isfinite(z);ii=np.flatnonzero(av)+1
        if len(ii):
            RR=self.R[np.ix_(av,av)];S=PP[np.ix_(ii,ii)]+RR;nu=z[av]-mu[ii]
            K=np.linalg.solve(S,PP[:,ii].T).T;self.z=mu+K@nu
            H=np.eye(n)[ii];A=np.eye(n)-K@H;self.Pz=A@PP@A.T+K@RR@K.T
            self.nis=float(nu@np.linalg.solve(S,nu));self.innovation=np.zeros(2);self.innovation[av]=nu
            if self.adaptive:
                rr=np.diag(self.R).copy();base=np.diag(RBASE)[av]
                target=np.maximum(nu**2-np.diag(PP[np.ix_(ii,ii)]),.25*base)
                rr[av]=np.clip(.99*rr[av]+.01*target,.25*base,4*base)
                self.R=np.diag(rr);self.qscale=float(np.clip(.98*self.qscale+.02*self.nis/len(ii),.3,10))
        else:self.z=mu;self.Pz=PP;self.nis=np.nan
        self.z[0]=np.clip(self.z[0],max(1e-8,self.sums[0]-self.sums[1]),self.sums[0]-1e-8)
        self.z[1:3]=np.clip(self.z[1:3],275,395)
        if self.nb:self.z[3:]=np.clip(self.z[3:],-.3,.3)
        self.Pz=(self.Pz+self.Pz.T)/2;self._publish();return self.state

