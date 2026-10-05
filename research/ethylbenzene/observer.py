"""Five-state temperature-only UKF, causal learned-Q LSTM, and NAKE-BB.

NAKE is this project's research name: learned dynamics plus UKF correction
and adaptive process uncertainty. It does not train a Kalman gain.
"""
import numpy as np
from model import *

Q_BASE=np.array([1.e-7,2.e-6,2.e-6,1.e-7,.0036])
R_MEAS=1.5**2;WINDOW=12
KINDS=['ukf','lstm_ukf','nake','lstm_nake']

def spd(p):
    p=(p+p.T)/2;w,v=np.linalg.eigh(p)
    if w.min()>=1e-13:return p,False
    return (v*np.maximum(w,1e-13))@v.T,True

class Observer:
    def __init__(self,x0,models,kind='ukf',lstm=None,network=None):
        self.models=models;self.kind=kind;self.lstm=lstm;self.x=np.array(x0,copy=True)
        self.p=np.diag((np.array([.015,.35,.18,.06,2.])/XS)**2)
        self.model='neural' if kind in ['nake','lstm_nake'] else 'physical'
        self.qbase=Q_BASE.copy()+(network.q_model if self.model=='neural' else 0.)
        self.last_u=U0.copy();self.last_innovation=0.;self.ema=1.;self.mask=1.
        self.sequence=[];self.repairs=0;self.projections=0;self.last_q=self.qbase.copy()
        alpha=.35;scale=alpha*alpha*5
        self.wm=np.r_[1-5/scale,np.full(10,1/(2*scale))];self.wc=self.wm.copy();self.wc[0]+=1-alpha*alpha+2
        self.sigscale=np.sqrt(scale)
    def feature(self,u):
        return np.r_[(self.x-BASE)/XS,(u-U0)/US,(u[[0,3]]-self.last_u[[0,3]])/US[[0,3]],
                      self.last_innovation,np.log(max(self.ema,1e-6)),self.mask]
    def update(self,u,y):
        feature=self.feature(np.asarray(u));self.sequence.append(feature);self.sequence=self.sequence[-WINDOW:]
        q=self.qbase.copy()
        if self.kind in ['lstm_ukf','lstm_nake']:
            seq=np.zeros((WINDOW,len(feature)));seq[-len(self.sequence):]=self.sequence
            factor=np.exp(np.clip(self.lstm.predict(seq),np.log(.25),np.log(100.)))
            q*=factor
        elif self.kind=='nake':q*=np.clip(self.ema,1.,100.)
        self.last_q=q.copy();self.p,fixed=spd(self.p);self.repairs+=int(fixed)
        L=np.linalg.cholesky(self.p);centre=(self.x-BASE)/XS
        sig=np.vstack([centre,centre+self.sigscale*L.T,centre-self.sigscale*L.T])
        physical=BASE+sig*XS
        # Positivity projection is explicit and counted, identically in all variants.
        if np.any(physical[:,:4]<1e-7):
            self.projections+=int(np.sum(physical[:,:4]<1e-7));physical[:,:4]=np.maximum(physical[:,:4],1e-7)
        z=(self.models.transition(self.model,physical,u)-BASE)/XS
        mean=self.wm@z;delta=z-mean;pp=delta.T@(delta*self.wc[:,None])+np.diag(q/XS**2)
        pp,fixed=spd(pp);self.repairs+=int(fixed);xp=BASE+mean*XS;nis=None
        if np.isfinite(y):
            h=np.array([0.,0.,0.,0.,XS[4]]);ss=float(h@pp@h+R_MEAS);gain=pp@h/ss
            innovation=float(y-xp[4]);mean+=gain*innovation
            a=np.eye(5)-np.outer(gain,h);post=a@pp@a.T+np.outer(gain,gain)*R_MEAS
            nis=innovation**2/ss;self.last_innovation=innovation/np.sqrt(ss)
            self.ema=.95*self.ema+.05*min(nis,100.);self.mask=1.
        else:post=pp;self.last_innovation=0.;self.mask=0.
        self.x=BASE+mean*XS;self.p,fixed=spd(post);self.repairs+=int(fixed)
        if np.any(self.x[:4]<1e-7):
            self.projections+=int(np.sum(self.x[:4]<1e-7));self.x[:4]=np.maximum(self.x[:4],1e-7)
        self.last_u=np.array(u,copy=True)
        if not np.all(np.isfinite(self.x)) or not 0.<self.x[4]<300.:raise ValueError('Observer divergence')
        return self.x.copy(),self.p*XS[:,None]*XS[None,:],nis
