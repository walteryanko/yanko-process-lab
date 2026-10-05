"""Six-state UKF and Neural Adaptive Kalman Estimator, CPU/NumPy inference.
Only state estimates, commanded inputs and PAST innovations enter the network.
No true concentrations or simulator parameters are accessible in update().
"""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
from cstr import Parameters, mass_ss, rhs, U0

DT=.015
P_TABLE=Parameters()
TARGET_T=332.3
_x=mass_ss(TARGET_T,U0,P_TABLE)
_rate=P_TABLE.k0*np.exp(-P_TABLE.E/(P_TABLE.R*TARGET_T))*_x[0]
_cap=P_TABLE.V*np.dot(_x[:4],[P_TABLE.cpA,P_TABLE.cpB,P_TABLE.cpC,P_TABLE.cpM])
HEAT=rhs(0,_x,U0,replace(P_TABLE,dH=0))[4]*_cap/(_rate*P_TABLE.V)
P_ADJUSTED=replace(P_TABLE,dH=float(HEAT))
BASE=mass_ss(TARGET_T,U0,P_ADJUSTED)
U_BASE=np.array([36.3,453.6,45.4,453.6,297.,289.])
XS=np.array([1.,40.,3.,4.,10.,10.])
US=np.array([7.26,90.72,9.08,226.8,10.,10.])
Q_PUBLISHED=np.array([5.616e-8,5.616e-5,5.616e-8,2.4246e-13,.0346356,.00666123])
R_BASE=np.diag(np.array([.35,.30])**2)  # Declared synthetic sensor calibration.
H=np.eye(6)[[4,5]]
P0=np.diag(np.array([.2,1.,.2,.2,1.,1.])**2)


def rhs6(x,u,p=P_ADJUSTED):
    """Vectorized literal balances. Final axis is the physical state."""
    x=np.asarray(x);fa,fb,fm,mw,t0,ta=np.asarray(u)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(u)) or mw<=0:raise ValueError('Invalid numerical domain')
    v=fa/p.rhoA+fb/p.rhoB+fm/p.rhoM
    r=p.k0*np.exp(-p.E/(p.R*x[...,4]))*x[...,0]
    cp=np.array([p.cpA,p.cpB,p.cpC,p.cpM])
    capacity=p.V*(x[...,:4]@cp)
    if np.any(capacity<=0) or np.any(x[...,4]<=0):raise ValueError('Invalid heat capacity/temperature')
    duty=mw*p.cpB*(ta-x[...,4])*(-np.expm1(-p.UA/(mw*p.cpB)))
    dc=(np.array([fa,fb,0.,fm])-v*x[...,:4])/p.V+r[...,None]*np.array([-1.,-1.,1.,0.])
    dT=(duty-(fa*p.cpA+fb*p.cpB+fm*p.cpM)*(x[...,4]-t0)-p.dH*r*p.V)/capacity
    dTt=(mw*p.cpB*(ta-x[...,5])-duty)/(p.rhoB*p.Vt*p.cpB)
    return np.concatenate([dc,dT[...,None],dTt[...,None]],axis=-1)


def transition(x,u,p=P_ADJUSTED,dt=DT,max_step=.003):
    x=np.array(x,dtype=float,copy=True);n=int(np.ceil(dt/max_step));h=dt/n
    for _ in range(n):
        a=rhs6(x,u,p);b=rhs6(x+h*a/2,u,p);c=rhs6(x+h*b/2,u,p);d=rhs6(x+h*c,u,p)
        x+=h*(a+2*b+2*c+d)/6
    if not np.all(np.isfinite(x)):raise ValueError('Nonfinite state')
    return x


def spd(p):
    """Floor only scaled covariance eigenvalues; count repairs elsewhere."""
    p=(p+p.T)/2;w,v=np.linalg.eigh(p)
    if w.min()>=1e-14:return p,False
    return (v*np.maximum(w,1e-14))@v.T,True


class DenseNetwork:
    """Portable trained tanh MLP; JSON weights rather than pickled code."""
    def __init__(self,data):self.data=data
    def predict(self,x):
        a=(np.asarray(x)-np.asarray(self.data['mean']))/np.asarray(self.data['scale'])
        for i,(w,b) in enumerate(zip(self.data['weights'],self.data['biases'])):
            a=a@np.asarray(w)+np.asarray(b)
            if i<len(self.data['weights'])-1:a=np.tanh(a)
        return a*np.asarray(self.data['target_scale'])+np.asarray(self.data['target_mean'])
    @classmethod
    def load(cls,path):return cls(json.loads(Path(path).read_text()))


class UKF:
    def __init__(self,x0,q=Q_PUBLISHED,network=None,kind='ukf',r=R_BASE,transition_model=None):
        self.x=np.array(x0,copy=True);self.p=P0/XS[:,None]/XS[None,:]
        self.q0=np.array(q,copy=True);self.r=np.array(r,copy=True)
        self.kind=kind;self.network=network;self.history=[];self.last_u=U_BASE.copy()
        self.transition_model=transition_model
        self.ema=np.zeros(2);self.repairs=0;self.last_q=self.q0.copy();self.last_scales=np.ones(2)
        n=6;alpha=.2;scale=alpha**2*n
        self.wm=np.r_[1-n/scale,np.full(12,1/(2*scale))];self.wc=self.wm.copy();self.wc[0]+=1-alpha**2+2
        self.sigma_scale=np.sqrt(scale)

    def features(self,u):
        # k-1 innovations only; history resets per trajectory, never crosses splits.
        hist=np.zeros((12,2))
        if self.history:
            z=np.asarray(self.history[-12:]);hist[-len(z):]=z
        return np.r_[(self.x-BASE)/XS,(u-U_BASE)/US,(u-self.last_u)/US,
                     hist[-1],hist.mean(0),hist.std(0),self.ema]

    def update(self,u,y):
        u=np.asarray(u);y=np.asarray(y);feat=self.features(u);p_model=P_ADJUSTED
        q=self.q0.copy()
        if self.network is not None:
            pred=self.network.predict(feat)
            if self.kind in ('nake_q','nake_hybrid'):
                # Bounded exponential: PSD, finite, no online oracle.
                q=self.q0*np.exp(np.clip(pred[2:],np.log(.25),np.log(1e6)))
            if self.kind in ('nake_hybrid','nake_dynamics'):
                scales=np.exp(np.clip(pred[:2],np.log(.7),np.log(1.3)))
                self.last_scales=.8*self.last_scales+.2*scales
                p_model=replace(P_ADJUSTED,UA=P_ADJUSTED.UA*self.last_scales[0],k0=P_ADJUSTED.k0*self.last_scales[1])
        self.last_q=q
        self.p,fixed=spd(self.p);self.repairs+=int(fixed)
        L=np.linalg.cholesky(self.p)
        centre=(self.x-BASE)/XS
        sig=np.vstack([centre,centre+self.sigma_scale*L.T,centre-self.sigma_scale*L.T])
        propagated=(transition if self.transition_model is None else self.transition_model)(BASE+sig*XS,u,p_model)
        pts=(propagated-BASE)/XS
        mean=self.wm@pts;delta=pts-mean
        pp=delta.T@(delta*self.wc[:,None])+np.diag(q/XS**2)
        pp,fixed=spd(pp);self.repairs+=int(fixed)
        xp=BASE+mean*XS
        observed=np.flatnonzero(np.isfinite(y));nis=np.nan
        if len(observed):
            hs=H[observed]*XS
            rr=self.r[np.ix_(observed,observed)]
            ss=hs@pp@hs.T+rr
            gain=np.linalg.solve(ss,(pp@hs.T).T).T
            inov=y[observed]-xp[4+observed]
            mean=mean+gain@inov
            a=np.eye(6)-gain@hs
            post=a@pp@a.T+gain@rr@gain.T  # Joseph form, linear measurement.
            nis=float(inov@np.linalg.solve(ss,inov))
            full=np.zeros(2);full[observed]=inov/np.sqrt(np.diag(ss))
            self.history.append(full);self.history=self.history[-12:]
            self.ema=.9*self.ema+.1*full
        else:
            post=pp
            self.history.append(np.zeros(2));self.history=self.history[-12:];self.ema*=.9
        self.x=BASE+mean*XS;self.p,fixed=spd(post);self.repairs+=int(fixed);self.last_u=u.copy()
        if not np.all(np.isfinite(self.x)) or np.any(self.x[4:]<150) or np.any(self.x[4:]>600):raise ValueError('Estimator divergence')
        return self.x.copy(),self.p*XS[:,None]*XS[None,:],nis,len(observed)
