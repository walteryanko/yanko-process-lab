"""Scaled pseudo-arclength predictor/corrector; no assumption of single-valued branches."""
import numpy as np
from scipy.optimize import root

def difference_jac(fun,x):
    x=np.array(x,float);J=np.empty((len(fun(x)),len(x)))
    for j in range(len(x)):
        h=2e-5*max(1.,abs(x[j]));d=np.eye(len(x))[j]*h
        J[:,j]=(fun(x+d)-fun(x-d))/(2*h)
    return J

def arclength(fun,z0,scale=None,ds=.025,steps=250,direction=1,stop=None):
    """fun(z)=0 has n equations for n+1 unknowns; scale fixes units of arclength.
    Tangent from nullspace, Newton correction with orthogonal hyperplane.
    Failed correction halves ds, records failure, then stops below 1e-6.
    """
    z0=np.array(z0,float);scale=np.ones_like(z0) if scale is None else np.array(scale,float)
    F=lambda q:np.asarray(fun(q*scale),float)
    q=z0/scale
    if np.max(np.abs(F(q)))>1e-6:raise ValueError('Initial point is not an equilibrium')
    _,_,vh=np.linalg.svd(difference_jac(F,q));tau=vh[-1];tau*=direction*(1 if tau[-1]>=0 else -1)
    rows=[q*scale];res=[float(np.linalg.norm(F(q)))];tangents=[tau.copy()];failures=[]
    for k in range(steps):
        ds_try=ds
        while True:
            pred=q+ds_try*tau
            g=lambda zz:np.r_[F(zz),np.dot(zz-pred,tau)]
            sol=root(g,pred,tol=1e-10)
            err=float(np.linalg.norm(g(sol.x)))
            if err<1e-8 and np.linalg.norm(sol.x-q)<4*ds_try:break
            failures.append({'step':k,'ds':ds_try,'residual':err});ds_try*=.5
            if ds_try<1e-6:return dict(points=np.array(rows),residual=np.array(res),tangents=np.array(tangents),failures=failures,terminated='corrector_failure')
        q=sol.x;_,s,vh=np.linalg.svd(difference_jac(F,q));nt=vh[-1]
        if np.dot(nt,tau)<0:nt=-nt
        tau=nt;rows.append(q*scale);res.append(float(np.linalg.norm(F(q))));tangents.append(tau.copy())
        if stop is not None and stop(q*scale):break
    return dict(points=np.array(rows),residual=np.array(res),tangents=np.array(tangents),failures=failures,terminated='complete')

def classify_crossings(points,spectra):
    """Candidate brackets only. A verified fold/Hopf needs refinement and transversality."""
    candidates=[]
    for i in range(1,len(points)):
        a=np.array(spectra[i-1]);b=np.array(spectra[i]);ea=a[np.argmax(a.real)];eb=b[np.argmax(b.real)]
        if ea.real*eb.real<0:
            candidates.append({'index':i,'type':'hopf_candidate' if abs(eb.imag)>.01 else 'fold_candidate','left':points[i-1].tolist(),'right':points[i].tolist()})
    return candidates

def normal_form_tests():
    fold=arclength(lambda z:np.array([z[1]-z[0]**2]),[1.,1.],ds=.04,steps=110,direction=-1)
    hopf=arclength(lambda z:np.array([z[2]*z[0]-z[1]-z[0]*(z[0]**2+z[1]**2),z[0]+z[2]*z[1]-z[1]*(z[0]**2+z[1]**2)]),[0.,0.,-1.],ds=.04,steps=50)
    return fold,hopf
