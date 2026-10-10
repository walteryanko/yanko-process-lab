"""Six original states; synthetic, explicitly declared plant-model mismatch."""
import numpy as np
from src.plant.model import *
from lbe.config import CP_DELTA

def residual_truth(x,u):
    t=x[...,4];a=x[...,0];m=u[...,1]/U0[1]
    return np.stack([.08+.035*np.tanh((t-332)/13)+.015*np.sin(2*a)/(1+m),
                     -.10+.025*np.tanh(m-1)+.015*np.sin((t-320)/17)],axis=-1)

def rates(x,u,p=Parameters(),severity=1.,offset=(0.,0.)):
    return np.maximum(.1,1+severity*residual_truth(np.asarray(x),np.asarray(u))+np.asarray(offset))

def vector_rhs(x,u,p=Parameters(),correction=None):
    x=np.asarray(x);c=np.zeros((*x.shape[:-1],2)) if correction is None else np.asarray(correction)
    k=p.k0*np.exp(-p.E/(p.R*(x[...,4]+p.arrhenius_offset)))*(1+c[...,0]);r=k*x[...,0]
    v,c0=feed(u,p);D=v/p.V
    duty=u[1]*p.cpB*(u[2]-x[...,4])*(-np.expm1(-p.UA*(1+c[...,1])/(u[1]*p.cpB)))
    w=x[...,:4]@np.array([p.cpA,p.cpB,p.cpC,p.cpM])
    dT=(duty-(u[0]*p.cpA+p.FB*p.cpB+p.FM*p.cpM)*(x[...,4]-p.T0)-p.dH*r*p.V)/(p.V*w)
    dTj=(u[1]*p.cpB*(u[2]-x[...,5])-duty)/(p.rhoB*p.Vt*p.cpB)
    return np.concatenate([D*(c0-x[...,:4])+r[...,None]*[-1,-1,1,0],dT[...,None],dTj[...,None]],axis=-1)

def truth_rhs(t,x,u,p=Parameters(),severity=1.,offset=(0.,0.)):
    return vector_rhs(x,u,p,rates(x,u,p,severity,offset)-1)

def rk4(x,u,p=Parameters(),model=None,bias=None,dt=DT,substeps=4,severity=None,offset=(0.,0.)):
    def f(z):
        c=np.zeros((*np.asarray(z).shape[:-1],2)) if model is None else model(z,u)
        if severity is not None:c=rates(z,u,p,severity,offset)-1
        if bias is not None:c=c+np.asarray(bias)
        return vector_rhs(z,u,p,np.clip(c,-.5,.6))
    z=np.array(x,copy=True);h=dt/substeps
    for _ in range(substeps):
        a=f(z);b=f(z+h*a/2);c=f(z+h*b/2);d=f(z+h*c);z+=h*(a+2*b+2*c+d)/6
    return z

def inventory_potential(x,p=Parameters()):
    x=np.asarray(x);w=x[...,:4]@np.array([p.cpA,p.cpB,p.cpC,p.cpM]);q=w-CP_DELTA*x[...,0]
    return x[...,4]+(-p.dH)/CP_DELTA*np.log1p(CP_DELTA*x[...,0]/q)

def economic_components(x,u,ref,p=Parameters()):
    v,_=feed(u,p);v0,_=feed(U0,Parameters());c0=.1433*CUNIT
    duty=abs(u[1]*p.cpB*(u[2]-x[4])*(-np.expm1(-p.UA/(u[1]*p.cpB))))
    e=(x[2]-ref)/c0;off=max(abs(e)-.01,0)
    prod=v*x[2];quality=30*e*e+200*off*off
    raw=u[0]/U0[0];cool=.04*(u[1]/U0[1])**2;heat=.02*duty/1e6;value=1.2*prod/(v0*c0)
    return dict(cost=raw+cool+heat+quality-value,feed=raw,cooling=cool,heat=heat,quality=quality,value=value,production=prod,duty=duty,on_spec=bool(abs(e)<=.01))
