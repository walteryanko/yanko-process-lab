"""Causal UKF/EKF; exact linear measurement covariance INCLUDING Q.

Adaptive baseline jointly estimates log(UA) and log(k). Neither estimator
receives ground truth. P0 and Q are explicit experimental settings.
"""
import time
import numpy as np
from .physics import njit,transition,Model,BASE,NP,DT
Q6=np.array([5.616e-8,5.616e-5,5.616e-8,2.4246e-13,.0346356,.00666123])
P6=np.array([.12**2,.6**2,.14**2,.1**2,.6**2,.6**2])

@njit(cache=True)
def sym_psd(p):
    p=(p+p.T)/2
    # Eigenvalue repair is only used when Cholesky fails at the public wrapper.
    return p+np.eye(len(p))*1e-12

@njit(cache=True)
def extended_step(x,u,params,dt,variant):
    p=params.copy();n=len(x)
    if n==8:
        p[0]+=x[6];p[6]+=x[7]
    z=x.copy();z[:6]=transition(x[:6],u,p,dt,3,variant)
    return z

@njit(cache=True)
def filter_step(x,p,u,y,params,dt,t,mode=0,variant=0,qscale=1.):
    n=len(x);Q=np.zeros((n,n))
    for i in range(6):Q[i,i]=Q6[i]*qscale
    if n==8:Q[6,6]=2e-5;Q[7,7]=2e-5
    if mode==1:
        xp=extended_step(x,u,params,dt,variant);F=np.empty((n,n))
        for j in range(n):
            e=max(1e-6,abs(x[j])*1e-6);a=x.copy();b=x.copy();a[j]+=e;b[j]-=e
            F[:,j]=(extended_step(a,u,params,dt,variant)-extended_step(b,u,params,dt,variant))/(2*e)
        pp=F@p@F.T+Q
    else:
        c=.25*n;L=np.linalg.cholesky(c*sym_psd(p));points=np.empty((2*n+1,n));points[0]=x
        for j in range(n):points[j+1]=x+L[:,j];points[j+1+n]=x-L[:,j]
        wm=np.full(2*n+1,1/(2*c));wm[0]=(c-n)/c;wc=wm.copy();wc[0]+=(1-.25+2)
        pred=np.empty_like(points)
        for j in range(2*n+1):pred[j]=extended_step(points[j],u,params,dt,variant)
        xp=np.zeros(n)
        for j in range(2*n+1):xp+=wm[j]*pred[j]
        pp=Q.copy()
        for j in range(2*n+1):
            d=pred[j]-xp;pp+=wc[j]*np.outer(d,d)
    count=0
    for j in range(2):
        if np.isfinite(y[j]):count+=1
    innovation=np.full(2,np.nan);Sfull=np.full((2,2),np.nan);nis=0.
    if count:
        H=np.zeros((count,n));z=np.empty(count);bias=np.empty(count);indices=np.empty(count,np.int64);k=0
        for j in range(2):
            if np.isfinite(y[j]):
                H[k,4+j]=1.;z[k]=y[j];bias[k]=params[10+j]+(params[12]*t if j==1 else 0.);indices[k]=j;k+=1
        S=H@pp@H.T+np.eye(count)*.2**2
        K=np.linalg.solve(S,(pp@H.T).T).T;res=z-H@xp-bias
        xn=xp+K@res;A=np.eye(n)-K@H;pn=A@pp@A.T+(K@K.T)*.2**2
        nis=np.dot(res,np.linalg.solve(S,res))
        for j in range(count):
            innovation[indices[j]]=res[j]
            for k in range(count):Sfull[indices[j],indices[k]]=S[j,k]
    else:xn=xp;pn=pp
    # Bounded parameter adaptation, recorded in traces (no physical law assertion).
    if n==8:
        xn[6]=min(.6,max(-.6,xn[6]));xn[7]=min(.6,max(-.6,xn[7]))
    return xn,sym_psd(pn),innovation,Sfull,nis,xp

@njit(cache=True)
def run_numeric(inputs,y,params,dt,mode=0,variant=0,qscale=1.):
    n=8 if mode==2 else 6;steps=len(y)
    x=np.zeros(n);x[:6]=BASE;p=np.zeros((n,n))
    for j in range(6):p[j,j]=P6[j]
    if n==8:p[6,6]=.15**2;p[7,7]=.15**2
    # Initial observation update only, no fictitious transition at t=0.
    for j in range(2):
        if np.isfinite(y[0,j]):
            gain=p[4+j,4+j]/(p[4+j,4+j]+.04)
            x[4+j]+=gain*(y[0,j]-params[10+j]-x[4+j]);p[4+j,4+j]*=(1-gain)
    xs=np.empty((steps,n));ps=np.empty((steps,n,n));res=np.full((steps,2),np.nan)
    Ss=np.full((steps,2,2),np.nan);nis=np.zeros(steps);pred=np.empty((steps,n))
    xs[0]=x;ps[0]=p;pred[0]=x
    for k in range(1,steps):
        x,p,res[k],Ss[k],nis[k],pred[k]=filter_step(x,p,inputs[k-1],y[k],params,dt,k*dt,mode,variant,qscale)
        xs[k]=x;ps[k]=p
    return xs,ps,res,Ss,nis,pred

def observe(record,model=None,kind='ukf',qscale=1.):
    model=model or Model();mode={'ukf':0,'ekf':1,'adaptive':2}[kind]
    start=time.perf_counter()
    xs,p,res,S,nis,pred=run_numeric(record.inputs,record.measurements,model.params,record.dt,mode,model.variant,qscale)
    if not np.all(np.isfinite(xs)) or np.min(xs[:,:4])<0:raise FloatingPointError('Filter domain')
    return dict(x=xs[:,:6],cov=p[:,:6,:6],innovation=res,S=S,nis=nis,pred=pred[:,:6],
                augmented=xs[:,6:],seconds=time.perf_counter()-start)

class OnlineUKF:
    def __init__(self,model=None,adaptive=False):
        self.model=model or Model();self.adaptive=adaptive;n=8 if adaptive else 6
        self.x=np.r_[BASE,np.zeros(n-6)];self.P=np.diag(np.r_[P6,np.full(n-6,.15**2)])
        self.t=0.;self.repairs=0
    def update(self,u,y,dt=DT):
        self.t+=dt
        self.x,self.P,r,S,nis,_=filter_step(self.x,self.P,np.asarray(u,float),np.asarray(y,float),self.model.params,dt,self.t,2 if self.adaptive else 0,self.model.variant)
        return self.x[:6].copy(),dict(innovation=r,S=S,nis=float(nis))
