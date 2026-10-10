"""Temperature-only state estimators; no true chemical state in updates."""
from collections import deque
import time
import numpy as np
import casadi as ca
from scipy.optimize import least_squares
from ethylbenzene_model.model import STEP,AJAC,SCALE,DT

PINITIAL=np.diag(np.array([.10,.05,.06,.10,.02])**2)
QBASE=np.diag(np.array([.004,.00015,.0005,.0006,.001])**2)

def project(x):
    x=np.asarray(x).copy();x[:4]=np.maximum(x[:4],1e-8);x[4]=np.clip(x[4],-10,300)
    return x

class Filter:
    def __init__(self,x,kind='ekf',sigma=.2,qscale=1.,p=None):
        self.kind=kind;self.x=x.copy();self.P=PINITIAL.copy();self.Q=QBASE*qscale
        self.R=(sigma/SCALE[4])**2;self.p=np.zeros(12) if p is None else p.copy()
        self.nis=[];self.cov=[];self.time=[];self.last_innovation=0.;self.anomalies=0
    def update(self,u,y):
        t=time.perf_counter(); z=self.x/SCALE
        if self.kind in ['ukf','adaptive_ukf','thermal_ukf']:
            n=5;alpha=.4;lam=alpha*alpha*n-n
            eig,V=np.linalg.eigh((self.P+self.P.T)/2);L=V@np.diag(np.sqrt(np.maximum(eig,1e-12)*(n+lam)))
            Z=np.column_stack([z,z[:,None]+L,z[:,None]-L])
            Wm=np.full(2*n+1,1/(2*(n+lam)));Wm[0]=lam/(n+lam);Wc=Wm.copy();Wc[0]+=1-alpha*alpha+2
            X=np.array(STEP(Z*SCALE[:,None],np.tile(u,(11,1)).T,np.tile(self.p,(11,1)).T))/SCALE[:,None]
            zp=X@Wm;DX=X-zp[:,None];Pp=(DX*Wc)@DX.T+self.Q
        else:
            zp=np.array(STEP(self.x,u,self.p)).ravel()/SCALE
            A=np.array(AJAC(self.x,u,self.p))*SCALE[None,:]/SCALE[:,None]
            Pp=A@self.P@A.T+self.Q
        self.last_innovation=float(y-zp[4]*SCALE[4]) if np.isfinite(y) else 0.
        if np.isfinite(y):
            innov=y/SCALE[4]-zp[4];var=max(Pp[4,4]+self.R,1e-12);nis=float(innov*innov/var)
            R=self.R
            if self.kind=='adaptive_ukf':
                if nis>16:
                    R*=max(1,nis/9);self.anomalies+=1
                # Bounded innovation-based inflation; cannot identify arbitrary model bias.
                self.Q=QBASE*np.clip(.97*np.trace(self.Q)/np.trace(QBASE)+.03*nis,.25,25)
            K=Pp[:,4]/(Pp[4,4]+R)
            zpost=zp+K*innov
            # Joseph form for the linear temperature measurement.
            H=np.zeros((1,5));H[0,4]=1
            M=np.eye(5)-K[:,None]@H
            self.P=M@Pp@M.T+R*np.outer(K,K)
            self.nis.append(nis)
        else:
            zpost=zp;self.P=Pp
        if self.kind=='thermal_ukf' and np.isfinite(y):
            # One thermal-residual parameter only, derivative units degC/h.
            self.p[11]=np.clip(self.p[11]+.05*self.last_innovation,-25,25)
        self.x=project(zpost*SCALE);self.cov.append(self.P.copy());self.time.append(time.perf_counter()-t)
        return self.x

class MHE:
    """Constrained deterministic MHE with EKF arrival and N past T samples.

    Initial state of horizon is optimized; no fictitious online composition label.
    Optional scalar heat residual, with a bounded prior, is an ablation.
    """
    functions={}
    def __init__(self,x,window=10,sigma=.2,adapt=False,p=None):
        self.x=x.copy();self.p=np.zeros(12) if p is None else p.copy();self.shadow=Filter(x,sigma=sigma,p=p)
        self.N=window;self.sigma=sigma;self.adapt=adapt;self.hist=deque(maxlen=window);self.states=deque([x.copy()],maxlen=window+1)
        self.P=PINITIAL.copy();self.nis=[];self.time=[];self.failures=0
    def _func(self,n):
        key=(n,self.adapt,float(self.sigma))
        if key in self.functions:return self.functions[key]
        z=ca.MX.sym('z',6 if self.adapt else 5);q=ca.MX.sym('q',n*8+5+12)
        prior=q[n*8:n*8+5];p=q[n*8+5:]
        if self.adapt:p[11]=z[5]
        state=z[:5]*ca.DM(SCALE);res=[(z[:5]-prior)/ca.DM([.08,.04,.06,.08,.015])]
        for j in range(n):
            state=STEP(state,q[8*j:8*j+7],p)
            res.append((state[4]-q[8*j+7])/self.sigma)
        if self.adapt:res.append(z[5]/10)
        rr=ca.vertcat(*res)
        f=ca.Function('mhe_res',[z,q],[rr]);jac=ca.Function('mhe_jac',[z,q],[ca.jacobian(rr,z)])
        out=ca.Function('mhe_out',[z,q],[state])
        self.functions[key]=(f,jac,out);return f,jac,out
    def update(self,u,y):
        t=time.perf_counter();pred=self.shadow.update(u,y)
        if not np.isfinite(y):
            self.x=pred;self.states.append(pred.copy());self.hist.clear();self.time.append(time.perf_counter()-t);return self.x
        self.hist.append((u.copy(),float(y)))
        n=len(self.hist);prior=list(self.states)[-n]
        q=np.r_[np.concatenate([np.r_[a,b] for a,b in self.hist]),prior/SCALE,self.p]
        f,jac,out=self._func(n);z0=prior/SCALE
        if self.adapt:z0=np.r_[z0,self.p[11]]
        lb=np.r_[np.zeros(4),-.2];ub=np.r_[[100,3,5,10],6.]
        if self.adapt:lb=np.r_[lb,-25];ub=np.r_[ub,25]
        try:
            sol=least_squares(lambda z:np.array(f(z,q)).ravel(),np.clip(z0,lb+1e-10,ub-1e-10),jac=lambda z:np.array(jac(z,q)),bounds=(lb,ub),max_nfev=10,ftol=1e-5,xtol=1e-5,gtol=1e-5)
            self.x=project(np.array(out(sol.x,q)).ravel())
            if self.adapt:self.p[11]=float(sol.x[5])
            if not sol.success:self.failures+=1
        except (ValueError,RuntimeError):self.x=pred;self.failures+=1
        self.states.append(pred.copy());self.P=self.shadow.P.copy();self.nis=self.shadow.nis;self.time.append(time.perf_counter()-t)
        return self.x
