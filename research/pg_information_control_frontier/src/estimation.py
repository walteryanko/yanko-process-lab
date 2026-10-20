"""Same-information estimators; optional exact inventory is labeled privileged.
The UKF uses the recovered sigma-point equations with a new explicit prior.
No plant state or future disturbances are accepted by the update interface.
"""
import numpy as np
from scipy.optimize import least_squares
from numba import njit
from model import step,DT,inventory_step,reconstruct
Q=np.array([2e-6,2e-5,2e-6,1e-7,.015,.006])
P0=np.diag(np.array([.15,.8,.4,.3,.5,.5])**2)
SIGMA=np.array([1.385,1.062])/1.8
R=SIGMA**2

@njit(cache=True)
def evolve(x,u,p,variant,mode,s):
    if mode==3:
        z=reconstruct(x,s);sn=inventory_step(s,u)
        zn=step(z,u,p,variant)
        return np.array([zn[2],zn[4],zn[5]])
    if mode==2:
        pp=p.copy();pp[0]+=x[6];pp[1]+=x[7]
        z=x.copy();z[:6]=step(x[:6],u,pp,variant);return z
    return step(x,u,p,variant)

@njit(cache=True)
def predict(x,P,u,p,variant,mode,s):
    n=len(x);c=.25*n
    L=np.linalg.cholesky(c*((P+P.T)/2+np.eye(n)*1e-12))
    pts=np.empty((2*n+1,n));pts[0]=x
    for j in range(n):pts[j+1]=x+L[:,j];pts[j+1+n]=x-L[:,j]
    wm=np.full(2*n+1,1/(2*c));wm[0]=(c-n)/c;wc=wm.copy();wc[0]+=2.75
    Z=np.empty_like(pts);xp=np.zeros(n)
    for j in range(2*n+1):
        Z[j]=evolve(pts[j],u,p,variant,mode,s);xp+=wm[j]*Z[j]
    pp=np.zeros((n,n))
    for j in range(2*n+1):
        e=Z[j]-xp;pp+=wc[j]*np.outer(e,e)
    if mode==3:
        pp+=np.diag(np.array([Q[2],Q[4],Q[5]]))
    else:
        for j in range(6):pp[j,j]+=Q[j]
        if n==8:pp[6,6]+=1e-5;pp[7,7]+=1e-5
    return xp,(pp+pp.T)/2+np.eye(n)*1e-12

class Filter:
    def __init__(self,x0,kind='ukf',known_inventory=None,p=None,variant=0):
        self.kind=kind;self.variant=variant;self.p=np.zeros(3) if p is None else p.copy()
        self.mode=2 if kind=='adaptive' else (3 if kind=='reduced' else 0)
        self.s=np.zeros(3) if known_inventory is None else known_inventory.copy()
        if self.mode==3:self.x=x0[[2,4,5]].copy();self.P=P0[np.ix_([2,4,5],[2,4,5])].copy()
        else:
            self.x=np.r_[x0,np.zeros(2)] if self.mode==2 else x0.copy()
            self.P=np.zeros((len(self.x),len(self.x)));self.P[:6,:6]=P0
            if self.mode==2:self.P[6:,6:]=np.eye(2)*.15**2
        self.nis=[];self.repairs=0;self.mhe_failures=0
        self.history=[]

    def update(self,u,y,advance=True,chemical=None):
        if advance:
            try:self.x,self.P=predict(self.x,self.P,u,self.p,self.variant,self.mode,self.s)
            except np.linalg.LinAlgError:
                w,v=np.linalg.eigh((self.P+self.P.T)/2)
                self.P=(v*np.maximum(w,1e-10))@v.T;self.repairs+=1
                self.x,self.P=predict(self.x,self.P,u,self.p,self.variant,self.mode,self.s)
            if self.mode==3:self.s=inventory_step(self.s,u)
        indices=[1,2] if self.mode==3 else [4,5]
        rows=[];yy=[];rv=[]
        for j in range(2):
            if np.isfinite(y[j]):rows.append(indices[j]);yy.append(y[j]);rv.append(R[j])
        if chemical is not None:
            value,variance=chemical
            rows.append(0 if self.mode==3 else 2);yy.append(value);rv.append(variance)
        if rows:
            H=np.eye(len(self.x))[rows];res=np.asarray(yy)-H@self.x
            S=H@self.P@H.T+np.diag(rv);K=np.linalg.solve(S,(self.P@H.T).T).T
            self.x+=K@res;A=np.eye(len(self.x))-K@H
            self.P=A@self.P@A.T+K@np.diag(rv)@K.T
            self.nis.append(float(res@np.linalg.solve(S,res)))
        else:self.nis.append(np.nan)
        if self.mode==2:self.x[6:8]=np.clip(self.x[6:8],-.5,.5)
        # Bounds are estimator repairs, never plant modifications.
        if self.mode!=3 and min(self.x[:4])<0:
            self.x[:4]=np.maximum(self.x[:4],1e-8);self.repairs+=1
        return self.state()

    def state(self):return reconstruct(self.x,self.s) if self.mode==3 else self.x[:6].copy()
    def params(self):
        pp=self.p.copy()
        if self.mode==2:pp[:2]+=self.x[6:8]
        return pp
    def covariance(self):
        if self.mode!=3:return self.P[:6,:6]
        G=np.array([[-1,0,0],[-1,0,0],[1,0,0],[0,0,0],[0,1,0],[0,0,1]])
        return G@self.P@G.T

class MHE:
    """Deterministic rolling-window MAP, six free initial states, zero process residual.
    Its finite window and approximate arrival prior are explicit limitations.
    """
    def __init__(self,x0,window=6):
        self.filter=Filter(x0);self.window=window;self.records=[];self.last=x0.copy()
        self.nis=self.filter.nis;self.repairs=0;self.mhe_failures=0
    def update(self,u,y,advance=True,chemical=None):
        self.filter.update(u,y,advance,chemical)
        self.records.append((u.copy(),y.copy(),self.filter.state(),self.filter.covariance().copy()))
        self.records=self.records[-(self.window+1):]
        if len(self.records)<3:
            self.last=self.filter.state();return self.last
        prior=self.records[0][2]
        sd=np.sqrt(np.maximum(np.diag(self.records[0][3]),1e-8))
        def residual(a):
            z=prior+sd*a;out=list(a)
            for k in range(1,len(self.records)):
                z=step(z,self.records[k][0],np.zeros(3))
                yy=self.records[k][1];mask=np.isfinite(yy)
                out.extend(((z[4:6]-yy)/SIGMA)[mask])
            return np.array(out)
        try:
            sol=least_squares(residual,np.zeros(6),bounds=((-prior+1e-8)/sd,
                (np.array([10,80,10,20,390,390])-prior)/sd),max_nfev=18,ftol=1e-5,xtol=1e-5,gtol=1e-5)
            if not sol.success:self.mhe_failures+=1
            z=prior+sd*sol.x
            for k in range(1,len(self.records)):z=step(z,self.records[k][0],np.zeros(3))
            self.last=z if np.all(np.isfinite(z)) else self.filter.state()
        except (ValueError,FloatingPointError):
            self.mhe_failures+=1;self.last=self.filter.state()
        return self.last.copy()
    def state(self):return self.last.copy()
    def covariance(self):return self.filter.covariance() # diagnostic approximate, not MHE Hessian
    def params(self):return np.zeros(3)
